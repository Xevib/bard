from pony.orm.dbapiprovider import Converter
from psycopg2.extensions import AsIs
from shapely import wkb

class Point(object):
    """A wrapper over a dict or list
    """
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __repr__(self):
        return '<Point %r>' % self.wrapped


class Line(object):
    """A wrapper over a dict or list
    """
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __repr__(self):
        return '<Line %r>' % self.wrapped


class PointConverter(Converter):

    def init(self, kwargs):
        # Override this method to process additional positional
        # and keyword arguments of the attribute
        if self.attr is not None:
            # self.attr.args can be analyzed here
            self.args = self.attr.args
        self.srid = kwargs.pop("srid")

    def validate(self, val, obj=None):
        # convert value to the necessary type (e.g. from string)
        # validate all necessary constraints (e.g. min/max bounds)
        return val

    def py2sql(self, val):
        from psycopg2.extensions import AsIs
        # prepare the value (if necessary) to storing in the database
        return AsIs("st_setsrid(st_makepoint({},{}),{})".format(val[0], val[1], self.srid))

    def sql2py(self, value):
        # convert value (if necessary) after the reading from the db
        wkt = wkb.loads(value, True)
        return wkt.x, wkt.y

    def sql_type(self):
        # generate corresponding SQL type, based on attribute options
        return "geometry(Point, {})".format(self.srid)


class LineConverter(Converter):

    def init(self, kwargs):
        # Override this method to process additional positional
        # and keyword arguments of the attribute
        if self.attr is not None:
            # self.attr.args can be analyzed here
            self.args = self.attr.args
        self.srid = kwargs.pop("srid")

    def validate(self, val, obj=None):
        # convert value to the necessary type (e.g. from string)
        # validate all necessary constraints (e.g. min/max bounds)
        return val

    def py2sql(self, val):
        from psycopg2.extensions import AsIs
        # prepare the value (if necessary) to storing in the database
        geom = []
        for node in val:
            if node.location.valid():
                geom.append("ST_MAKEPOINT({},{})".format(node.location.lat, node.location.lon))
            else:
                return False
        return AsIs("ST_SETSRID(ST_MAKELINE(ARRAY[{}]),{})".format(",".join(geom), self.srid))

    def sql2py(self, value):
        # convert value (if necessary) after the reading from the db
        return [list(wkb.loads(value, True).coords)]


    def sql_type(self):
        # generate corresponding SQL type, based on attribute options
        return "geometry(Linestring, {})".format(self.srid)