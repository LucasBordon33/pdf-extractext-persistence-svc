from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.config import Settings


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="pdf-extractext-persistence-svc")
    app.state.settings = settings
    app.include_router(api_v1_router)
    return app


settings = Settings()
app = create_app(settings)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
