import unittest
from changewithin import ChangeWithin
from changewithin import ChangeHandler
from osmium.osm import Location, WayNodeList, Node
from changewithin import get_state
from changewithin.changewithin import DbCache
import osmapi
import psycopg2
import sys
if sys.version_info[0] == 2:
    import mock
else:
    from unittest.mock import MagicMock

class LibTest(unittest.TestCase):
    """
    Unitest for the lif module
    """

    def test_get_state(self):
        """
        Tests get_state 
        :return: None
        """

        state = get_state()
        self.assertNotEqual(state, "")


class CacheTest(unittest.TestCase):
    """
    Test suite for cache
    """

    def setUp(self):
        """
        Setup database cache test

        :return:
        """
        self.cache = DbCache("localhost", "changewithin", "postgres", "postgres")
        self.connection = psycopg2.connect(host="localhost", database="changewithin", user="postgres", password="postgres")

    def tearDown(self):
        """

        :return:
        """
        self.connection.close()

    def test_initialize(self):
        """
        Test cache initialization

        :return:
        """
        self.cur = self.connection.cursor()
        self.cur.execute("SELECT * FROM cache_node;")

    def test_add_node(self):
        """
        Tests how to add a node to the  cache

        :return:
        """
        self.cur = self.connection.cursor()
        self.cur.execute("DELETE FROM cache_node;")
        self.connection.commit()
        self.cache.add_node(123, 1, 1.23, 2.42, {})
        self.cache.commit()
        self.connection.commit()
        self.cur.execute("SELECT count(*) from cache_node;")
        data = self.cur.fetchall()
        self.assertEqual(data[0][0], 1)

    def test_check_pending_nodes(self):
        """
        Tests the pending nodes managment

        :return:
        """
        pending = self.cache.get_pending_nodes()
        self.cache.add_node(1234, 1, 1.23, 2.42, {})
        new_pending = self.cache.get_pending_nodes()
        self.assertEqual(pending+1, new_pending)
        self.cache.commit()
        zero_pending = self.cache.get_pending_nodes()
        self.assertEqual(0, zero_pending)

    def test_check_pending_ways(self):
        """

        :return:
        """
        l1 = Location(1, 1)
        l2 = Location(2, 2)

        if sys.version_info[0] == 2:
            n1 = mock.MagicMock(id=1, location=l1)
            n2 = mock.MagicMock(id=2, location=l2)
        else:
            n1 = MagicMock(id=1, location=l1)
            n2 = MagicMock(id=2, location=l2)

        if sys.version_info[0] == 2:
            nl = [n1, n2]
        else:
            nl = [n1, n2]

        self.cur = self.connection.cursor()
        pending = self.cache.get_pending_ways()
        self.cache.add_way(10, 2, nl, {})
        pending_new = self.cache.get_pending_ways()
        self.assertEqual(pending+1, pending_new)
        self.cache.commit()
        pending_zero = self.cache.get_pending_ways()
        self.assertEqual(0, pending_zero)

    def test_add_way(self):
        """
        Tests how to add a way to the cache

        :return: None
        """

        l1 = Location(1, 1)
        l2 = Location(2, 2)

        if sys.version_info[0] == 2:
            n1 = mock.MagicMock(id=1,location=l1)
            n2 = mock.MagicMock(id=2,location=l2)
        else:
            n1 = MagicMock(id=1,location=l1)
            n2 = MagicMock(id=2,location=l2)

        if sys.version_info[0] == 2:
            nl = [n1, n2]
        else:
            nl = [n1, n2]

        self.cur = self.connection.cursor()
        self.cur.execute("DELETE FROM cache_way;")
        self.connection.commit()
        self.cache.add_way(1, 2, nl, {})
        self.cache.commit()

        self.cur.execute("SELECT count(*) from cache_way;")
        data = self.cur.fetchall()
        self.assertEqual(data[0][0], 1)
        self.cache.commit()
        way = self.cache.get_way(1, 2)
        expected_data = {
            "data": {
                "id": 1,
                "version": 2,
                "tag": {},
                "coordinates": [[[1, 1], [2, 2]]]
            }

        }
        self.assertEqual(expected_data, way)
        way2 = self.cache.get_way(1)
        self.assertEqual(way2, expected_data)
        way_none = self.cache.get_way(23212)
        self.assertIsNone(way_none)

    def test_get_node(self):
        """
        Test the get_node method

        :return: None
        """

        self.cur = self.connection.cursor()

        self.cache.add_node(42, 1, 1.23, 2.42,{"building": "yes"})
        self.cache.add_node(42, 2, 2.22, 0.23,{"building": "yes", "name":"test"})
        self.cache.add_node(43, 1, 2.99, 0.99,{})
        self.connection.commit()
        nod_42 = {
            "data":{
                "id": 42,
                "version": 2,
                "lat": 2.22,
                "lon": 0.23,
                "tag": {
                    "building": "yes",
                    "name": "test"

                }
            }
        }

        nod_43 = {
            "data": {
                "id": 43,
                "version": 1,
                "lat": 2.99,
                "lon": 0.99,
                "tag": {}
            }
        }
        self.assertEqual(self.cache.get_node(42, 2), nod_42)
        self.assertEqual(self.cache.get_node(43), nod_43)
        self.assertIsNone(self.cache.get_node(1))


