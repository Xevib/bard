CREATE TABLE cache_way (id BIGINT, version INTEGER, tag hstore);
SELECT AddGeometryColumn ('public','cache_way','geom',4326,'LINESTRING',2, false);
CREATE INDEX ON cache_node(id);
CREATE INDEX ON cache_node(version);