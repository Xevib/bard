from __future__ import absolute_import
import os
import re
import sys
from tempfile import mkstemp

from configobj import ConfigObj
import osmium
import requests
import gettext
from jinja2 import Environment
from osconf import config_from_environment
import osmapi
import psycopg2
import psycopg2.extras
from psycopg2.extensions import AsIs



from raven import Client

# Env vars:
# AREA_GEOJSON
# MAILGUN_DOMAIN
# MAILGUN_API_KEY
# EMAIL_RECIPIENTS
# EMAIL_LANGUAGE
# CONFIG


def get_state():
    """
    Downloads the state from OSM replication system

    :return: Actual state as a str
    """

    r = requests.get('http://planet.openstreetmap.org/replication/day/state.txt')
    return r.text.split('\n')[1].split('=')[1]


def get_osc(stateurl=None):
    """
    Function to download the osc file

    :param stateurl: str with the url of the osc
    :return: None
    """

    if not stateurl:
        state = get_state()

        # zero-pad state so it can be safely split.
        state = '000000000' + state
        path = '{0}/{1}/{2}'.format(state[-9:-6], state[-6:-3], state[-3:])
        stateurl = 'http://planet.openstreetmap.org/replication/day/{0}.osc.gz'.format(path)

    sys.stderr.write('downloading {0}...\n'.format(stateurl))
    # prepare a local file to store changes
    handle, filename = mkstemp(prefix='change-', suffix='.osc.gz')
    os.close(handle)

    with open(filename, "w") as f:
        resp = requests.get(stateurl)
        f.write(resp.content)
    sys.stderr.write('Done\n')
    #sys.stderr.write('extracting {0}...\n'.format(filename))
    #os.system('gunzip -f {0}'.format(filename))

    # knock off the ".gz" suffix and return
    return filename


class ChangeHandler(osmium.SimpleHandler):
    """
    Class that handles the changes
    """

    def __init__(self):
        """
        Class constructor
        """
        osmium.SimpleHandler.__init__(self)
        self.num_nodes = 0
        self.num_ways = 0
        self.num_rel = 0
        self.tags = {}
        self.north = 0
        self.east = 0
        self.south = 0
        self.west = 0
        self.changeset = {}
        self.stats = {}
        self.cache = None
        self.cache_enabled = False
        self.sentry_client = Client()

    def set_cache(self, host, db, user, password):
        """
        Sets the cache of the handler
        :param host: database host
        :param db: database name
        :param user: database user
        :param password: database password
        :return: None
        :rtype: None
        """

        self.cache = DbCache(host,db,user,password)
        self.cache_enabled = True

    def location_in_bbox(self, location):
        """
        Checks if the location is in the bounding box

        :param location: Location
        :return: Boolean
        """

        return self.north > location.lat > self.south and self.east > location.lon > self.west

    def way_in_bbox(self, nodes):
        """
        Checks if the way is in the bounding box
        :param nodes: Nodes of the way
        :return: Booelan
        """

        inside = False
        x = 0
        while not inside and x < len(nodes):
            if nodes[x].location.valid():
                inside = self.location_in_bbox(nodes[x].location)
            x += 1
        return inside

    def node_in_bbox(self, node):
        """
        Check if a node id is in the bounding box

        :param node: Node
        :type node: dict or list
        :return: True if the node is in the bounding box
        :rtype: bool
        """

        if isinstance(node, dict):
            if 'data' in node:
                lat = node["data"]["lat"]
                lon = node["data"]["lon"]
            else:
                lat = node.get("lat")
                lon = node.get("lon")
        elif isinstance(node, list):
            lat = node[0]
            lon = node[1]
        return self.north > lat > self.south and self.east > lon > self.west

    def way_id_in_bbox(self, way_id):
        """
        Checks if an id of a way is in the bounding box

        :param way_id: id of the way
        :return:
        """
        osm_api = osmapi.OsmApi()
        way = self.cache.get_way(way_id)
        if not way:
            way = osm_api.WayGet(way_id)
        ret = False
        index = 0
        while not ret and index < len(way["nd"]):
            ret = self.node_in_bbox(way["nd"][index])
            index += 1
        return ret

    def rel_in_bbox(self, relation):
        """
        Checks if the relation is in the bounding box

        :param relation: List of members of the relation
        :return: True if the relation is in the bounding box
        :rtype: bool
        """
        api = osmapi.OsmApi()
        for member in relation.members:
            if member.type == "n":
                if self.cache_enabled:
                    node = self.cache.get_node(member.ref)
                    if node is None:
                        node = api.NodeGet(member.ref)
                    ret = self.node_in_bbox(node)
                    if ret:
                        return True
            elif member.type == "w":
                if self.cache_enabled:
                    way = self.cache.get_way(member.ref)
                else:
                    way = None
                if way is None:
                    way = api.WayFull(member.ref)
                    nodes = []
                    for element in way:
                        if element["type"] == "way":
                            version = element["data"]["version"]
                            tags = element["data"]["tag"]
                        else:
                            nodes.append([element["data"]["lat"],element["data"]["lon"]])
                    if self.cache_enabled:
                        self.cache.add_way(member.ref, version, nodes, tags)
                    print("way ref:{}".format(member.ref))
                if "coordinates" in way:
                    nodes = way.get("coordinates", [])
                else:
                    nodes = way
                for node in nodes:
                    if isinstance(node, dict) and node.get("type")!="node":
                        for node_id in node.get("nd", []):
                            n = self.cache.get_node(node_id)
                            if node is None:
                                node = api.NodeGet(node_id)
                            ret = self.node_in_bbox(n)
                            if ret:
                                return True
                    else:
                        ret = self.node_in_bbox(node)
                        if ret:
                            return True
            else:
                print("member.type:{}".format(member.type))

        # rel_data = api.RelationFull(relation.id)
        # for element in rel_data:
        #     if element["type"] == "node":
        #         ret = self.node_in_bbox(element)
        #         if ret:
        #             return True
        # return False

    def has_tag_changed(self, gid, old_tags, watch_tags, version, elem):
        """
        Checks if tags has changed on the changeset

        :param gid: Geometry id
        :param old_tags: Old tags
        :param watch_tags: Tags to check
        :param version: version to check
        :param elem: Type of element
        :return: Boolean
        """

        previous_elem = {}
        osm_api = osmapi.OsmApi()
        if elem == 'node':
            if self.cache_enabled:
                previous_elem = self.cache.get_node(gid, version -1)
                if previous_elem is None:
                    previous_elem = osm_api.NodeHistory(gid)[version - 1]
            else:
                previous_elem = osm_api.NodeHistory(gid)[version - 1]
        elif elem == 'way':
            previous_elem = osm_api.WayHistory(gid)[version - 1]
        elif elem == 'relation':
            previous_elem = osm_api.RelationHistory(gid)[version - 1]
        if previous_elem:
            previous_tags = previous_elem['tag']
            out_tags = {}
            for key, value in previous_tags.items():
                if re.match(watch_tags, key):
                    out_tags[key] = value
            previous_tags = out_tags
            out_tags = {}
            for key, value in old_tags.items():
                if re.match(watch_tags, key):
                    out_tags[key] = value
            old_tags = out_tags
            return previous_tags != old_tags
        else:
            return False

    def convert_osmium_tags_dict(self, tags):
        """
        Converts the tags of osmium to dict
        :return: Dict
        """
        ret = {}
        for tag in tags:
            ret[tag.k] = tag.v
        return ret

    def has_tag(self, element, key_re, value_re):
        """
        Checks if the element have the key,value

        :param element: Element to check
        :param key_re: Compiled re expression of key 
        :param value_re: Compiled re expression of value
        :return: boolean
        """
        for tag in element:
            key = tag.k
            value = tag.v
            if key_re.match(key) and value_re.match(value):
                return True
        return False

    def set_tags(self, name, key, value, element_types):
        """
        Sets the tags to wathc on the handler
        :param name: Name of the tags
        :param key: Key value expression
        :param value: Value expression
        :param element_types: List of element types
        :return: None
        """
        self.tags[name] = {}
        self.tags[name]["key_re"] = re.compile(key)
        self.tags[name]["value_re"] = re.compile(value)
        self.tags[name]["types"] = element_types
        self.stats[name] = set()

    def set_bbox(self, north, east, south, west):
        """
        Sets the bounding box to check

        :param north: North of bbox
        :param east: East of the bbox
        :param south: South of the bbox
        :param west: West of the bbox
        :return: None
        """
        self.north = float(north)
        self.east = float(east)
        self.south = float(south)
        self.west = float(west)

    def node(self, node):
        """
        Attends the nodes in the file

        :param node: Node to check 
        :return: None
        """
        try:

            if self.cache_enabled:
                self.cache.add_node(node.id, node.version, node.location.lat, node.location.lon, self.convert_osmium_tags_dict(node.tags))
            if self.location_in_bbox(node.location):
                for tag_name in self.tags.keys():
                    key_re = self.tags[tag_name]["key_re"]
                    value_re = self.tags[tag_name]["value_re"]
                    if self.has_tag(node.tags, key_re, value_re):
                        if node.deleted:
                            add_node = True
                        elif node.version == 1:
                            add_node = True
                        else:
                            add_node = self.has_tag_changed(
                                node.id, self.convert_osmium_tags_dict(node.tags), key_re, node.version, "node")
                        if add_node:
                            if tag_name in self.stats:
                                self.stats[tag_name].add(node.changeset)
                            else:
                                self.stats[tag_name] = [node.changeset]
                            if node.changeset not in self.changeset:
                                self.changeset[node.changeset] = {
                                    "changeset": node.changeset,
                                    "user": node.user,
                                    "uid": node.uid,
                                    "nids": {tag_name: [node.id]},
                                    "wids": {},
                                    "rids": {}
                                }
                            else:
                                if tag_name not in self.changeset[node.changeset]["nids"]:
                                    self.changeset[node.changeset]["nids"][tag_name] = []
                                self.changeset[node.changeset]["nids"][tag_name].append(
                                    node.id)
            self.num_nodes += 1
        except Exception:
            self.sentry_client.captureException()

    def way(self, way):
        """
        Attends the ways in the file

        :param way: Way to check
        :return: None
        """
        if self.cache and self.cache.get_pending_nodes() > 0:
            self.cache.commit()
        try:
            if self.cache:
                self.cache.add_way(way.id, way.version, way.nodes, self.convert_osmium_tags_dict(way.tags))
            if self.way_in_bbox(way.nodes):
                for tag_name in self.tags.keys():
                    key_re = self.tags[tag_name]["key_re"]
                    value_re = self.tags[tag_name]["value_re"]
                    if self.has_tag(way.tags, key_re, value_re):
                        if way.deleted:
                            add_way = True
                        elif way.version == 1:
                            add_way = True
                        else:
                            add_way = self.has_tag_changed(
                                way.id, self.convert_osmium_tags_dict(way.tags), key_re, way.version, "way")
                        if add_way:
                            if tag_name in self.stats:
                                self.stats[tag_name].add(way.changeset)
                            else:
                                self.stats[tag_name] = [way.changeset]
                            if way.changeset in self.changeset:
                                if tag_name not in self.changeset[way.changeset]["wids"]:
                                    self.changeset[way.changeset]["wids"][tag_name] = []
                                self.changeset[way.changeset]["wids"][tag_name].append(way.id)
                            else:
                                self.changeset[way.changeset] = {
                                    "changeset": way.changeset,
                                    "user": way.user,
                                    "uid": way.uid,
                                    "nids": {},
                                    "wids": {tag_name: [way.id]},
                                    "rids": {}
                                }
            self.num_ways += 1
        except Exception:
            self.sentry_client.captureException()

    def relation(self, rel):
        # print 'rel:{}'.format(self.num_rel)
        # for member in r.members:
        #    print member
        try:
            if self.cache_enabled:
                if self.cache.get_pending_nodes > 0 or self.cache.get_pending_ways > 0:
                    self.cache.commit()

            print ("rel.id {} len:{}".format(rel.id,len(rel.members)))
            if not rel.deleted and self.rel_in_bbox(rel):
                for tag_name in self.tags.keys():
                    key_re = self.tags[tag_name]["key_re"]
                    value_re = self.tags[tag_name]["value_re"]
                    if self.has_tag(rel.tags, key_re, value_re):
                        if rel.deleted:
                            add_rel = True
                        elif rel.version == 1:
                            add_rel = True
                        else:
                            rel_tags = self.convert_osmium_tags_dict(rel.tags)
                            add_rel = self.has_tag_changed(rel.id, rel_tags, key_re, rel.version, "relation")
                        if add_rel:
                            if tag_name in self.stats:
                                self.stats[tag_name].add(rel.changeset)
                            else:
                                self.stats[tag_name] = [rel.changeset]
                            if rel.changeset in self.changeset:
                                if tag_name not in self.changeset[rel.changeset]["rids"]:
                                    self.changeset[rel.changeset]["rids"][tag_name] = []
                                self.changeset[rel.changeset]["rids"][
                                    tag_name].append(rel.id)
                            else:
                                self.changeset[rel.changeset] = {
                                    "changeset": rel.changeset,
                                    "user": rel.user,
                                    "uid": rel.uid,
                                    "nids": {},
                                    "wids": {},
                                    "rids": {tag_name: [rel.id]}
                                }
            self.num_rel += 1
        except Exception as e:
            self.sentry_client.captureException()

