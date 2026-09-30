"""
Pruebas de persistencia del repositorio SQLite.

Cubren el requisito de verificacion: "comprobar que el historial persiste
al reiniciar". Se simula un reinicio de la aplicacion creando una SEGUNDA
instancia de RepositorioConsultas apuntando al mismo archivo .db: si los
datos siguen ahi, la persistencia es real y no solo un cache en memoria.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.repositorio import RepositorioConsultas  # noqa: E402


def _ruta_temporal() -> str:
    descriptor, ruta = tempfile.mkstemp(suffix=".db")
    os.close(descriptor)
    os.remove(ruta)  # el repositorio debe poder crear el archivo desde cero
    return ruta


def test_guardar_y_recuperar_una_consulta():
    ruta = _ruta_temporal()
    try:
        repo = RepositorioConsultas(ruta)
        id_guardado = repo.guardar_consulta(
            estado="resuelto",
            hechos_originales={"led_power_encendido": "no"},
            hechos_derivados={"router_sin_energia": True},
            conclusiones=[
                {
                    "regla_id": "R05",
                    "conclusion": "Router sin alimentacion electrica",
                    "recomendacion": "Revise el cable de poder.",
                }
            ],
            reglas_activadas=[{"regla_id": "R04"}, {"regla_id": "R05"}],
            contradicciones=[],
            hechos_faltantes_relevantes=[],
        )
        consulta = repo.obtener_consulta(id_guardado)
        assert consulta is not None
        assert consulta["estado"] == "resuelto"
        assert consulta["hechos_originales"] == {"led_power_encendido": "no"}
        assert consulta["conclusiones"][0]["regla_id"] == "R05"
    finally:
        os.remove(ruta)


def test_consulta_inexistente_devuelve_none():
    ruta = _ruta_temporal()
    try:
        repo = RepositorioConsultas(ruta)
        assert repo.obtener_consulta(9999) is None
    finally:
        os.remove(ruta)


def test_historial_persiste_al_reiniciar():
    """Simula un reinicio: una nueva instancia del repositorio, mismo archivo .db."""
    ruta = _ruta_temporal()
    try:
        repo_antes_del_reinicio = RepositorioConsultas(ruta)
        id_guardado = repo_antes_del_reinicio.guardar_consulta(
            estado="resuelto",
            hechos_originales={"ping_gateway_exitoso": "si", "ping_dns_exitoso": "si", "resolucion_dns_exitosa": "si"},
            hechos_derivados={},
            conclusiones=[
                {
                    "regla_id": "R21",
                    "conclusion": "La conexion a internet funciona correctamente",
                    "recomendacion": "No se detectan fallas.",
                }
            ],
            reglas_activadas=[{"regla_id": "R21"}],
            contradicciones=[],
            hechos_faltantes_relevantes=[],
        )
        del repo_antes_del_reinicio  # se descarta la instancia, como al detener el backend

        # "Reinicio": se crea una instancia nueva sobre el mismo archivo .db.
        repo_despues_del_reinicio = RepositorioConsultas(ruta)
        historial = repo_despues_del_reinicio.listar_consultas()
        assert len(historial) == 1
        assert historial[0]["id"] == id_guardado
        assert historial[0]["conclusiones"][0]["regla_id"] == "R21"
    finally:
        os.remove(ruta)


def test_listar_consultas_orden_descendente():
    ruta = _ruta_temporal()
    try:
        repo = RepositorioConsultas(ruta)
        ids = []
        for _ in range(3):
            ids.append(
                repo.guardar_consulta(
                    estado="sin_evidencia",
                    hechos_originales={},
                    hechos_derivados={},
                    conclusiones=[],
                    reglas_activadas=[],
                    contradicciones=[],
                    hechos_faltantes_relevantes=["router_encendido"],
                )
            )
        historial = repo.listar_consultas()
        assert [fila["id"] for fila in historial] == list(reversed(ids))
    finally:
        os.remove(ruta)


if __name__ == "__main__":
    import traceback

    pruebas = [
        obj
        for nombre, obj in list(globals().items())
        if nombre.startswith("test_") and callable(obj)
    ]
    fallidas = 0
    for prueba in pruebas:
        try:
            prueba()
            print(f"OK   {prueba.__name__}")
        except AssertionError:
            fallidas += 1
            print(f"FALLO {prueba.__name__}")
            traceback.print_exc()
    print(f"\n{len(pruebas) - fallidas}/{len(pruebas)} pruebas superadas")
    if fallidas:
        raise SystemExit(1)