class HandlerTest(unittest.TestCase):
    """
    Unittest for the handler
    """
    
    def setUp(self):
        """
        Initialization
        """
        self.handler = ChangeHandler()

    def test_in_bbox(self):
        """
        Tests the location_in_bbox of handler
        :return: None
        """

        self.handler.set_bbox(41.9933, 2.8576, 41.9623, 2.7847)
        l = Location(2.81372, 41.98268)
        self.assertTrue(self.handler.location_in_bbox(l))

    def test_set_tags(self):
        """
        Test set_tags of handler
        :return: None
        """

        self.handler.set_tags("test", "key_tag", "element_tag", ["nodes", "ways"])
        self.assertTrue("test" in self.handler.tags)

    def test_set_bbox(self):
        """
        Test set_bbox of handler
        :return: None 
        """

        self.handler.set_bbox(41.9933, 2.8576, 41.9623, 2.7847)
        self.assertEqual(self.handler.north, 41.9933)
        self.assertEqual(self.handler.east, 2.8576)
        self.assertEqual(self.handler.south, 41.9623)
        self.assertEqual(self.handler.west, 2.7847)

    def test_has_changed(self):
        osm_api = osmapi.OsmApi()
        old_tags = osm_api.WayGet(360662139, 1)["tag"]
        ret = self.handler.has_tag_changed(360662139, old_tags, "surface", 3, "way")
        self.assertTrue(ret)
        old_tags = osm_api.WayGet(360662139, 2)["tag"]
        ret = self.handler.has_tag_changed(360662139, old_tags, "surface", 3, "way")
        self.assertFalse(ret)


class ChangesWithinTest(unittest.TestCase):
    """
    Initest for changeswithin using osmium
    """
    def setUp(self):
        """
        Constructor
        """
        self.cw = ChangeWithin()

    def test_osc1(self):
        """
        Tests load of test1.osc
        :return: None
        """
        conf = {
            'area': {
                'bbox': ['41.9933', '2.8576', '41.9623', '2.7847']
            },
            'tags': {
                'all': {
                    'tags': '.*=.*',
                    'type': 'node,way'
                }
            },
            "url_locales": "locales"
        }
        self.cw.conf = conf
        self.cw.load_config(conf)
        self.cw.handler.set_bbox('41.9933', '2.8576', '41.9623', '2.7847')
        self.assertEqual(self.cw.handler.north, 41.9933)
        self.assertEqual(self.cw.handler.east, 2.8576)
        self.assertEqual(self.cw.handler.south, 41.9623)
        self.assertEqual(self.cw.handler.west, 2.7847)
        self.cw.handler.set_tags("all", ".*", ".*", ["node", "way"])
        self.cw.process_file("test/test1.osc")
        self.assertTrue("all" in self.cw.handler.tags)
        self.assertTrue(49033608 in self.cw.changesets)

    def test_osc1_multiple(self):
        """
        Tests load of test1.osc
        :return: None
        """
        conf = {
            'area': {
                'bbox': ['41.9933', '2.8576', '41.9623', '2.7847']
            },
            'tags': {
                'highway': {
                    'tags': "highway=.*",
                    'type': 'node,way'
                },
                "housenumber": {
                    "tags": "addr:housenumber=.*",
                    "type": "way,node"
                },
                "building": {
                    "tags": "building=public",
                    "type": "way,node"
                }
            },
            "url_locales": "locales"
        }
        self.cw.conf = conf
        self.cw.load_config(conf)
        self.cw.handler.set_bbox('41.9933', '2.8576', '41.9623', '2.7847')
        self.assertEqual(self.cw.handler.north, 41.9933)
        self.assertEqual(self.cw.handler.east, 2.8576)
        self.assertEqual(self.cw.handler.south, 41.9623)
        self.assertEqual(self.cw.handler.west, 2.7847)
        self.cw.handler.set_tags("all", ".*", ".*", ["node", "way"])
        self.cw.process_file("test/test2.osc")
        self.assertTrue("all" in self.cw.handler.tags)
        self.assertEqual(len(set(self.cw.stats["all"])), len(self.cw.stats["all"]))
        self.assertEqual(len(set(self.cw.stats["building"])), len(self.cw.stats["building"]))
        self.assertTrue(48595327 in self.cw.changesets)

    def test_relation(self):
        """
        Tests load of test1.osc
        :return: None
        """
        conf = {
            'area': {
                'bbox': ['41.9933', '2.8576', '41.9623', '2.7847']
            },
            'tags': {
                'highway': {
                    'tags': "highway=.*",
                    'type': 'node,way'
                },
                "housenumber": {
                    "tags": "addr:housenumber=.*",
                    "type": "way,node"
                },
                "building": {
                    "tags": "building=public",
                    "type": "way,node"
                }
            },
            "url_locales": "locales"
        }
        self.cw.conf = conf
        self.cw.load_config(conf)
        self.cw.handler.set_bbox('41.9933', '2.8576', '41.9623', '2.7847')
        self.assertEqual(self.cw.handler.north, 41.9933)
        self.assertEqual(self.cw.handler.east, 2.8576)
        self.assertEqual(self.cw.handler.south, 41.9623)
        self.assertEqual(self.cw.handler.west, 2.7847)
        self.cw.handler.set_tags("all", ".*", ".*", ["node", "way"])
        self.cw.process_file("test/test_rel.osc")
        self.assertTrue(41928815 in self.cw.changesets)
        self.assertTrue(343535 in self.cw.changesets[41928815]["rids"]["all"])


