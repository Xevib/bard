from pony.orm import *
from pony.orm.ormtypes import *
from .postgis import *

db = Database()


class Cache_Node(db.Entity):
    id = PrimaryKey(int, auto=True)
    osm_id = Required(int, sql_type="BIGINT", index=True)
    version = Optional(int, index=True)
    tag = Optional(Json)
    geom = Optional(Point, srid=4326)


class Cache_Way(db.Entity):
    osm_id = Required(int,sql_type="BIGINT")
    version = Optional(int)
    tag = Optional(Json)
    geom = Optional(Line, srid=4326)


class BardUser(db.Entity):
    id = PrimaryKey(int,auto=True)
    login = Required(str, unique=True)
    password = Required(str)
    users = Set('UserTags')


class UserTags(db.Entity):
    id = PrimaryKey(int, auto=True)
    description = Optional(str)
    tags = Required(str)
    node = Required(bool)
    way = Required(bool)
    relation = Required(bool)
    bbox = Required(str)
    user = Required(BardUser)
    states = Set('ResultTags')


class ResultTags(db.Entity):
    id = PrimaryKey(int, auto=True)
    timestamp = Required(datetime)
    user_tags = Required(UserTags)
    changesets = Required(Json)