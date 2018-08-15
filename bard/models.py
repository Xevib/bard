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


class User(db.Entity):
    id = PrimaryKey(int,auto=True, index=True)
    login = Required(str)
    password = Required(str)


#class UserTags(db.Entity):
#    id = PrimaryKey(int,auto=True, index=True)
#    description = Optional(str)
#    tags = Required(str)
#    node = Required(bool)
#    way = Required(bool)
#    relation = Required(bool)
#    bbox = Required(str)