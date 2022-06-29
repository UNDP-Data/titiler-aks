__version__='0.0.3'
import azure.functions as func
from .wmts import app

def main(
    req: func.HttpRequest, context: func.Context,
) -> func.HttpResponse:
    return func.AsgiMiddleware(app).handle(req, context)
