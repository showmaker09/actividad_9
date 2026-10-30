"""Módulo de Infraestructura - Persistencia y adaptadores externos."""
from .database import CloudDatabaseManager
from .libro_repository import LibroRepository

__all__ = ["CloudDatabaseManager", "LibroRepository"]

