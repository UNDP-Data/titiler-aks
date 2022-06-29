import logging
import base64
import rasterio
from urllib.request import urlopen
import json
from rio_tiler.utils import get_array_statistics
from titiler.core.factory import TilerFactory
from titiler.application.routers import mosaic, stac, tms
from titiler.application.settings import ApiSettings
from titiler.application import __version__ as titiler_version
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
# from titiler.core.middleware import (LoggerMiddleware,
#                                      LowerCaseQueryStringMiddleware,
#                                      TotalTimeMiddleware)
from titiler.application.custom import templates
from titiler.mosaic.errors import MOSAIC_STATUS_CODES
from geojson_pydantic.features import Feature, FeatureCollection
from fastapi import FastAPI, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from rio_tiler.models import BandStatistics
from titiler.core.resources.responses import JSONResponse
from starlette.responses import HTMLResponse

logging.getLogger("botocore.credentials").disabled = True
logging.getLogger("botocore.utils").disabled = True
logging.getLogger("rio-tiler").setLevel(logging.ERROR)

api_settings = ApiSettings()

def fetch_admin_geojson(url: str = None) -> dict:
    with urlopen(url) as response:
        return json.loads(response.read().decode('utf-8'))


def DatasetPathParams(
        url: str = Query(..., description="Signed raster dataset URL"),

) -> str:
    """
        FastAPI dependency function that enables
        COG endpoint to handle Azure Blob located&signed raster files
        and combine them into one  multiband GDAL VRT file.
        This allows one to use titiler's  expression parameter
        to perform simple but powerful multiband computations.
        Example
            expression=((b1>0.5)&(b3<100))/b4;

        Each url consists of a base64 encoded SAS token:

        http://localhost:8000/cog/statistics? \
        url=https://undpngddlsgeohubdev01.blob.core.windows.net/testforgeohub/HREA_Algeria_2012_v1%2FAlgeria_rade9lnmu_2012.tif?c3Y9MjAyMC0xMC0wMiZzZT0yMDIyLTAzLTA0VDE0JTNBMzIlM0E0M1omc3I9YiZzcD1yJnNpZz0lMkJUZVd0UnRScG1uNmpTQ1ZHY2JuV3dhUWMlMkJjRlp5c05ENjRDUDlyMERNRSUzRA==& \
        url=https://undpngddlsgeohubdev01.blob.core.windows.net/testforgeohub/HREA_Algeria_2012_v1%2FAlgeria_set_zscore_sy_2012.tif?c3Y9MjAyMC0xMC0wMiZzZT0yMDIyLTAzLTA0VDE0JTNBMzIlM0E0M1omc3I9YiZzcD1yJnNpZz1DTFRBQmI5aVRmV3UlMkZ0VHElMkZ4MCUyQm1hUDFUYVM5eUtDMnB3UTBjOUZmMlNBJTNE \

        The returned value is a str representing a RAM stored GDAL VRT file
        which Titiler will use to resolve the request

        Obviously the rasters need to spatially overlap. Additionaly, the VRT can be created with various params
        (spatial align, resolution, resmapling) that, to some extent can influence the performace of the server

    """

    furl, b64token = url.split('?')
    try:
        decoded_token = base64.b64decode(b64token).decode()
    except Exception:
        decoded_token = b64token
    return f'/vsicurl/{furl}?{decoded_token}'

def admin_parameters(admin_id_url: str = Query(..., description='the Azure hosted url of admin id geojson')):
    return admin_id_url

ccog = TilerFactory(path_dependency=DatasetPathParams)

@ccog.router.get(
    "/geojsonstats",
    #response_model=BandStatistics,
    response_model_exclude_none=True,
    response_class=JSONResponse,
    responses={
        200: {"description": "Return dataset's band stats for 1-3 admin levels ."}},
)
#def adminstats(src_path=Depends(ccog.path_dependency), admin_params: dict = Depends(admin_parameters)):
def adminstats(
        src_path=Depends(ccog.path_dependency),
        geojson_url: str = None
):
    # fetch the admin level boundary as geoJSON

    try:
        geojson_str = fetch_admin_geojson(geojson_url)
    except Exception as e:
        raise
    geojson = None
    try:
        geojson = FeatureCollection(**geojson_str)
    except Exception:
        geojson = Feature(**geojson_str)

    with rasterio.Env(**ccog.gdal_config):
        with ccog.reader(src_path) as src_dst:

            if isinstance(geojson, FeatureCollection):
                for i, feature in enumerate(geojson):
                    data = src_dst.feature(
                        feature.dict(exclude_none=True)
                    )
                    stats = get_array_statistics(
                        data.as_masked()
                    )

                return dict([(data.band_names[ix],BandStatistics(**stats[ix])) for ix in range(len(stats))])
            else:  # simple feature
                data = src_dst.feature(
                    geojson.dict(exclude_none=True),
                )
                stats = get_array_statistics(
                    data.as_masked(),
                )
                return dict([(data.band_names[ix],BandStatistics(**stats[ix])) for ix in range(len(stats))])

app = FastAPI(
    title=api_settings.name,
    description="A lightweight Cloud Optimized GeoTIFF tile server",
    version=titiler_version,
    root_path=api_settings.root_path,
)

if not api_settings.disable_cog:
    app.include_router(ccog.router, prefix="/cog",
                       tags=["Cloud Optimized GeoTIFF"])

if not api_settings.disable_stac:
    app.include_router(
        stac.router, prefix="/stac", tags=["SpatioTemporal Asset Catalog"]
    )

if not api_settings.disable_mosaic:
    app.include_router(mosaic.router, prefix="/mosaicjson",
                       tags=["MosaicJSON"])

app.include_router(tms.router, tags=["TileMatrixSets"])
add_exception_handlers(app, DEFAULT_STATUS_CODES)
add_exception_handlers(app, MOSAIC_STATUS_CODES)



# if api_settings.debug:
#     app.add_middleware(LoggerMiddleware, headers=True, querystrings=True)
#     app.add_middleware(TotalTimeMiddleware)
#
# if api_settings.lower_case_query_parameters:
#     app.add_middleware(LowerCaseQueryStringMiddleware)


@app.get("/health", description="Health Check", tags=["Health Check"])
def ping():
    """Health check."""
    return {"ping": "pong!"}

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing(request: Request):
    """TiTiler Landing page"""
    return templates.TemplateResponse(
        name="index.html",
        context={"request": request},
        media_type="text/html",
    )


@app.get("/routes")
def get_all_urls():
    url_list = [{"path": route.path, "name": route.name}
                for route in app.routes]
    return url_list




#Set all CORS enabled origins
if api_settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )