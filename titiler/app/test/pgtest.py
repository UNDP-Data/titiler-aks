from app import pg
import os
import asyncio
import numpy as np
from martin_config import db
import postgis
try:
    POSTGRES_DSN = os.environ['POSTGRES_DSN']
except KeyError:
    msg = f'"POSTGRES_DSN" environment variable is not defined'
    raise Exception(msg)

def bbox(postgis_geom=None, bounds=None):
    if isinstance(postgis_geom, postgis.Point):
        if bounds is None:
            bounds = [postgis_geom.x, postgis_geom.x, postgis_geom.y, postgis_geom.y]
        else:
            x, y = postgis_geom.coords[:2]
            if x < bounds[0]: bounds[0] = x
            if x > bounds[1]: bounds[1] = x
            if y < bounds[2]: bounds[2] = y
            if y > bounds[3]: bounds[3] = y
            return bounds
    else:
        for g in postgis_geom:
            r = bbox(postgis_geom=g, bounds=bounds)
            if r:
                bounds = r
    return bounds


@pg.connect
async def session(dsn=None, conn_obj=None):


    # await pg.run_query(conn_obj=conn_obj, sql_query='set search_path="admin"')
    schemas = await db.list_schemas(conn_obj=conn_obj)
    tables = await db.list_tables(conn_obj=conn_obj, schema='admin')

    cols = await db.get_table_columns(conn_obj=conn_obj,table='admin.admin0')
    print(cols[0]['properties'])
    r = await db.run_query(conn_obj=conn_obj, sql_query="select geom, country_name from admin.admin0 where iso3cd='ISR'", method='fetchrow')
    print(type(r['geom']),  r['country_name'])
    b = bbox(r['geom'])
    print(b)


    r = await db.run_query(conn_obj=conn_obj, sql_query='select country_name, iso3cd, isoadm from admin.admin0', method='fetchrow')
    print(r)



if __name__ == '__main__':
    import logging
    logging.basicConfig()
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.info('START')
    # asyncio.run(
    #     pg.check_pg_version(dsn=POSTGRES_DSN)
    #
    # )
    # asyncio.run(
    #     pg.run_query(
    #                     dsn=POSTGRES_DSN,
    #                     sql_query='set search_path=admin;',
    #                     method='execute'
    #                  )
    #             )
    asyncio.run(
        session(dsn=POSTGRES_DSN)
    )