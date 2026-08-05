from fastapi import FastAPI

from app.routers import health, ingest

app = FastAPI(title="ContentIQ API")

app.include_router(health.router)
app.include_router(ingest.router)