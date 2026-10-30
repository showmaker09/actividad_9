"""Módulo de Infraestructura: Repositorio de Libros con Mutación Atómica In-Situ.

Implementa la persistencia y operaciones directas en MongoDB Atlas siguiendo
estrictamente los principios de atomicidad para eliminar condiciones de carrera
y transferencias innecesarias de datos por la red.
"""
from typing import Optional, Dict, Any
from pymongo.collection import Collection
from pymongo.database import Database
from .database import CloudDatabaseManager


class LibroRepository:
    """Repositorio responsable de las operaciones de persistencia de Libros en MongoDB.
    
    Implementa el método crítico 'procesar_descarga_libro' utilizando una única
    operación de actualización con aggregation pipeline, garantizando la mutación
    in-situ atómica en el nodo primario de MongoDB Atlas.
    """
    COLECCION_NOMBRE = "inventario_libros"

    def __init__(self, db_manager: Optional[CloudDatabaseManager] = None) -> None:
        """Inicializa el repositorio asociándolo a la base de datos."""
        self._db_manager = db_manager or CloudDatabaseManager()
        self._coleccion: Collection = self._db_manager.db[self.COLECCION_NOMBRE]

    @property
    def coleccion(self) -> Collection:
        """Retorna la colección subyacente de pymongo."""
        return self._coleccion

    def procesar_descarga_libro(self, id_libro: str, matricula_estudiante: str) -> bool:
        """Procesa la descarga atómica de un libro reduciendo el stock y registrando auditoría.

        REGLAS DE IMPLEMENTACIÓN NO NEGOCIABLES:
        1. Prohibido utilizar 'find_one()', 'find()' o ciclos para leer el stock.
        2. Prohibido realizar cálculos aritméticos en Python sobre el stock.
        3. Se realiza una ÚNICA llamada a 'update_one()'.
        4. Filtro obligatorio: `{"_id": id_libro, "stock": {"$gt": 0}}` para prevenir
           sobreventas concurrentes a nivel de hardware/motor de almacenamiento.
        5. Pipeline de actualización (MongoDB 4.2+):
           - Decrementa el stock con `$add: ["$stock", -1]`.
           - Evalúa condicionalmente `$cond` para actualizar `estado` a 'Agotado' si el nuevo stock <= 0.
           - Concatena atómicamente el nuevo subdocumento de auditoría a `historial_descargas` con `$concatArrays`.

        Args:
            id_libro: Identificador único del libro (_id).
            matricula_estudiante: Matrícula del alumno que solicita la descarga.

        Returns:
            bool: True si la descarga fue autorizada y persistida atómicamente;
                  False si no había stock disponible o el libro no existe.
        """
        # Filtro estricto que destruye la Race Condition: solo coincide si hay stock > 0
        filtro = {
            "_id": id_libro,
            "stock": {"$gt": 0}
        }

        # Pipeline de mutación atómica in-situ en el nodo primario
        pipeline = [
            {
                "$set": {
                    # Decremento atómico del stock directamente en el motor de almacenamiento
                    "stock": {"$add": ["$stock", -1]},

                    # Actualización condicional del estado evaluando el stock resultante
                    "estado": {
                        "$cond": {
                            "if": {"$lte": [{"$add": ["$stock", -1]}, 0]},
                            "then": "Agotado",
                            "else": "Disponible"
                        }
                    },

                    # Inserción atómica del registro de auditoría sin transferir el array previo
                    "historial_descargas": {
                        "$concatArrays": [
                            {"$ifNull": ["$historial_descargas", []]},
                            [{
                                "matricula": matricula_estudiante,
                                "timestamp": "$$NOW"  # Timestamp nativo del servidor primario Atlas
                            }]
                        ]
                    }
                }
            }
        ]

        # Una sola operación atómica en MongoDB Atlas
        resultado = self._coleccion.update_one(filtro, pipeline)

        # modified_count > 0 confirma que el documento cumplió la condición y fue mutado
        return resultado.modified_count > 0

    def obtener_libro(self, id_libro: str) -> Optional[Dict[str, Any]]:
        """Consulta el estado actual de un libro por su ID."""
        return self._coleccion.find_one({"_id": id_libro})

    def upsert_libro(self, libro_data: Dict[str, Any]) -> None:
        """Inserta o actualiza por completo el documento inicial para pruebas."""
        id_libro = libro_data.get("_id")
        self._coleccion.replace_one({"_id": id_libro}, libro_data, upsert=True)

    def restablecer_stock(self, id_libro: str, stock_inicial: int = 3) -> bool:
        """Restablece el stock y estado de un libro para propósitos de pruebas."""
        resultado = self._coleccion.update_one(
            {"_id": id_libro},
            {
                "$set": {
                    "stock": stock_inicial,
                    "estado": "Disponible" if stock_inicial > 0 else "Agotado",
                    "historial_descargas": []
                }
            }
        )
        return resultado.matched_count > 0

    def eliminar_libro(self, id_libro: str) -> bool:
        """Elimina un libro de la colección (útil para limpieza de pruebas)."""
        resultado = self._coleccion.delete_one({"_id": id_libro})
        return resultado.deleted_count > 0

