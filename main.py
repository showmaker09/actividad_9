"""Punto de Entrada y Suite de Pruebas Concurrentes.

Actividad 9: Refactorización Atómica de Inventario (Biblioteca Virtual Eclesiástica)
Demuestra la eliminación de Race Conditions y el patrón Read-Modify-Write
mediante mutaciones in-situ atómicas en MongoDB Atlas.
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any

# Asegurar compatibilidad de codificación en consola Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from domain.entities import Libro
from infrastructure.database import CloudDatabaseManager
from infrastructure.libro_repository import LibroRepository
from application.inventario_service import InventarioService


def json_serial(obj: Any) -> Any:
    """Serializador para objetos no estándar en JSON como datetime."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Tipo no serializable: {type(obj)}")


def ejecutar_pruebas() -> None:
    """Ejecuta el flujo completo de prueba concurrente y verificación de atomicidad."""
    print("=" * 80)
    print(" ACTIVIDAD 9: REFACTORIZACIÓN ATÓMICA DE INVENTARIO - MONGODB ATLAS")
    print(" Sistema de Biblioteca Virtual Eclesiástica / E-Church Store")
    print("=" * 80)

    # 1. Inicialización de componentes bajo Clean Architecture
    print("\n[Paso 1] Inicializando componentes y conexión Singleton...")
    db_manager = CloudDatabaseManager()
    libro_repo = LibroRepository(db_manager)
    servicio = InventarioService(libro_repo)

    # 2. Preparación del Dataset de Prueba (libro_test)
    ID_LIBRO = "LIB-TEOL-001"
    STOCK_INICIAL = 3

    libro_inicial = Libro(
        id=ID_LIBRO,
        titulo="Teología Sistemática: Doctrina Bíblica Fundamental",
        autor="Louis Berkhof",
        categoria="Teología Eclesiástica",
        stock=STOCK_INICIAL,
        estado="Disponible",
        historial_descargas=[]
    )

    print(f"\n[Paso 2] Insertando/Restableciendo documento de prueba '{ID_LIBRO}' en Atlas...")
    servicio.registrar_o_actualizar_libro(libro_inicial)

    # Verificación del estado inicial
    doc_inicial = libro_repo.obtener_libro(ID_LIBRO)
    print("\n--- ESTADO INICIAL EN MONGODB ATLAS ---")
    print(f"ID del Libro    : {doc_inicial.get('_id')}")
    print(f"Título          : {doc_inicial.get('titulo')}")
    print(f"Stock Inicial   : {doc_inicial.get('stock')} unidades")
    print(f"Estado Inicial  : {doc_inicial.get('estado')}")
    print(f"Descargas Previas: {len(doc_inicial.get('historial_descargas', []))}")

    # 3. Simulación de Alta Concurrencia (Destrucción de Race Conditions)
    TOTAL_PETICIONES = 10
    estudiantes = [f"EST-2026-{i:03d}" for i in range(1, TOTAL_PETICIONES + 1)]

    print(f"\n[Paso 3] Lanzando {TOTAL_PETICIONES} solicitudes de descarga CONCURRENTES...")
    print(f"         (Stock disponible = {STOCK_INICIAL} | Solicitudes = {TOTAL_PETICIONES})")
    print("         Ejecutando threads simultáneos con ThreadPoolExecutor...")

    resultados_exitosos: List[Dict[str, Any]] = []
    resultados_fallidos: List[Dict[str, Any]] = []

    t_inicio = time.time()
    with ThreadPoolExecutor(max_workers=TOTAL_PETICIONES) as executor:
        # Lanzamiento concurrente de descargas
        futuros = {
            executor.submit(servicio.descargar_libro, ID_LIBRO, matricula): matricula
            for matricula in estudiantes
        }

        for futuro in as_completed(futuros):
            res = futuro.result()
            matricula = res["matricula"]
            if res["exito"]:
                resultados_exitosos.append(res)
                print(f"  [OK] Descarga AUTORIZADA  -> Estudiante: {matricula}")
            else:
                resultados_fallidos.append(res)
                print(f"  [X]  Descarga RECHAZADA    -> Estudiante: {matricula} (Stock Agotado)")

    t_total = time.time() - t_inicio
    print(f"\nTiempo total de ejecución concurrente: {t_total:.3f} segundos.")

    # 4. Verificación y Auditoría del Documento Final en MongoDB Atlas
    print("\n[Paso 4] Consultando documento final en MongoDB Atlas...")
    doc_final = libro_repo.obtener_libro(ID_LIBRO)

    stock_final = doc_final.get("stock")
    estado_final = doc_final.get("estado")
    historial_final = doc_final.get("historial_descargas", [])
    total_descargas_registradas = len(historial_final)

    print("\n--- REPORTE FINAL DE VERIFICACIÓN DE ATOMICIDAD ---")
    print(f"Stock Final en Atlas             : {stock_final} (Esperado: 0)")
    print(f"Estado Final del Libro           : '{estado_final}' (Esperado: 'Agotado')")
    print(f"Descargas Exitosas Aprobadas     : {len(resultados_exitosos)} (Esperado: {STOCK_INICIAL})")
    print(f"Descargas Rechazadas             : {len(resultados_fallidos)} (Esperado: {TOTAL_PETICIONES - STOCK_INICIAL})")
    print(f"Registros en 'historial_descargas': {total_descargas_registradas} (Esperado: {STOCK_INICIAL})")

    # 5. Aserciones de Integridad
    assert stock_final == 0, f"ERROR CRÍTICO: El stock final es {stock_final}, debería ser 0!"
    assert estado_final == "Agotado", f"ERROR: El estado final es '{estado_final}', debería ser 'Agotado'!"
    assert len(resultados_exitosos) == STOCK_INICIAL, (
        f"ERROR: Se autorizaron {len(resultados_exitosos)} descargas pero solo había {STOCK_INICIAL} disponibles!"
    )
    assert total_descargas_registradas == STOCK_INICIAL, (
        f"ERROR: Se registraron {total_descargas_registradas} descargas en historial, se esperaban {STOCK_INICIAL}!"
    )
    assert stock_final >= 0, "ERROR: Condición de carrera detectada, el stock fue menor que 0!"

    print("\n" + "=" * 80)
    print(" [EXITO] TODAS LAS PRUEBAS DE ATOMICIDAD Y CONCURRENCIA FUERON EXITOSAS")
    print("     - Cero sobreventas (No Overselling).")
    print("     - Eliminación total del antipatrón Read-Modify-Write.")
    print("     - Mutación in-situ atómica ejecutada en el nodo primario de Atlas.")
    print("=" * 80)

    # 6. Mostrar el documento JSON final directamente de MongoDB
    print("\nDocumento BSON final en la colección 'inventario_libros':")
    print(json.dumps(doc_final, indent=2, default=json_serial, ensure_ascii=False))


if __name__ == "__main__":
    try:
        ejecutar_pruebas()
    except Exception as e:
        print(f"\n[ERROR] Ocurrió una excepción durante la ejecución: {e}")
        raise