class DbCache(object):

    def __init__(self, host, database, user, password):
        """
        Class constructor

        :param host: Host to connect
        :type host: str
        :param database: Database name to connect
        :type database: str
        :param user: User to connect to the database
        :type user: str
        :param password: Password to connect to the databse
        :type password: str
        """
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.con = psycopg2.connect(host=self.host, database=self.database, user=self.user,password=self.password)
        psycopg2.extras.register_hstore(self.con)
        self.pending_nodes = 0
        self.pending_ways = 0

    def commit(self):
        """
        Commits the data of the connection

        :return: None
        """
        self.pending_nodes = 0
        self.pending_ways = 0
        self.con.commit()

    def initialize(self):
        """
        Initializes the database
        :return: None
        """

        pkg_dir, this_filename = os.path.split(__file__)
        schema_url = os.path.join(pkg_dir, 'schema.sql')
        with open(schema_url, "r") as f:
            cur = self.con.cursor()
            sql = f.read()
            cur.execute(sql)
            self.con.commit()

    def add_node(self, identifier, version, x, y, tags):
        """
        Adds a node to the cache

        :param identifier: Node id
        :type identifier: int
        :param version:
        :type version: int
        :param x: X coordenate
        :type x: float
        :param y: Y coordenate
        :type y: float
        :param tags: Tags to store
        :type tags: dict
        :return: None
        """
        cur = self.con.cursor()
        insert_sql = """INSERT INTO cache_node
                          VALUES (%s,%s,%s,ST_SetSRID(ST_MAKEPOINT(%s, %s),4326));
                         
        """
        cur.execute(insert_sql, (identifier, version, tags, x, y))
        cur.close()
        self.pending_nodes += 1

    def get_pending_nodes(self):
        """
        Gets the pending to commit nodes

        :return: Pending nodes
        :rtype: int
        """
        return self.pending_nodes

    def get_pending_ways(self):
        """
        Gets the pending to commit ways

        :return: Pending ways
        :rtype: int
        """
        return  self.pending_ways

    def get_way(self, identifier, version=None):
        """
        Gets the way from the cache

        :param identifier: Identifier of the way
        :type identifier: int
        :param version: Version of the way
        :type version: int
        :return: Data of the way
        :rtype: dict
        """
        import json
        sql_id = """
                SELECT id,version,st_asgeojson(geom),tag
                FROM cache_way where id = %s;
                """

        sql_version = """
                SELECT id,version,st_asgeojson(geom),tag
                FROM cache_way WHERE id= %s AND version=%s;
                """
        cur = self.con.cursor()
        if version is None:
            cur.execute(sql_id, (identifier,))
        else:
            cur.execute(sql_version, (identifier, version))

        data = cur.fetchone()
        if data:
            coord = json.loads(data[2])["coordinates"]
            pairs = []
            for indx in range(len(coord))[::2]:
                pairs.append([coord[indx],coord[indx + 1]])
            return {"data":
                {
                    "id": data[0],
                    "version": data[1],
                    "coordinates": pairs,
                    "tag": data[3]
                }
            }
        return None

    def get_node(self, identifier, version=None):
        """
        Returns a node of the cache, if version is not specified returns the last version avaible

        :param identifier: Identifier of the node
        :type identifier: int
        :param version: Version of the node
        :type version: int
        :return: dict with identifier, verison,x,y
        :rtype:dict
        """
        sql_id = """
        SELECT id,version,st_x(geom),st_y(geom),tag
        FROM cache_node where id = %s;
        """

        sql_version = """
        SELECT id,version,st_x(geom),st_y(geom),tag
        FROM cache_node WHERE id= %s AND version=%s;
        """
        cur = self.con.cursor()
        if version is None:
            cur.execute(sql_id, (identifier,))
        else:
            cur.execute(sql_version, (identifier, version))

        data = cur.fetchone()
        if data:
            return {
                "data": {
                    "id": data[0],
                    "version": data[1],
                    "lat": data[2],
                    "lon": data[3],
                    "tag": data[4]
                }
            }
        return None

    def add_way(self, identifier, version, nodes, tags):
        """
        Adds a way into the cache

        :param identifier: identifier of the way to store
        :type identifier: int
        :param version: version of the way
        :type version: int
        :param nodes: Nodes to store
        :param tags: Tags to store
        :type tags: dict
        :return: None
        :rtype: None
        """
        cur = self.con.cursor()
        insert_sql = """INSERT INTO cache_way
                          VALUES (%s,%s,%s,ST_SetSRID(ST_MakeLine(ARRAY[%s]),4326));

        """
        geom = []
        has_geom = False
        for node in nodes:
            if node.location.valid():
                geom.append( "ST_MAKEPOINT({},{})".format(node.location.lat, node.location.lon))
                has_geom = True
            else:
                return False

        if has_geom:
            cur.execute(insert_sql, (identifier, version, tags, AsIs(",".join(geom))))
            self.pending_ways += 1




