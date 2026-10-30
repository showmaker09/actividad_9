"""Módulo de Infraestructura: Gestión de Conexión a Base de Datos en la Nube.

Implementa el Patrón Singleton Thread-Safe para administrar la conexión
a MongoDB Atlas sin duplicar pools de conexiones.
"""
import os
import sys
import threading
from typing import Optional
from dotenv import load_dotenv
import certifi
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ConfigurationError, PyMongoError

# Carga de variables de entorno (.env prioritario, base_Datos.env como respaldo)
load_dotenv(".env")
load_dotenv("base_Datos.env")


class CloudDatabaseManager:
    """Administrador Singleton Thread-Safe para la conexión a MongoDB Atlas.
    
    Garantiza una única instancia del cliente de base de datos a lo largo de toda
    la aplicación, optimizando el uso de recursos y sockets de red.
    """
    _instance: Optional["CloudDatabaseManager"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "CloudDatabaseManager":
        """Implementa instanciación perezosa thread-safe con Double-Checked Locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CloudDatabaseManager, cls).__new__(cls)
                    cls._instance._inicializado = False
        return cls._instance

    def __init__(self) -> None:
        """Inicializa la conexión a MongoDB Atlas y ejecuta verificación por Ping."""
        if getattr(self, "_inicializado", False):
            return

        with self._lock:
            if getattr(self, "_inicializado", False):
                return

            # Carga de credenciales obligatorias sin hardcoding
            self._uri: Optional[str] = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
            self._db_name: str = os.getenv("DB_NAME") or os.getenv("Data_Base") or "biblioteca_virtual"

            if not self._uri:
                raise ConfigurationError(
                    "Error de Configuración: 'MONGODB_URI' no está definida en el archivo .env. "
                    "Por favor configure sus credenciales en .env o base_Datos.env"
                )

            try:
                # Conexión resiliente a MongoDB Atlas
                self._client: MongoClient = MongoClient(
                    self._uri,
                    tls=True,
                    tlsCAFile=certifi.where(),
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    retryWrites=True
                )

                # Ping de verificación obligatorio
                self._client.admin.command("ping")
                self._db: Database = self._client[self._db_name]
                self._inicializado = True
                print(f"[CloudDatabaseManager] Conexión establecida exitosamente con MongoDB Atlas.")
                print(f"[CloudDatabaseManager] Base de datos activa: '{self._db_name}'.")

            except ConnectionFailure as cf:
                raise ConnectionFailure(
                    f"Fallo de conexión al cluster MongoDB Atlas: {cf}"
                ) from cf
            except PyMongoError as pe:
                raise PyMongoError(
                    f"Error general de PyMongo al inicializar la base de datos: {pe}"
                ) from pe

    @property
    def db(self) -> Database:
        """Retorna el objeto Database de MongoDB."""
        return self._db

    @property
    def client(self) -> MongoClient:
        """Retorna el cliente MongoClient activo."""
        return self._client

    def close(self) -> None:
        """Cierra el pool de conexiones con MongoDB Atlas de manera ordenada."""
        with self._lock:
            if getattr(self, "_client", None) is not None:
                self._client.close()
                self._inicializado = False
                CloudDatabaseManager._instance = None
                print("[CloudDatabaseManager] Conexión cerrada correctamente.")

