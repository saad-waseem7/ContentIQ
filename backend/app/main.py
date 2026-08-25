from fastapi import FastAPI

from app.routers import content, health, ingest, recommend

app = FastAPI(title="ContentIQ API")

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(content.router)
app.include_router(recommend.router)