from fastapi import Request

from app.adapters.mongo.client import MongoClient
from app.config import Settings


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_mongo_client(request: Request) -> MongoClient | None:
    return getattr(request.app.state, "mongo_client", None)