class ChangesWithinTestCache(unittest.TestCase):
    """
    Initest for changeswithin using osmium
    """
    def setUp(self):
        """
        Constructor
        """
        self.cw = ChangeWithin(
            host="localhost",
            user="postgres",
            db="changewithin",
            password="test"
        )


    def test_osc1(self):
        """
        Tests load of test1.osc
        :return: None
        """
        conf = {
            'area': {
                'bbox': ['41.9933', '2.8576', '41.9623', '2.7847']
            },
            'tags': {
                'all': {
                    'tags': '.*=.*',
                    'type': 'node,way'
                }
            },

            "url_locales": "locales"
        }
        self.cw.conf = conf
        self.cw.load_config(conf)
        self.cw.handler.set_bbox('41.9933', '2.8576', '41.9623', '2.7847')
        self.assertEqual(self.cw.handler.north, 41.9933)
        self.assertEqual(self.cw.handler.east, 2.8576)
        self.assertEqual(self.cw.handler.south, 41.9623)
        self.assertEqual(self.cw.handler.west, 2.7847)
        self.cw.handler.set_tags("all", ".*", ".*", ["node", "way"])
        self.cw.process_file("test/test1.osc")
        self.assertTrue("all" in self.cw.handler.tags)
        self.assertTrue(49033608 in self.cw.changesets)

    def test_osc1_multiple(self):
        """
        Tests load of test1.osc
        :return: None
        """
        conf = {
            'area': {
                'bbox': ['41.9933', '2.8576', '41.9623', '2.7847']
            },
            'tags': {
                'highway': {
                    'tags': "highway=.*",
                    'type': 'node,way'
                },
                "housenumber": {
                    "tags": "addr:housenumber=.*",
                    "type": "way,node"
                },
                "building": {
                    "tags": "building=public",
                    "type": "way,node"
                }
            },
            "url_locales": "locales"
        }
        self.cw.conf = conf
        self.cw.load_config(conf)
        self.cw.handler.set_bbox('41.9933', '2.8576', '41.9623', '2.7847')
        self.assertEqual(self.cw.handler.north, 41.9933)
        self.assertEqual(self.cw.handler.east, 2.8576)
        self.assertEqual(self.cw.handler.south, 41.9623)
        self.assertEqual(self.cw.handler.west, 2.7847)
        self.cw.handler.set_tags("all", ".*", ".*", ["node", "way"])
        self.cw.process_file("test/test2.osc")
        self.assertTrue("all" in self.cw.handler.tags)
        self.assertEqual(len(set(self.cw.stats["all"])), len(self.cw.stats["all"]))
        self.assertEqual(len(set(self.cw.stats["building"])), len(self.cw.stats["building"]))
        self.assertTrue(48595327 in self.cw.changesets)

    def test_relation(self):
        """
        Tests load of test1.osc
        :return: None
        """
        conf = {
            'area': {
                'bbox': ['41.9933', '2.8576', '41.9623', '2.7847']
            },
            'tags': {
                'highway': {
                    'tags': "highway=.*",
                    'type': 'node,way'
                },
                "housenumber": {
                    "tags": "addr:housenumber=.*",
                    "type": "way,node"
                },
                "building": {
                    "tags": "building=public",
                    "type": "way,node"
                }
            },
            "url_locales": "locales"
        }
        self.cw.conf = conf
        self.cw.load_config(conf)
        self.cw.handler.set_bbox('41.9933', '2.8576', '41.9623', '2.7847')
        self.assertEqual(self.cw.handler.north, 41.9933)
        self.assertEqual(self.cw.handler.east, 2.8576)
        self.assertEqual(self.cw.handler.south, 41.9623)
        self.assertEqual(self.cw.handler.west, 2.7847)
        self.cw.handler.set_tags("all", ".*", ".*", ["node", "way"])
        self.cw.process_file("test/test_rel.osc")
        self.assertTrue(41928815 in self.cw.changesets)
        self.assertTrue(343535 in self.cw.changesets[41928815]["rids"]["all"])


if __name__ == '__main__':
    unittest.main()
