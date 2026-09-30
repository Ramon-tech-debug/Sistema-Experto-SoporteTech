"""
Capa de persistencia en SQLite para el sistema experto.

Guarda cada consulta con sus hechos originales, hechos derivados,
conclusiones y traza de reglas activadas. Toda la informacion se
serializa como JSON dentro de columnas TEXT para mantener el esquema
simple y evitar tablas adicionales por cada tipo de hecho posible.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

RUTA_BASE_DATOS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datos", "sistema_experto.db"
)

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS consultas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    estado TEXT NOT NULL,
    hechos_originales TEXT NOT NULL,
    hechos_derivados TEXT NOT NULL,
    conclusiones TEXT NOT NULL,
    reglas_activadas TEXT NOT NULL,
    contradicciones TEXT NOT NULL,
    hechos_faltantes_relevantes TEXT NOT NULL
);
"""


class RepositorioConsultas:
    """Acceso a la base de datos SQLite de consultas del sistema experto."""

    def __init__(self, ruta_base_datos: str = RUTA_BASE_DATOS):
        self.ruta_base_datos = ruta_base_datos
        os.makedirs(os.path.dirname(self.ruta_base_datos), exist_ok=True)
        self._inicializar_esquema()

    @contextmanager
    def _conectar(self):
        conexion = sqlite3.connect(self.ruta_base_datos)
        conexion.row_factory = sqlite3.Row
        try:
            with conexion:
                yield conexion
        finally:
            conexion.close()

    def _inicializar_esquema(self) -> None:
        with self._conectar() as conexion:
            conexion.execute(_ESQUEMA)
            conexion.commit()

    def guardar_consulta(
        self,
        estado: str,
        hechos_originales: Dict[str, Any],
        hechos_derivados: Dict[str, Any],
        conclusiones: List[Dict[str, str]],
        reglas_activadas: List[Dict[str, Any]],
        contradicciones: List[str],
        hechos_faltantes_relevantes: List[str],
    ) -> int:
        fecha = datetime.now().isoformat()
        with self._conectar() as conexion:
            cursor = conexion.execute(
                """
                INSERT INTO consultas (
                    fecha, estado, hechos_originales, hechos_derivados,
                    conclusiones, reglas_activadas, contradicciones,
                    hechos_faltantes_relevantes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fecha,
                    estado,
                    json.dumps(hechos_originales, ensure_ascii=False),
                    json.dumps(hechos_derivados, ensure_ascii=False),
                    json.dumps(conclusiones, ensure_ascii=False),
                    json.dumps(reglas_activadas, ensure_ascii=False),
                    json.dumps(contradicciones, ensure_ascii=False),
                    json.dumps(hechos_faltantes_relevantes, ensure_ascii=False),
                ),
            )
            conexion.commit()
            return int(cursor.lastrowid)

    def obtener_consulta(self, id_consulta: int) -> Optional[Dict[str, Any]]:
        with self._conectar() as conexion:
            fila = conexion.execute(
                "SELECT * FROM consultas WHERE id = ?", (id_consulta,)
            ).fetchone()
        if fila is None:
            return None
        return self._fila_a_diccionario(fila)

    def listar_consultas(self) -> List[Dict[str, Any]]:
        with self._conectar() as conexion:
            filas = conexion.execute(
                "SELECT * FROM consultas ORDER BY id DESC"
            ).fetchall()
        return [self._fila_a_diccionario(fila) for fila in filas]

    @staticmethod
    def _fila_a_diccionario(fila: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": fila["id"],
            "fecha": fila["fecha"],
            "estado": fila["estado"],
            "hechos_originales": json.loads(fila["hechos_originales"]),
            "hechos_derivados": json.loads(fila["hechos_derivados"]),
            "conclusiones": json.loads(fila["conclusiones"]),
            "reglas_activadas": json.loads(fila["reglas_activadas"]),
            "contradicciones": json.loads(fila["contradicciones"]),
            "hechos_faltantes_relevantes": json.loads(fila["hechos_faltantes_relevantes"]),
        }
