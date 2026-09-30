"""
Modelos Pydantic de entrada y salida para la API del sistema experto.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Valores posibles para hechos de tipo "si / no / desconocido".
ValorSiNoDesconocido = Literal["si", "no", "desconocido"]

# Nombres de hechos que el formulario puede enviar. Se validan de forma
# explicita para no aceptar claves arbitrarias en la API.
HECHOS_VALIDOS = {
    "router_encendido",
    "led_power_encendido",
    "led_internet_encendido",
    "cable_ethernet_conectado",
    "wifi_activado_en_dispositivo",
    "dispositivo_ve_red_wifi",
    "contrasena_wifi_correcta",
    "ip_asignada",
    "ping_gateway_exitoso",
    "ping_dns_exitoso",
    "resolucion_dns_exitosa",
    "otros_dispositivos_con_internet",
    "corte_programado_isp",
    "distancia_al_router",
    "interferencia_visible",
    "reinicio_router_reciente",
    "vpn_activa",
}

# Hechos cuyo valor no es si/no sino una categoria propia.
VALORES_CATEGORICOS = {
    "distancia_al_router": {"cerca", "lejos", "desconocido"},
}


class HechosEntrada(BaseModel):
    """
    Hechos capturados por el formulario de una nueva consulta.

    Cada campo puede ser "si", "no", "desconocido" (o, para distancia_al_router,
    "cerca"/"lejos"/"desconocido"). Un valor "desconocido" NO se envia al
    motor como hecho: simplemente se omite, de modo que el motor lo trate
    como informacion faltante y no como falso.
    """

    router_encendido: Optional[ValorSiNoDesconocido] = "desconocido"
    led_power_encendido: Optional[ValorSiNoDesconocido] = "desconocido"
    led_internet_encendido: Optional[ValorSiNoDesconocido] = "desconocido"
    cable_ethernet_conectado: Optional[ValorSiNoDesconocido] = "desconocido"
    wifi_activado_en_dispositivo: Optional[ValorSiNoDesconocido] = "desconocido"
    dispositivo_ve_red_wifi: Optional[ValorSiNoDesconocido] = "desconocido"
    contrasena_wifi_correcta: Optional[ValorSiNoDesconocido] = "desconocido"
    ip_asignada: Optional[ValorSiNoDesconocido] = "desconocido"
    ping_gateway_exitoso: Optional[ValorSiNoDesconocido] = "desconocido"
    ping_dns_exitoso: Optional[ValorSiNoDesconocido] = "desconocido"
    resolucion_dns_exitosa: Optional[ValorSiNoDesconocido] = "desconocido"
    otros_dispositivos_con_internet: Optional[ValorSiNoDesconocido] = "desconocido"
    corte_programado_isp: Optional[ValorSiNoDesconocido] = "desconocido"
    distancia_al_router: Optional[Literal["cerca", "lejos", "desconocido"]] = "desconocido"
    interferencia_visible: Optional[ValorSiNoDesconocido] = "desconocido"
    reinicio_router_reciente: Optional[ValorSiNoDesconocido] = "desconocido"
    vpn_activa: Optional[ValorSiNoDesconocido] = "desconocido"

    def a_memoria_de_trabajo(self) -> Dict[str, Any]:
        """Convierte el formulario en hechos para el motor, omitiendo 'desconocido'."""
        datos = self.model_dump()
        return {clave: valor for clave, valor in datos.items() if valor != "desconocido"}


class SolicitudConsulta(BaseModel):
    hechos: HechosEntrada


class PasoTrazaSalida(BaseModel):
    regla_id: str
    descripcion: str
    # Condiciones evaluadas de la regla (hecho, operador, valor esperado),
    # necesarias para que el modulo de explicacion muestre "que condiciones
    # la justificaron", tal como exige el enunciado.
    condiciones_evaluadas: List[Dict[str, Any]] = Field(default_factory=list)
    tipo_resultado: str
    hecho_derivado: Optional[str] = None
    explicacion: str
    fuente: str


class ConclusionSalida(BaseModel):
    regla_id: str
    conclusion: str
    recomendacion: str


class ConsultaRespuesta(BaseModel):
    id: int
    fecha: datetime
    hechos_originales: Dict[str, Any]
    hechos_derivados: Dict[str, Any]
    conclusiones: List[ConclusionSalida]
    reglas_activadas: List[PasoTrazaSalida]
    estado: str
    contradicciones: List[str] = Field(default_factory=list)
    hechos_faltantes_relevantes: List[str] = Field(default_factory=list)


class ConsultaResumen(BaseModel):
    """Fila resumida para el historial (GET /consultas)."""
    id: int
    fecha: datetime
    estado: str
    conclusion_principal: Optional[str] = None
    cantidad_reglas_activadas: int


class SaludRespuesta(BaseModel):
    estado: str
    tema: str
    cantidad_reglas: int
