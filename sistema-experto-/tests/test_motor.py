"""
Pruebas automatizadas del motor de inferencia.

Cubren:
- Encadenamiento de al menos tres reglas en una misma consulta.
- Terminacion del ciclo de inferencia (no entra en bucle infinito).
- Aislamiento entre consultas (una consulta no deja hechos en la siguiente).
- Resolucion de prioridad entre reglas candidatas.
- Deteccion de contradicciones.
- Evidencia insuficiente cuando faltan datos.
- Que un hecho desconocido nunca se trate como falso.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.motor import MotorInferencia  # noqa: E402


def _motor() -> MotorInferencia:
    return MotorInferencia()


def test_carga_minimo_20_reglas():
    motor = _motor()
    assert len(motor.obtener_reglas()) >= 20


def test_encadenamiento_de_al_menos_tres_reglas():
    motor = _motor()
    resultado = motor.ejecutar(
        {
            "ip_asignada": "si",
            "ping_gateway_exitoso": "no",
            "otros_dispositivos_con_internet": "si",
        }
    )
    ids_activados = [paso.regla_id for paso in resultado.reglas_activadas]
    assert ids_activados == ["R11", "R12", "R13"]
    assert resultado.estado == "resuelto"
    assert resultado.conclusiones[0]["regla_id"] == "R13"


def test_terminacion_no_entra_en_bucle_infinito():
    motor = _motor()
    # Un conjunto de hechos que dispara varias cadenas simultaneamente;
    # el motor debe terminar (la prueba falla por timeout si no lo hace).
    resultado = motor.ejecutar(
        {
            "led_power_encendido": "no",
            "reinicio_router_reciente": "no",
            "cable_ethernet_conectado": "no",
            "wifi_activado_en_dispositivo": "no",
            "dispositivo_ve_red_wifi": "no",
        }
    )
    # Ninguna regla debe dispararse dos veces.
    ids_activados = [paso.regla_id for paso in resultado.reglas_activadas]
    assert len(ids_activados) == len(set(ids_activados))


def test_aislamiento_entre_consultas():
    motor = _motor()
    resultado1 = motor.ejecutar({"led_power_encendido": "no", "reinicio_router_reciente": "no"})
    assert "router_sin_energia" in resultado1.hechos_derivados

    # Una segunda consulta, sin ese hecho, no debe heredar nada de la anterior.
    resultado2 = motor.ejecutar({"ip_asignada": "si"})
    assert "router_sin_energia" not in resultado2.hechos_derivados
    assert "router_sin_energia" not in resultado2.hechos_originales


def test_prioridad_resuelve_reglas_candidatas():
    motor = _motor()
    # led_power_encendido=no dispara tanto R04 (deriva router_sin_energia,
    # prioridad 95) como potencialmente otras reglas; se verifica que la
    # regla de mayor prioridad se evalua primero.
    resultado = motor.ejecutar({"led_power_encendido": "no", "reinicio_router_reciente": "no"})
    assert resultado.reglas_activadas[0].regla_id == "R04"


def test_deteccion_de_contradicciones():
    motor = _motor()
    resultado = motor.ejecutar({"router_encendido": "no", "ip_asignada": "si"})
    assert resultado.estado == "contradiccion"
    assert len(resultado.contradicciones) == 1
    assert resultado.reglas_activadas == []


def test_evidencia_insuficiente():
    motor = _motor()
    resultado = motor.ejecutar({"router_encendido": "si"})
    assert resultado.estado == "sin_evidencia"
    assert resultado.reglas_activadas == []
    assert len(resultado.hechos_faltantes_relevantes) > 0


def test_hecho_desconocido_no_se_trata_como_falso():
    motor = _motor()
    # No se envia contrasena_wifi_correcta -> es desconocida, NO falsa.
    # Por lo tanto R06 (que requiere contrasena_wifi_correcta == 'no') NO
    # debe dispararse solo porque el dato este ausente.
    resultado = motor.ejecutar({"dispositivo_ve_red_wifi": "si"})
    ids_activados = [paso.regla_id for paso in resultado.reglas_activadas]
    assert "R06" not in ids_activados
    assert resultado.estado == "sin_evidencia"


def test_conclusion_todo_funciona_correctamente():
    motor = _motor()
    resultado = motor.ejecutar(
        {
            "ping_gateway_exitoso": "si",
            "ping_dns_exitoso": "si",
            "resolucion_dns_exitosa": "si",
        }
    )
    assert resultado.estado == "resuelto"
    ids_conclusiones = [c["regla_id"] for c in resultado.conclusiones]
    assert "R21" in ids_conclusiones


def test_fallo_dns_por_vpn():
    motor = _motor()
    resultado = motor.ejecutar(
        {
            "ping_gateway_exitoso": "si",
            "ping_dns_exitoso": "si",
            "resolucion_dns_exitosa": "no",
            "vpn_activa": "si",
        }
    )
    ids_conclusiones = [c["regla_id"] for c in resultado.conclusiones]
    # Debe dispararse tanto el diagnostico general de fallo DNS (R18->R19)
    # como el diagnostico especifico de VPN (R22).
    assert "R19" in ids_conclusiones
    assert "R22" in ids_conclusiones


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
