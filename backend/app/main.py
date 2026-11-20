from fastapi import FastAPI
from app.health import router
from app.catalog import router as catalog_router
from app.auth import router as auth_router
app = FastAPI()

app.include_router(router, prefix="/api")
app.include_router(catalog_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
