"""
Motor de inferencia del sistema experto de diagnostico de conectividad.

Implementa encadenamiento hacia adelante (forward chaining) puro en Python,
sin usar eval() sobre las condiciones de las reglas. Las reglas se cargan
desde backend/reglas.json y se comparan mediante funciones explicitas por
operador.

Conceptos clave manejados aqui:
- Memoria de trabajo: diccionario de hechos conocidos para UNA consulta.
- Un dato "desconocido" simplemente no esta presente en la memoria de
  trabajo; nunca se asume falso.
- Cada regla se dispara como maximo una vez por consulta.
- Conflictos (varias reglas aplicables a la vez) se resuelven por mayor
  prioridad primero; en caso de empate, por orden de identificador (R01
  antes que R02, etc.).
- Contradicciones logicas explicitas se detectan antes de inferir.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

RUTA_REGLAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reglas.json")

# Operadores soportados por las condiciones de las reglas.
# No se usa eval(): cada operador es una funcion explicita.
_OPERADORES = {
    "eq": lambda actual, esperado: actual == esperado,
    "neq": lambda actual, esperado: actual != esperado,
}

# Pares de hechos logicamente incompatibles: si ambos estan presentes con
# los valores indicados, se reporta una contradiccion antes de inferir.
# Cada entrada: (hecho_a, valor_a, hecho_b, valor_b, mensaje)
_CONTRADICCIONES = [
    (
        "router_encendido", "no", "ip_asignada", "si",
        "El router esta apagado pero se indica que el dispositivo tiene "
        "una direccion IP asignada; ambos hechos no pueden ser ciertos a la vez."
    ),
    (
        "router_encendido", "no", "ping_gateway_exitoso", "si",
        "El router esta apagado pero se indica que el ping a la puerta de "
        "enlace fue exitoso; sin router encendido no puede haber respuesta."
    ),
    (
        "ip_asignada", "no", "ping_gateway_exitoso", "si",
        "No hay direccion IP asignada pero se indica que el ping a la "
        "puerta de enlace fue exitoso; sin IP no es posible enviar trafico."
    ),
    (
        "ping_gateway_exitoso", "no", "ping_dns_exitoso", "si",
        "El ping a la puerta de enlace fallo pero el ping a un servidor "
        "DNS externo fue exitoso; sin alcanzar la puerta de enlace no "
        "puede salir trafico hacia internet."
    ),
    (
        "ping_dns_exitoso", "no", "resolucion_dns_exitosa", "si",
        "El ping al servidor DNS fallo pero se indica que la resolucion "
        "de nombres fue exitosa; sin respuesta del servidor DNS no puede "
        "resolverse ningun dominio."
    ),
]


@dataclass
class PasoTraza:
    """Un paso registrado en la traza de ejecucion de una consulta."""
    regla_id: str
    descripcion: str
    condiciones_evaluadas: List[Dict[str, Any]]
    tipo_resultado: str
    hecho_derivado: Optional[str] = None
    explicacion: str = ""
    fuente: str = ""


@dataclass
class ResultadoInferencia:
    hechos_originales: Dict[str, Any]
    hechos_derivados: Dict[str, Any]
    conclusiones: List[Dict[str, str]] = field(default_factory=list)
    reglas_activadas: List[PasoTraza] = field(default_factory=list)
    contradicciones: List[str] = field(default_factory=list)
    hechos_faltantes_relevantes: List[str] = field(default_factory=list)
    estado: str = "sin_evidencia"  # sin_evidencia | resuelto | contradiccion


class MotorInferencia:
    """Motor de encadenamiento hacia adelante sobre una base de reglas JSON."""

    def __init__(self, ruta_reglas: str = RUTA_REGLAS):
        self.ruta_reglas = ruta_reglas
        self.reglas: List[Dict[str, Any]] = []
        self.tema: str = ""
        self._cargar_reglas()

    def _cargar_reglas(self) -> None:
        with open(self.ruta_reglas, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        self.tema = datos.get("tema", "")
        self.reglas = datos.get("reglas", [])
        if len(self.reglas) < 20:
            raise ValueError(
                f"La base de conocimiento debe tener al menos 20 reglas; "
                f"tiene {len(self.reglas)}."
            )

    def obtener_reglas(self) -> List[Dict[str, Any]]:
        """Devuelve las reglas tal como estan definidas (para GET /reglas)."""
        return self.reglas

    # ------------------------------------------------------------------
    # Deteccion de contradicciones
    # ------------------------------------------------------------------
    @staticmethod
    def detectar_contradicciones(hechos: Dict[str, Any]) -> List[str]:
        mensajes: List[str] = []
        for hecho_a, valor_a, hecho_b, valor_b, mensaje in _CONTRADICCIONES:
            if hechos.get(hecho_a) == valor_a and hechos.get(hecho_b) == valor_b:
                mensajes.append(mensaje)
        return mensajes

    # ------------------------------------------------------------------
    # Evaluacion de condiciones
    # ------------------------------------------------------------------
    @staticmethod
    def _condicion_se_cumple(condicion: Dict[str, Any], hechos: Dict[str, Any]) -> Optional[bool]:
        """
        Evalua una condicion contra la memoria de trabajo.

        Devuelve:
            True  -> la condicion se cumple
            False -> la condicion no se cumple (el hecho existe pero con otro valor)
            None  -> el hecho es desconocido (no esta en la memoria de trabajo);
                     NUNCA se interpreta como falso.
        """
        nombre_hecho = condicion["hecho"]
        if nombre_hecho not in hechos:
            return None
        operador = _OPERADORES[condicion["operador"]]
        return operador(hechos[nombre_hecho], condicion["valor"])

    def _regla_aplicable(self, regla: Dict[str, Any], hechos: Dict[str, Any]) -> Optional[bool]:
        """
        True si todas las condiciones se cumplen, False si alguna se
        cumple explicitamente en falso, None si falta evidencia (al menos
        una condicion depende de un hecho desconocido y ninguna es falsa).
        """
        hay_desconocido = False
        for condicion in regla["condiciones"]:
            resultado = self._condicion_se_cumple(condicion, hechos)
            if resultado is False:
                return False
            if resultado is None:
                hay_desconocido = True
        if hay_desconocido:
            return None
        return True

    # ------------------------------------------------------------------
    # Encadenamiento hacia adelante
    # ------------------------------------------------------------------
    def ejecutar(self, hechos_entrada: Dict[str, Any]) -> ResultadoInferencia:
        hechos_originales = dict(hechos_entrada)
        hechos: Dict[str, Any] = dict(hechos_entrada)

        contradicciones = self.detectar_contradicciones(hechos)

        resultado = ResultadoInferencia(
            hechos_originales=hechos_originales,
            hechos_derivados={},
            contradicciones=contradicciones,
        )

        if contradicciones:
            resultado.estado = "contradiccion"
            return resultado

        reglas_disparadas: set[str] = set()
        reglas_indice = {regla["id"]: idx for idx, regla in enumerate(self.reglas)}

        while True:
            candidatas: List[Dict[str, Any]] = []
            hubo_faltante = False

            for regla in self.reglas:
                if regla["id"] in reglas_disparadas:
                    continue
                aplicable = self._regla_aplicable(regla, hechos)
                if aplicable is True:
                    candidatas.append(regla)
                elif aplicable is None:
                    hubo_faltante = True

            if not candidatas:
                break

            # Resolucion de conflictos: mayor prioridad primero;
            # empate resuelto por identificador de regla (orden en el archivo).
            candidatas.sort(
                key=lambda r: (-r["prioridad"], reglas_indice[r["id"]])
            )
            regla_elegida = candidatas[0]
            self._disparar_regla(regla_elegida, hechos, resultado)
            reglas_disparadas.add(regla_elegida["id"])

        # Si nunca se disparo ninguna regla y hubo condiciones con hechos
        # desconocidos, se informa evidencia insuficiente y que hechos
        # ayudarian a continuar.
        if not resultado.reglas_activadas:
            resultado.estado = "sin_evidencia"
            resultado.hechos_faltantes_relevantes = self._hechos_desconocidos_relevantes(hechos)
        else:
            resultado.estado = "resuelto"

        return resultado

    def _disparar_regla(
        self,
        regla: Dict[str, Any],
        hechos: Dict[str, Any],
        resultado: ResultadoInferencia,
    ) -> None:
        resultado_regla = regla["resultado"]
        paso = PasoTraza(
            regla_id=regla["id"],
            descripcion=regla["descripcion"],
            condiciones_evaluadas=regla["condiciones"],
            tipo_resultado=resultado_regla["tipo"],
            explicacion=regla["explicacion"],
            fuente=regla["fuente"],
        )

        if resultado_regla["tipo"] == "hecho":
            nombre = resultado_regla["hecho"]
            valor = resultado_regla["valor"]
            # No se sobrescriben hechos incompatibles ya presentes; los
            # hechos derivados por el motor si pueden anadirse si aun no existen.
            if nombre not in hechos:
                hechos[nombre] = valor
                resultado.hechos_derivados[nombre] = valor
            paso.hecho_derivado = nombre

        elif resultado_regla["tipo"] == "conclusion":
            resultado.conclusiones.append(
                {
                    "regla_id": regla["id"],
                    "conclusion": resultado_regla["conclusion"],
                    "recomendacion": resultado_regla["recomendacion"],
                }
            )

        resultado.reglas_activadas.append(paso)

    def _hechos_desconocidos_relevantes(self, hechos: Dict[str, Any]) -> List[str]:
        """Hechos mencionados en alguna condicion que aun no estan en la memoria de trabajo."""
        faltantes: set[str] = set()
        for regla in self.reglas:
            for condicion in regla["condiciones"]:
                nombre = condicion["hecho"]
                if nombre not in hechos:
                    faltantes.add(nombre)
        return sorted(faltantes)
