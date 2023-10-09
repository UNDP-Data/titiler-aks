import logging
from postgis.asyncpg import register
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
from urllib.parse import quote_plus, urlencode
import asyncpg
from functools import wraps

#_path_, fname = os.path.split(__file__)
logger = logging.getLogger(__name__)
# try:
#     POSTGRES_DSN = os.environ['POSTGRES_DSN']
# except KeyError:
#     msg = f'"POSTGRES_DSN" environment variable is not defined'
#     logger.error(msg)
#     raise Exception(msg)
ALLOWED_METHODS = 'execute', 'fetch', 'fetchval', 'fetchrow'

def cd2s(user=None, password=None, host=None, port=None, database=None, **kwargs):
    """
    Convert a dict representing a conn dict into a connection string
    :param user:
    :param password:
    :param host:
    :param port:
    :param database:
    :param kwargs: any other params as key=value. They will be added to the end as options
    :return:
    """
    if 'ssl' in kwargs:
        kwargs['sslmode'] = kwargs['ssl']
        del kwargs['ssl']
    try:
        return f'postgres://{quote_plus(user)}:{quote_plus(password)}@{quote_plus(host)}:{port}/{database}?{urlencode(kwargs)}'
    except KeyError:
        raise


def cs2d(url=None):
    """
    Convert a connection string to dict
    :param url:
    :return:
    """

    # otherwise parse the url as normal
    config = {}

    url = urlparse.urlparse(url)

    # Split query strings from path.
    path = url.path[1:]
    if '?' in path and not url.query:
        path, query = path.split('?', 2)
    else:
        path, query = path, url.query

    # Handle postgres percent-encoded paths.
    hostname = url.hostname or ''
    if '%2f' in hostname.lower():
        # Switch to url.netloc to avoid lower cased paths
        hostname = url.netloc
        if "@" in hostname:
            hostname = hostname.rsplit("@", 1)[1]
        if ":" in hostname:
            hostname = hostname.split(":", 1)[0]
        hostname = hostname.replace('%2f', '/').replace('%2F', '/')

    port = url.port
    if query:
        if 'sslmode' in query:
            query = query.replace('sslmode', 'ssl')
        d = dict(urlparse.parse_qsl(query))

        config.update(d)

    # Update with environment configuration.
    config.update({
        'database': urlparse.unquote(path or ''),
        'user': urlparse.unquote(url.username or ''),
        'password': urlparse.unquote(url.password or ''),
        'host': hostname,
        'port': port or '',

    })

    return config

def print_pg_message(conn_obj, msg):
    logger.info(msg)


def connect(func):
    """
    Decorator function that handles the connection to PostgreSQL DB
    If the decorated function possesses a conn_obj in **kwargs it patches it with
    a listener to log the messages from PG server
    If the dsn is supplied the decorator creates a pool and a connection to the serves specified in DB and
    closes the pool ad the connection after the decorated function is called
    """

    @wraps(func)
    async def wrapper(**kwargs):
        if not 'conn_obj' in kwargs:

            reuse = False
            dsn = kwargs.get('dsn', None)
            if dsn is None:
                raise ValueError(f'dsn argument have to be provided to be able to connect to DB')
            pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=1, command_timeout=60, )
            logger.debug(f'connecting to DB')
            conn_obj = await pool.acquire(timeout=10)
        else:
            reuse = True
            conn_obj = kwargs['conn_obj']

        #register
        if 'register' in globals():
            logger.debug('registering postgis')
            await register(connection=conn_obj)

        # add log listener
        if not print_pg_message in conn_obj._log_listeners:
            conn_obj.add_log_listener(print_pg_message)

        kwargs['conn_obj'] = conn_obj
        result = await func(**kwargs)
        if print_pg_message in conn_obj._log_listeners:
            conn_obj.remove_log_listener(print_pg_message)
        if reuse is False:
            logger.debug(f'going to close the connection')
            conn_obj = kwargs['conn_obj']
            await conn_obj.close()
            if 'pool' in locals():
                await pool.close()
        else:
            logger.debug(f'going to keep the connection')
        return result

    return wrapper

@connect
async def check_pg_version(dsn=None, conn_obj=None):
    """
    Checks the postgres version. Uses connect decorator


    """
    sql_query = 'SELECT PostGIS_Full_Version();'
    logger.info(sql_query)
    result = await conn_obj.fetchval(sql_query)
    logger.info(result)



@connect
async def run_query(dsn=None, conn_obj=None, sql_query=None, method='execute'):
    """
    Run a SQL query represented by sql_query against the context represented by conn_obj
    :param conn_obj: asyncpg connection object
    :param sql_query: str, SQL query
    :param method: str, the asyncpg method used to perform the query. One of
    'execute', 'fetch', 'fetch_val', 'fetch_all'
    :return:
    """
    assert conn_obj is not None, f'invalid conn_obj={conn_obj}'
    assert sql_query not in ('', None), f'Invalid sql_query={sql_query}'
    assert method not in ('', None), f'Invalid method={method}'
    assert method in ALLOWED_METHODS, f'Invalid method={method}. Valid option are {",".join(ALLOWED_METHODS)}'
    m = getattr(conn_obj, method)
    return await m(sql_query)


def test():
    logger.info('here')


