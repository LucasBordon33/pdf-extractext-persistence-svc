from fastapi import Request

from app.adapters.mongo.client import MongoClient
from app.config import Settings
from app.domain.services.persistence_service import PersistenceService


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_mongo_client(request: Request) -> MongoClient | None:
    return getattr(request.app.state, "mongo_client", None)


def get_persistence_service(request: Request) -> PersistenceService:
    service: PersistenceService = request.app.state.persistence_service
    return service
