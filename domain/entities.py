"""Entidades del Dominio para el Sistema de Inventario de Libros.

Principio de Arquitectura Limpia:
Este módulo no contiene dependencias de infraestructura ni llamadas a MongoDB.
Define únicamente las reglas de negocio puras e invariantes del dominio.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class RegistroDescarga:
    """Entidad de auditoría que representa una descarga realizada por un estudiante."""
    matricula: str
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entidad a un diccionario serializable."""
        return {
            "matricula": self.matricula,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegistroDescarga":
        """Crea una instancia de RegistroDescarga a partir de un diccionario."""
        return cls(
            matricula=data.get("matricula", ""),
            timestamp=data.get("timestamp")
        )


@dataclass
class Libro:
    """Entidad de dominio que representa un libro digital en el inventario eclesiástico."""
    id: str
    titulo: str
    autor: str
    categoria: str
    stock: int
    estado: str = "Disponible"
    historial_descargas: List[RegistroDescarga] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Valida las invariantes del modelo de dominio."""
        if self.stock < 0:
            raise ValueError(f"El stock no puede ser negativo: {self.stock}")
        
        # Sincroniza el estado con el nivel de stock
        if self.stock == 0:
            self.estado = "Agotado"
        elif self.estado not in ("Disponible", "Agotado"):
            self.estado = "Disponible"

    def esta_disponible(self) -> bool:
        """Determina si el libro puede ser descargado según las reglas de negocio."""
        return self.stock > 0 and self.estado == "Disponible"

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la entidad a formato diccionario compatible con persistencia."""
        return {
            "_id": self.id,
            "titulo": self.titulo,
            "autor": self.autor,
            "categoria": self.categoria,
            "stock": self.stock,
            "estado": self.estado,
            "historial_descargas": [r.to_dict() for r in self.historial_descargas]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Libro":
        """Reconstituye una entidad Libro a partir de un diccionario de persistencia."""
        historial_raw = data.get("historial_descargas", []) or []
        historial = [
            RegistroDescarga.from_dict(h) if isinstance(h, dict) else h
            for h in historial_raw
        ]
        return cls(
            id=str(data.get("_id", "")),
            titulo=data.get("titulo", ""),
            autor=data.get("autor", ""),
            categoria=data.get("categoria", "General"),
            stock=int(data.get("stock", 0)),
            estado=data.get("estado", "Disponible"),
            historial_descargas=historial
        )

