"""FastAPI adapter for ReAgent application services."""

from .app import app, create_app
from .composition import ApplicationContainer

__all__ = ["ApplicationContainer", "app", "create_app"]
