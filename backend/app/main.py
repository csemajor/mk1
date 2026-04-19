from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .db.database import close_mongo_connection, connect_to_mongo
from .routes.auth_routes import router as auth_router
from .routes.booking_routes import router as booking_router
from .routes.review_routes import router as review_router
from .routes.service_routes import router as service_router
from .routes.test_routes import router as test_router
from .routes.user_routes import router as user_router
from .routes.wishlist_routes import router as wishlist_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title="Eventra API", lifespan=lifespan)

cors_raw = settings.CORS_ORIGINS.strip()
if not cors_raw or cors_raw == "*":
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]

allow_credentials = cors_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(test_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(wishlist_router)
app.include_router(service_router)
app.include_router(booking_router)
app.include_router(review_router)
