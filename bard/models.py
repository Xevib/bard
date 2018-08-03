from pony.orm import *
from pony.orm.ormtypes import *
from bard.postgis import *
from bard.bard import db


class Cache_Node(db.Entity):
    id = PrimaryKey(int, auto=True)
    osm_id = Required(int, sql_type="BIGINT")
    version = Optional(int)
    tag = Optional(Json)
    geom = Optional(Point, srid=4326)


class Cache_Way(db.Entity):
    osm_id = Required(int,sql_type="BIGINT")
    version = Optional(int)
    tag = Optional(Json)
    geom = Optional(Line, srid=4326)
