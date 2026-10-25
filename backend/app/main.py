from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import configure_logging, get_settings

configure_logging()
app = FastAPI(title="UK Wind Forecast Procurement API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origin_list,
                   allow_methods=["GET"], allow_headers=["*"])
app.include_router(router)
