from fastapi import FastAPI, HTTPException, Body, Header, Request
from fastapi.responses import JSONResponse

# from starlette.middleware.sessions import SessionMiddleware
from typing import Dict, Union
from pydantic import BaseModel, ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os

# from admin import init
from nicegui import ui

# Secret key has to be set as environment variable
if os.environ.get("SECRET_KEY") is None:
    raise Exception("Environment variable SECRET_KEY is not set.")

json_data = {}

app = FastAPI()
# init(app, json_data)


# Initialize limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Define Pydantic schema for JSON data
class JsonData(BaseModel):
    __root__: Dict[str, Union[str, "JsonData"]]


# Initialize json_data with environment variables beginning with "DATA_"
for key, value in os.environ.items():
    if key.startswith("DATA_"):
        # Split key into levels separated by underscores
        levels = key.replace("DATA_", "").split("_")
        # Create nested dictionary
        nested_dict = json_data
        for level in levels[:-1]:
            if level not in nested_dict:
                nested_dict[level.lower()] = {}
            nested_dict = nested_dict[level.lower()]
        # Add value to nested dictionary
        nested_dict[levels[-1].lower()] = value
print(json_data)


@app.get("/config")
async def read_json_data():
    """
    Returns the contents of the JSON data.
    """
    return JSONResponse(
        content=json_data,
        media_type="application/json",
        headers={"Cache-Control": "max-age=60"},
    )


@app.put("/config")
@limiter.limit("1/minute")
async def update_json_data(
    request: Request, data: JsonData = Body(...), secret_key: str = Header(None)
):
    """
    Updates the contents of the JSON data.
    """
    # Check if the secret header is present and has the correct value
    if secret_key != os.environ.get("SECRET_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Validate incoming data against schema
    try:
        JsonData(**data.dict())
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {e}")

    # Merge existing data with incoming data
    json_data.update(data)

    return {"message": "JSON data updated successfully"}


# Add auto-generated OpenAPI endpoint
@app.get("/docs")
async def get_docs():
    return {"detail": "Documentation available at /redoc or /docs"}


# Add auto-generated ReDoc endpoint
@app.get("/redoc")
async def get_redoc():
    return FastAPI().redoc_html


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(content={"error": exc.detail}, status_code=exc.status_code)


# Start development server if module is executed
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
