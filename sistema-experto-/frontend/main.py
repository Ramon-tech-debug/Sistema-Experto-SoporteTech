"""
Interfaz web del sistema experto, construida con NiceGUI.

Este proceso NO contiene reglas del dominio ni accede directamente a la
base de datos: toda la logica se consulta a la API de FastAPI mediante
HTTPX (cliente asincrono), para practicar la comunicacion entre dos
procesos independientes.

Ejecucion:
    python frontend/main.py

Variables de entorno:
    API_URL  -> direccion base del backend (por defecto http://127.0.0.1:8000)
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx
from nicegui import ui

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")

# Etiquetas legibles para cada hecho del formulario. El orden aqui define
# el orden en el que aparecen los campos en la pantalla "Nueva consulta".
CAMPOS_SI_NO = [
    ("router_encendido", "Â¿El router esta encendido?"),
    ("led_power_encendido", "Â¿El LED de encendido (power) del router esta iluminado?"),
    ("led_internet_encendido", "Â¿El LED de internet/linea del router esta iluminado?"),
    ("cable_ethernet_conectado", "Â¿Hay un cable Ethernet conectado al dispositivo?"),
    ("wifi_activado_en_dispositivo", "Â¿El Wi-Fi del dispositivo esta activado?"),
    ("dispositivo_ve_red_wifi", "Â¿El dispositivo detecta/ve la red Wi-Fi del hogar?"),
    ("contrasena_wifi_correcta", "Â¿La contrasena Wi-Fi ingresada es correcta?"),
    ("ip_asignada", "Â¿El dispositivo tiene una direccion IP asignada?"),
    ("ping_gateway_exitoso", "Â¿El ping a la puerta de enlace (router) fue exitoso?"),
    ("ping_dns_exitoso", "Â¿El ping a un servidor DNS externo (por ejemplo 8.8.8.8) fue exitoso?"),
    ("resolucion_dns_exitosa", "Â¿Se pudo resolver un nombre de dominio (por ejemplo google.com)?"),
    ("otros_dispositivos_con_internet", "Â¿Otros dispositivos del hogar si tienen internet?"),
    ("corte_programado_isp", "Â¿El proveedor aviso un corte de mantenimiento programado?"),
    ("interferencia_visible", "Â¿Hay interferencia visible (paredes, electrodomesticos, otros routers)?"),
    ("reinicio_router_reciente", "Â¿El router se reinicio hace pocos minutos (aun en arranque)?"),
    ("vpn_activa", "Â¿Hay una VPN activa en el dispositivo?"),
]

CAMPO_DISTANCIA = ("distancia_al_router", "Distancia del dispositivo al router")

OPCIONES_SI_NO = {"Si": "si", "No": "no", "No lo se": "desconocido"}
OPCIONES_DISTANCIA = {"Cerca": "cerca", "Lejos": "lejos", "No lo se": "desconocido"}



# ---------------------------------------------------------------------
# Tema oscuro (fondo negro) para toda la aplicacion
# ---------------------------------------------------------------------
ui.add_head_html("""
<style>
    :root { color-scheme: dark; }
    body, body.body--dark, .q-page, .q-layout {
        background-color: #000000 !important;
    }
    .q-header {
        background-color: #000000 !important;
        border-bottom: 1px solid #222222;
    }
    .q-card, .q-expansion-item, .q-table, .q-table__container, .q-markup-table {
        background-color: #111114 !important;
        color: #f2f2f2 !important;
        border: 1px solid #262626;
    }
    .q-table thead th { color: #cfcfcf !important; }
    .q-table tbody td { color: #eaeaea !important; }
    a { color: #4da3ff; }
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: #000000; }
    ::-webkit-scrollbar-thumb { background: #333333; border-radius: 6px; }
</style>
""", shared=True)


def _tema_oscuro() -> None:
    """Activa el modo oscuro de Quasar/NiceGUI para el cliente actual."""
    ui.dark_mode().enable()


async def obtener_json(cliente: httpx.AsyncClient, ruta: str) -> Optional[Any]:
    try:
        respuesta = await cliente.get(f"{API_URL}{ruta}", timeout=5.0)
        respuesta.raise_for_status()
        return respuesta.json()
    except httpx.RequestError:
        ui.notify(
            "No se pudo contactar la API. Verifique que el backend este en ejecucion.",
            type="negative",
        )
        return None
    except httpx.HTTPStatusError as error:
        ui.notify(f"La API respondio con un error: {error.response.status_code}", type="negative")
        return None


CATEGORIAS_DIAGNOSTICO = [
    ("router", "Alimentacion y hardware del router", "Â¿El router tiene energia y esta encendido?"),
    ("wifi", "Red Wi-Fi", "Credenciales correctas, senal e interferencia."),
    ("dns", "Direcciones IP (DHCP)", "Si el dispositivo recibe una IP valida."),
    ("cloud_off", "Proveedor de internet (ISP)", "Cortes programados o fallas fuera del hogar."),
    ("travel_explore", "Resolucion de nombres (DNS)", "Si los dominios se resuelven correctamente."),
]


@ui.page("/")
def pagina_inicio() -> None:
    _barra_navegacion()
    with ui.column().classes("max-w-3xl mx-auto p-6 gap-4"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("wifi_off", size="2.2rem").classes("text-primary")
            ui.label("Sistema Experto de Diagnostico de Conectividad").classes("text-2xl font-bold")

        ui.label("Â¿De que trata este proyecto?").classes("text-lg font-bold text-primary mt-2")
        ui.label(
            "Cuando un dispositivo del hogar pierde internet, la causa puede estar en el "
            "router, en la red Wi-Fi, en la asignacion de direcciones IP, en la red local "
            "o fuera del hogar, en el proveedor de servicios de internet (ISP). Una persona "
            "sin conocimientos tecnicos no suele distinguir entre estas causas."
        ).classes("text-gray-300")
        ui.label(
            "Este sistema experto aplica una base de conocimiento de mas de 20 reglas "
            "de diagnostico de redes sobre las respuestas de un formulario sencillo, y "
            "entrega una conclusion justificada, una recomendacion concreta y la traza "
            "completa de que reglas se activaron y por que."
        ).classes("text-gray-300")

        ui.label("Â¿Que tipos de falla puede identificar?").classes("text-lg font-bold text-primary mt-2")
        with ui.column().classes("gap-2 w-full"):
            for icono, titulo, detalle in CATEGORIAS_DIAGNOSTICO:
                with ui.row().classes("items-center gap-3 w-full"):
                    ui.icon(icono).classes("text-primary")
                    with ui.column().classes("gap-0"):
                        ui.label(titulo).classes("font-bold")
                        ui.label(detalle).classes("text-sm text-gray-400")

        ui.label(
            "Responda el formulario de 'Nueva consulta' indicando lo que observa en su "
            "router y dispositivo. Si no sabe un dato, seleccione 'No lo se': el sistema "
            "nunca lo tratara como una respuesta negativa."
        ).classes("text-gray-300 mt-2")

        with ui.row().classes("gap-4 mt-4"):
            ui.button("Iniciar nueva consulta", on_click=lambda: ui.navigate.to("/consulta")).props("color=primary")
            ui.button("Ver historial", on_click=lambda: ui.navigate.to("/historial")).props("outline color=white")
            ui.button("Ver base de conocimiento", on_click=lambda: ui.navigate.to("/reglas")).props("outline color=white")


@ui.page("/consulta")
def pagina_nueva_consulta() -> None:
    _barra_navegacion()
    valores: Dict[str, Any] = {}

    with ui.column().classes("max-w-3xl mx-auto p-6 gap-3"):
        ui.label("Nueva consulta").classes("text-xl font-bold")
        ui.label(
            "Complete lo que pueda observar. Deje 'No lo se' si desconoce un dato: "
            "el sistema no lo tratara como una respuesta negativa."
        )

        for nombre_hecho, etiqueta in CAMPOS_SI_NO:
            valores[nombre_hecho] = "desconocido"
            seleccion = ui.toggle(
                list(OPCIONES_SI_NO.keys()), value="No lo se"
            ).props("dense")
            ui.label(etiqueta).classes("text-sm text-gray-300 -mt-2")

            def _al_cambiar(evento, hecho=nombre_hecho):
                valores[hecho] = OPCIONES_SI_NO[evento.value]

            seleccion.on_value_change(_al_cambiar)

        nombre_distancia, etiqueta_distancia = CAMPO_DISTANCIA
        valores[nombre_distancia] = "desconocido"
        seleccion_distancia = ui.toggle(
            list(OPCIONES_DISTANCIA.keys()), value="No lo se"
        ).props("dense")
        ui.label(etiqueta_distancia).classes("text-sm text-gray-300 -mt-2")

        def _al_cambiar_distancia(evento):
            valores[nombre_distancia] = OPCIONES_DISTANCIA[evento.value]

        seleccion_distancia.on_value_change(_al_cambiar_distancia)

        boton_evaluar = ui.button("Evaluar").props("color=primary")
        indicador_carga = ui.spinner(size="md").props("color=primary")
        indicador_carga.set_visibility(False)

        async def _evaluar() -> None:
            boton_evaluar.disable()
            indicador_carga.set_visibility(True)
            try:
                async with httpx.AsyncClient() as cliente:
                    try:
                        respuesta = await cliente.post(
                            f"{API_URL}/consultas",
                            json={"hechos": valores},
                            timeout=10.0,
                        )
                        respuesta.raise_for_status()
                    except httpx.RequestError:
                        ui.notify(
                            "No se pudo contactar la API. Verifique que el backend "
                            "este en ejecucion en " + API_URL,
                            type="negative",
                        )
                        return
                    except httpx.HTTPStatusError as error:
                        ui.notify(
                            f"La API rechazo la solicitud ({error.response.status_code}): "
                            f"{error.response.text}",
                            type="negative",
                        )
                        return

                    datos = respuesta.json()
                    ui.navigate.to(f"/resultado/{datos['id']}")
            finally:
                boton_evaluar.enable()
                indicador_carga.set_visibility(False)

        boton_evaluar.on_click(_evaluar)


@ui.page("/resultado/{id_consulta}")
def pagina_resultado(id_consulta: int) -> None:
    _barra_navegacion()

    with ui.column().classes("max-w-3xl mx-auto p-6 gap-3"):
        ui.label(f"Resultado de la consulta #{id_consulta}").classes("text-xl font-bold")
        contenedor = ui.column().classes("gap-3 w-full")

        async def _cargar() -> None:
            async with httpx.AsyncClient() as cliente:
                datos = await obtener_json(cliente, f"/consultas/{id_consulta}")
            contenedor.clear()
            if datos is None:
                return
            with contenedor:
                _renderizar_resultado(datos)

        ui.timer(0.1, _cargar, once=True)


# Frases en lenguaje natural para mostrar los hechos al usuario.
# (valor "si", valor "no"). Es solo presentacion; las reglas viven en el backend.
FRASES_HECHOS = {
    "router_encendido": ("El router esta encendido", "El router esta apagado"),
    "led_power_encendido": ("El LED de encendido del router esta prendido", "El LED de encendido del router esta apagado"),
    "led_internet_encendido": ("El LED de internet del router esta prendido", "El LED de internet del router esta apagado"),
    "cable_ethernet_conectado": ("Hay un cable Ethernet conectado", "No hay cable Ethernet conectado"),
    "wifi_activado_en_dispositivo": ("El Wi-Fi del dispositivo esta activado", "El Wi-Fi del dispositivo esta desactivado"),
    "dispositivo_ve_red_wifi": ("El dispositivo ve la red Wi-Fi", "El dispositivo no ve la red Wi-Fi"),
    "contrasena_wifi_correcta": ("La contrasena Wi-Fi es correcta", "La contrasena Wi-Fi es incorrecta"),
    "ip_asignada": ("El dispositivo tiene direccion IP", "El dispositivo no tiene direccion IP"),
    "ping_gateway_exitoso": ("El router responde al ping", "El router no responde al ping"),
    "ping_dns_exitoso": ("El servidor DNS externo responde al ping", "El servidor DNS externo no responde al ping"),
    "resolucion_dns_exitosa": ("Se pudo resolver un nombre de dominio", "No se pudo resolver un nombre de dominio"),
    "otros_dispositivos_con_internet": ("Otros dispositivos si tienen internet", "Ningun otro dispositivo tiene internet"),
    "corte_programado_isp": ("El proveedor aviso de un corte programado", "El proveedor no aviso de ningun corte programado"),
    "interferencia_visible": ("Hay interferencia visible", "No hay interferencia visible"),
    "reinicio_router_reciente": ("El router se reinicio hace poco", "El router no se ha reiniciado recientemente"),
    "vpn_activa": ("Hay una VPN activa", "No hay ninguna VPN activa"),
}

# Hechos intermedios que deduce el motor (cuando valen "verdadero").
FRASES_DERIVADOS = {
    "sin_medio_conexion": "El dispositivo no tiene ningun medio de conexion (ni cable ni Wi-Fi)",
    "fallo_interfaz_red": "Falla la interfaz de red del dispositivo",
    "router_sin_energia": "El router no tiene energia electrica",
    "fallo_autenticacion_wifi": "Fallo la autenticacion en la red Wi-Fi",
    "fallo_dhcp": "Falla la asignacion automatica de direccion IP (DHCP)",
    "fallo_red_local": "Falla la comunicacion dentro de la red local",
    "fallo_especifico_dispositivo": "La falla afecta solo a este dispositivo",
    "fallo_conexion_internet": "Se perdio la salida a internet",
    "posible_corte_isp": "Posible corte del proveedor de internet",
    "fallo_dns": "Falla el servicio de nombres (DNS)",
}


def _frase_hecho(nombre: str, valor: Any) -> str:
    """Convierte un hecho y su valor en una frase natural."""
    if nombre == "distancia_al_router":
        return "El dispositivo esta lejos del router" if valor == "lejos" else "El dispositivo esta cerca del router"
    if nombre in FRASES_DERIVADOS and valor is True:
        return FRASES_DERIVADOS[nombre]
    if nombre in FRASES_HECHOS and valor in ("si", "no"):
        return FRASES_HECHOS[nombre][0 if valor == "si" else 1]
    return f"{nombre.replace('_', ' ')}: {valor}"


def _frases_condiciones(condiciones: list) -> list:
    """Lista de frases naturales, una por condicion de la regla."""
    frases = []
    for c in condiciones:
        if c["operador"] == "eq":
            frases.append(_frase_hecho(c["hecho"], c["valor"]))
        else:
            frases.append(f"{c['hecho'].replace('_', ' ')} distinto de {c['valor']}")
    return frases


def _renderizar_resultado(datos: Dict[str, Any]) -> None:
    estado = datos["estado"]

    if estado == "contradiccion":
        ui.label("âš ï¸ Se detectaron hechos contradictorios").classes("text-lg font-bold text-red-400")
        for mensaje in datos["contradicciones"]:
            ui.label(f"â€¢ {mensaje}")
        ui.label(
            "Revise las respuestas del formulario: alguno de los datos indicados "
            "no es consistente con otro."
        )
        return

    if estado == "sin_evidencia":
        ui.label("iï¸ Evidencia insuficiente para llegar a una conclusion").classes(
            "text-lg font-bold text-orange-400"
        )
        ui.label("Los siguientes datos ayudarian a continuar el diagnostico:")
        preguntas = dict(CAMPOS_SI_NO)
        preguntas[CAMPO_DISTANCIA[0]] = CAMPO_DISTANCIA[1]
        for hecho in datos["hechos_faltantes_relevantes"]:
            if hecho in preguntas:  # solo datos que el usuario puede responder
                ui.label(f"â€¢ {preguntas[hecho]}")
        return

    ui.label("âœ… Diagnostico completado").classes("text-lg font-bold text-green-400")

    for conclusion in datos["conclusiones"]:
        with ui.card().classes("w-full"):
            ui.label(conclusion["conclusion"]).classes("font-bold")
            ui.label(f"Recomendacion: {conclusion['recomendacion']}")
            ui.label(f"Regla: {conclusion['regla_id']}").classes("text-xs text-gray-400")

    with ui.expansion("Ver traza de reglas activadas y explicacion", icon="rule").classes("w-full"):
        for numero, paso in enumerate(datos["reglas_activadas"], start=1):
            with ui.column().classes("w-full gap-1 border-b py-3"):
                ui.label(f"Paso {numero} Â· Regla {paso['regla_id']}").classes("font-bold text-primary")
                ui.label(paso["descripcion"])
                ui.label("Se aplico porque:").classes("text-sm font-bold mt-1")
                for frase in _frases_condiciones(paso["condiciones_evaluadas"]):
                    ui.label(f"â€¢ {frase}").classes("text-sm text-gray-300")
                if paso.get("hecho_derivado"):
                    ui.label(
                        "Se dedujo que: " + _frase_hecho(paso["hecho_derivado"], True)
                    ).classes("text-sm font-bold mt-1")
                ui.label(f"Por que: {paso['explicacion']}").classes("text-sm text-gray-300 mt-1")
                ui.label(f"Fuente: {paso['fuente']}").classes("text-xs text-gray-400 italic")

    with ui.expansion("Ver hechos originales y derivados").classes("w-full"):
        ui.label("Datos que usted indico:").classes("font-bold")
        for nombre, valor in datos["hechos_originales"].items():
            ui.label(f"â€¢ {_frase_hecho(nombre, valor)}").classes("text-sm")
        ui.label("Hechos que el sistema dedujo:").classes("font-bold mt-2")
        if not datos["hechos_derivados"]:
            ui.label("(ninguno)").classes("text-sm")
        for nombre, valor in datos["hechos_derivados"].items():
            ui.label(f"â€¢ {_frase_hecho(nombre, valor)}").classes("text-sm")


@ui.page("/historial")
def pagina_historial() -> None:
    _barra_navegacion()

    with ui.column().classes("max-w-4xl mx-auto p-6 gap-3 w-full"):
        ui.label("Historial de consultas").classes("text-xl font-bold")
        contenedor = ui.column().classes("w-full")

        async def _cargar() -> None:
            async with httpx.AsyncClient() as cliente:
                datos = await obtener_json(cliente, "/consultas")
            contenedor.clear()
            if not datos:
                with contenedor:
                    ui.label("Aun no hay consultas registradas.")
                return
            with contenedor:
                columnas = [
                    {"name": "id", "label": "ID", "field": "id"},
                    {"name": "fecha", "label": "Fecha", "field": "fecha"},
                    {"name": "estado", "label": "Estado", "field": "estado"},
                    {
                        "name": "conclusion_principal",
                        "label": "Conclusion principal",
                        "field": "conclusion_principal",
                    },
                    {
                        "name": "cantidad_reglas_activadas",
                        "label": "Reglas activadas",
                        "field": "cantidad_reglas_activadas",
                    },
                ]
                tabla = ui.table(columns=columnas, rows=datos, row_key="id").classes("w-full")
                tabla.on(
                    "rowClick",
                    lambda evento: ui.navigate.to(f"/resultado/{evento.args[1]['id']}"),
                )

        ui.timer(0.1, _cargar, once=True)


@ui.page("/reglas")
def pagina_reglas() -> None:
    _barra_navegacion()

    with ui.column().classes("max-w-5xl mx-auto p-6 gap-3 w-full"):
        ui.label("Base de conocimiento").classes("text-xl font-bold")
        contenedor = ui.column().classes("w-full")

        async def _cargar() -> None:
            async with httpx.AsyncClient() as cliente:
                datos = await obtener_json(cliente, "/reglas")
            contenedor.clear()
            if not datos:
                return
            with contenedor:
                for regla in datos:
                    with ui.expansion(f"{regla['id']} â€” {regla['descripcion']}").classes("w-full"):
                        ui.label("Se aplica cuando:").classes("text-sm font-bold")
                        for frase in _frases_condiciones(regla["condiciones"]):
                            ui.label(f"â€¢ {frase}").classes("text-sm text-gray-300")
                        ui.label(regla["explicacion"]).classes("text-sm text-gray-300 mt-2")
                        ui.label(f"Prioridad: {regla['prioridad']}").classes("text-xs text-gray-400")
                        ui.label(f"Fuente: {regla['fuente']}").classes("text-xs text-gray-400 italic")

        ui.timer(0.1, _cargar, once=True)


def _barra_navegacion() -> None:
    _tema_oscuro()
    with ui.header().classes("items-center justify-between px-4 bg-black"):
        ui.label("Diagnostico de Conectividad").classes("text-lg font-bold text-white")
        with ui.row().classes("gap-2"):
            ui.button("Inicio", on_click=lambda: ui.navigate.to("/")).props("flat color=white")
            ui.button("Nueva consulta", on_click=lambda: ui.navigate.to("/consulta")).props("flat color=white")
            ui.button("Historial", on_click=lambda: ui.navigate.to("/historial")).props("flat color=white")
            ui.button("Reglas", on_click=lambda: ui.navigate.to("/reglas")).props("flat color=white")


ui.run(host="127.0.0.1", port=8080, title="Sistema Experto - Conectividad", reload=False)


