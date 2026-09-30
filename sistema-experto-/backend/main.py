"""
API FastAPI del sistema experto de diagnostico de conectividad en redes
domesticas e internet.

Rutas:
    GET  /salud            -> verificar disponibilidad de la API
    GET  /reglas           -> consultar la base de conocimiento
    POST /consultas        -> validar hechos, inferir y guardar
    GET  /consultas        -> listar historial (resumen)
    GET  /consultas/{id}   -> consultar hechos, resultados y traza completa
"""

from __future__ import annotations

from dataclasses import asdict
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.modelos import (
    ConclusionSalida,
    ConsultaResumen,
    ConsultaRespuesta,
    PasoTrazaSalida,
    SaludRespuesta,
    SolicitudConsulta,
)
from backend.motor import MotorInferencia
from backend.repositorio import RepositorioConsultas

app = FastAPI(
    title="Sistema Experto - Diagnostico de Conectividad",
    description=(
        "API de un sistema experto basado en reglas para diagnosticar "
        "problemas de conectividad en redes domesticas e internet."
    ),
    version="1.0.0",
)

# Permite que el frontend NiceGUI (otro proceso/puerto) consuma la API
# durante el desarrollo local.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

motor = MotorInferencia()
repositorio = RepositorioConsultas()


@app.get("/salud", response_model=SaludRespuesta)
def salud() -> SaludRespuesta:
    """Verifica que la API y la base de conocimiento esten disponibles."""
    return SaludRespuesta(
        estado="disponible",
        tema=motor.tema,
        cantidad_reglas=len(motor.obtener_reglas()),
    )


@app.get("/reglas")
def obtener_reglas() -> List[dict]:
    """Devuelve la base de conocimiento completa (para la pantalla de reglas)."""
    return motor.obtener_reglas()


@app.post("/consultas", response_model=ConsultaRespuesta)
def crear_consulta(solicitud: SolicitudConsulta) -> ConsultaRespuesta:
    """
    Recibe los hechos capturados en el formulario, ejecuta el motor de
    inferencia y guarda la consulta completa (entradas, salidas y traza)
    en SQLite.
    """
    hechos_para_motor = solicitud.hechos.a_memoria_de_trabajo()
    resultado = motor.ejecutar(hechos_para_motor)

    reglas_activadas_dict = [asdict(paso) for paso in resultado.reglas_activadas]

    id_guardado = repositorio.guardar_consulta(
        estado=resultado.estado,
        hechos_originales=resultado.hechos_originales,
        hechos_derivados=resultado.hechos_derivados,
        conclusiones=resultado.conclusiones,
        reglas_activadas=reglas_activadas_dict,
        contradicciones=resultado.contradicciones,
        hechos_faltantes_relevantes=resultado.hechos_faltantes_relevantes,
    )

    consulta_guardada = repositorio.obtener_consulta(id_guardado)
    return _fila_a_respuesta(consulta_guardada)


@app.get("/consultas", response_model=List[ConsultaResumen])
def listar_consultas() -> List[ConsultaResumen]:
    """Lista el historial de consultas en orden descendente por fecha."""
    filas = repositorio.listar_consultas()
    resumenes: List[ConsultaResumen] = []
    for fila in filas:
        conclusion_principal = (
            fila["conclusiones"][0]["conclusion"] if fila["conclusiones"] else None
        )
        resumenes.append(
            ConsultaResumen(
                id=fila["id"],
                fecha=fila["fecha"],
                estado=fila["estado"],
                conclusion_principal=conclusion_principal,
                cantidad_reglas_activadas=len(fila["reglas_activadas"]),
            )
        )
    return resumenes


@app.get("/consultas/{id_consulta}", response_model=ConsultaRespuesta)
def obtener_consulta(id_consulta: int) -> ConsultaRespuesta:
    """Devuelve el detalle completo (hechos, resultados y traza) de una consulta."""
    fila = repositorio.obtener_consulta(id_consulta)
    if fila is None:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
    return _fila_a_respuesta(fila)


def _fila_a_respuesta(fila: dict) -> ConsultaRespuesta:
    """Convierte una fila del repositorio (dict con JSON ya decodificado) en el modelo de salida."""
    return ConsultaRespuesta(
        id=fila["id"],
        fecha=fila["fecha"],
        hechos_originales=fila["hechos_originales"],
        hechos_derivados=fila["hechos_derivados"],
        conclusiones=[ConclusionSalida(**c) for c in fila["conclusiones"]],
        reglas_activadas=[PasoTrazaSalida(**p) for p in fila["reglas_activadas"]],
        estado=fila["estado"],
        contradicciones=fila["contradicciones"],
        hechos_faltantes_relevantes=fila["hechos_faltantes_relevantes"],
    )