class ChangeWithin(object):
    """
    Class that process the OSC files
    """

    def __init__(self, host=None, db=None, user=None, password=None):
        """
        Initiliazes the class

        :param host: Database host
        :param db: Database name
        :param user: Database user
        :param password: Databse password
        """

        self.conf = {}
        self.env_vars = {}
        self.handler = ChangeHandler()
        self.osc_file = None
        self.changesets = []
        self.stats = {}

        if host is not None and db is not None and user is not None and password is not None:
            self.has_cache = True
            self.handler.set_cache(host, db, user, password)
        else:
            self.has_cache = False
            self.cache = None

        self.jinja_env = Environment(extensions=['jinja2.ext.i18n'])
        pkg_dir, this_filename = os.path.split(__file__)
        self.text_tmpl = self.get_template(os.path.join(pkg_dir, 'templates', 'text_template.txt'))
        self.html_tmpl = self.get_template(os.path.join(pkg_dir, 'templates', 'html_template.html'))

    def initialize_db(self):
        """
        Initializes the databse cache

        :return:
        """
        if self.has_cache:
            self.cache.initialize()

    def get_template(self, template_name):
        """
        Returns the template

        :param template_name: Template name as a string
        :return: Template
        """

        url = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           'templates', template_name)
        with open(url) as f:
            template_text = f.read()
        return self.jinja_env.from_string(template_text)

    def load_config(self, config=None):
        """
        Loads the configuration from the file
        :config_file: Configuration as a dict
        :return: None
        """
        if not config:
            self.env_vars = config_from_environment('bard', ['config'])
            self.conf = ConfigObj(self.env_vars["config"])
        else:
            self.conf = config

        languages = ['en']
        if 'email' in self.conf and 'language' in self.conf['email']:
            tmp = languages
            tmp.append(self.conf['email']['language'])
            languages = tmp
        if "email" not in self.conf or "url_locales" not in self.conf["email"] :
            dir_path = os.path.dirname(os.path.realpath(__file__))
            url_locales = os.path.join(dir_path, '../locales')
        else:
            url_locales = self.conf["email"]["url_locales"]

        lang = gettext.translation(
            'messages',
            localedir=url_locales,
            languages=languages)
        lang.install()
        translations = gettext.translation(
            'messages',
            localedir=url_locales,
            languages=languages)
        self.jinja_env.install_gettext_translations(translations)

        self.handler.set_bbox(*self.conf["area"]["bbox"])
        for name in self.conf["tags"]:
            key, value = self.conf["tags"][name]["tags"].split("=")
            types = self.conf["tags"][name]["tags"].split(",")
            self.stats["name"] = 0
            self.handler.set_tags(name, key, value, types)

    def process_file(self, filename=None):
        """

        :param filename: 
        :return: 
        """
        if filename is None:
            self.osc_file = get_osc()
            self.handler.apply_file(self.osc_file,
                                    osmium.osm.osm_entity_bits.CHANGESET)
        else:
            self.handler.apply_file(filename,
                                    osmium.osm.osm_entity_bits.CHANGESET)

        self.changesets = self.handler.changeset
        self.stats = self.handler.stats
        self.stats["total"] = len(self.changesets)

    def report(self):
        """
        Generates the report and sends it

        :return: None
        """
        from datetime import datetime
        print ("self.changesets:{}".format(self.changesets))
        if len(self.changesets) > 1000:
            self.changesets = self.changesets[:999]
            self.stats[
                'limit_exceed'] = 'Note: For performance reasons only the first 1000 changesets are displayed.'

        now = datetime.now()

        for state in self.stats:
            if state != "total":
                self.stats[state] = len(set(self.stats[state]))

        template_data = {
            'changesets': self.changesets,
            'stats': self.stats,
            'date': now.strftime("%B %d, %Y"),
            'tags': self.conf['tags'].keys()
        }
        html_version = self.html_tmpl.render(**template_data)
        text_version = self.text_tmpl.render(**template_data)

        if 'domain' in self.conf['mailgun'] and 'api_key' in self.conf['mailgun']:
            if "api_url" in self.conf["mailgun"]:
                url = self.conf["mailgun"]["api_url"]
            else:
                url = 'https://api.mailgun.net/v3/{0}/messages'.format(
                    self.conf['mailgun']['domain'])
            resp = requests.post(
                url,
                auth=("api", self.conf['mailgun']['api_key']),
                data={"from": "OSM Changes <mailgun@{}>".format(
                    self.conf['mailgun']['domain']),
                      "to": self.conf["email"]["recipients"].split(),
                      "subject": 'OSM building and address changes {0}'.format(
                          now.strftime("%B %d, %Y")),
                      "text": text_version,
                      "html": html_version})
            print("response:{}".format(resp.status_code))
            print("mailgun response:{}".format(resp.content))

        file_name = 'osm_change_report_{0}.html'.format(
            now.strftime('%m-%d-%y'))
        f_out = open(file_name, 'w')
        f_out.write(html_version.encode('utf-8'))
        f_out.close()
        print('Wrote {0}'.format(file_name))
        # os.unlink(self.osc_file)


if __name__ == '__main__':
    client = Client()
    try:
        c = ChangeWithin()
        c.load_config()
        c.process_file()
        c.report()
    except Exception:
        client.captureException()
