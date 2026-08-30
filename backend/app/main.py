from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import content, health, ingest, insights, predict, recommend

app = FastAPI(title="ContentIQ API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(content.router)
app.include_router(recommend.router)
app.include_router(insights.router)
app.include_router(predict.router)