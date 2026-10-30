"""Módulo de Aplicación: Servicio de Inventario y Casos de Uso.

Orquesta la lógica de negocio y los casos de uso de la Biblioteca Virtual,
manteniéndose desacoplado de los detalles específicos de la base de datos (MongoDB).
"""
from typing import Optional, Dict, Any, Tuple
from domain.entities import Libro
from infrastructure.libro_repository import LibroRepository


class InventarioService:
    """Servicio de aplicación que orquesta las operaciones de inventario de libros.
    
    Aplica el principio de Inversión de Dependencias (DIP) y Responsabilidad Única (SRP):
    No contiene lógica de persistencia directa ni operadores de base de datos;
    delega la persistencia atómica al repositorio.
    """

    def __init__(self, libro_repository: Optional[LibroRepository] = None) -> None:
        """Inicializa el servicio inyectando el repositorio de libros."""
        self._libro_repo = libro_repository or LibroRepository()

    def descargar_libro(self, id_libro: str, matricula_estudiante: str) -> Dict[str, Any]:
        """Caso de Uso: Procesar la solicitud de descarga de un libro por un estudiante.

        Valida los parámetros de negocio y delega la ejecución atómica in-situ al repositorio.

        Args:
            id_libro: Identificador único del libro solicitado.
            matricula_estudiante: Matrícula académica del solicitante.

        Returns:
            Dict[str, Any]: Resultado estructurado de la operación con estado y mensaje.
        """
        # Validación de parámetros a nivel de aplicación
        id_libro = id_libro.strip() if id_libro else ""
        matricula_estudiante = matricula_estudiante.strip() if matricula_estudiante else ""

        if not id_libro:
            return {
                "exito": False,
                "mensaje": "Error: El identificador del libro es obligatorio.",
                "id_libro": id_libro,
                "matricula": matricula_estudiante
            }

        if not matricula_estudiante:
            return {
                "exito": False,
                "mensaje": "Error: La matrícula del estudiante es requerida.",
                "id_libro": id_libro,
                "matricula": matricula_estudiante
            }

        # Delegación al repositorio para ejecución atómica en Atlas
        exito = self._libro_repo.procesar_descarga_libro(id_libro, matricula_estudiante)

        if exito:
            return {
                "exito": True,
                "mensaje": f"Descarga procesada exitosamente para la matrícula '{matricula_estudiante}'.",
                "id_libro": id_libro,
                "matricula": matricula_estudiante
            }
        else:
            return {
                "exito": False,
                "mensaje": f"Descarga rechazada: Libro '{id_libro}' agotado o no disponible para la matrícula '{matricula_estudiante}'.",
                "id_libro": id_libro,
                "matricula": matricula_estudiante
            }

    def registrar_o_actualizar_libro(self, libro: Libro) -> None:
        """Caso de Uso: Registra o inicializa un libro en el inventario."""
        self._libro_repo.upsert_libro(libro.to_dict())

    def consultar_libro(self, id_libro: str) -> Optional[Libro]:
        """Caso de Uso: Obtiene la entidad Libro desde el inventario."""
        datos = self._libro_repo.obtener_libro(id_libro)
        if not datos:
            return None
        return Libro.from_dict(datos)

    def reiniciar_stock(self, id_libro: str, stock_inicial: int = 3) -> bool:
        """Caso de Uso: Restablece el stock de un libro para propósitos de prueba."""
        return self._libro_repo.restablecer_stock(id_libro, stock_inicial)

