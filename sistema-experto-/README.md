# Sistema Experto — Diagnostico de Conectividad en Redes Domesticas e Internet

Sistema experto basado en reglas que ayuda a diagnosticar por que un
dispositivo del hogar no tiene internet: problemas del router, de la red
Wi-Fi, de la asignacion de IP, del proveedor (ISP) o de resolucion DNS.

Construido con **FastAPI** (backend), **NiceGUI** (frontend web) y
**SQLite** (persistencia), como dos procesos independientes que se
comunican por HTTP/HTTPX.

## 1. Arquitectura

```
Navegador
   │
   ▼
NiceGUI (puerto 8080)  ──HTTPX (async)──▶  FastAPI (puerto 8000)
                                               │
                                               ▼
                                       Motor de inferencia
                                       (backend/motor.py)
                                               │
                                               ▼
                                            SQLite
                                     (datos/sistema_experto.db)
```

El frontend **no** contiene reglas del dominio ni accede directamente a
la base de datos: todo pasa por la API.

## 2. Estructura de archivos

```
backend/
  __init__.py
  main.py          # aplicacion FastAPI y rutas
  modelos.py       # validacion de datos (Pydantic)
  motor.py         # motor de inferencia (encadenamiento hacia adelante)
  repositorio.py   # almacenamiento SQLite
  reglas.json      # base de conocimiento (22 reglas)
frontend/
  main.py          # interfaz NiceGUI
tests/
  test_motor.py    # pruebas del motor de inferencia
datos/             # base SQLite local (se crea automaticamente)
requirements.txt
README.md
```

## 3. Preparacion del entorno (Ubuntu o WSL2)

Si usa Windows, abra PowerShell como administrador:

```powershell
wsl --install -d Ubuntu
```

Reinicie si Windows lo solicita y complete la creacion del usuario Linux.
Los siguientes comandos se ejecutan **dentro de Ubuntu**:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

mkdir -p ~/sistema-experto
cd ~/sistema-experto
# copie aqui el contenido del proyecto (backend/, frontend/, tests/, etc.)

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Al finalizar la implementacion y las pruebas, actualice el archivo de
dependencias con las versiones realmente instaladas:

```bash
python -m pip freeze > requirements.txt
```

## 4. Ejecucion

Se necesitan **dos terminales**, ambas con el entorno virtual activado
desde la raiz del proyecto.

**Terminal 1 — backend (FastAPI):**

```bash
source .venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — frontend (NiceGUI):**

```bash
source .venv/bin/activate
python frontend/main.py
```

- Interfaz web: <http://localhost:8080>
- Documentacion interactiva de la API (Swagger): <http://localhost:8000/docs>

El frontend lee la direccion del backend desde la variable de entorno
`API_URL` (por defecto `http://127.0.0.1:8000`). Para apuntar a otra
direccion:

```bash
export API_URL=http://127.0.0.1:8000
python frontend/main.py
```

Si trabaja en WSL2, verifique que pueda abrir `http://localhost:8080` y
`http://localhost:8000/docs` desde el navegador de Windows; WSL2 expone
automaticamente los puertos de `localhost` al host en la mayoria de los
casos. Si no fuese asi, use `ip addr show eth0` dentro de WSL2 para
obtener la IP de la distribucion y navegue a esa IP en su lugar.

## 5. Ejecutar las pruebas

Con `pytest` instalado:

```bash
source .venv/bin/activate
pytest tests/ -v
```

Sin `pytest`, el archivo de pruebas tambien puede ejecutarse directamente:

```bash
python tests/test_motor.py
```

## 6. Uso de la aplicacion

1. Abra <http://localhost:8080>.
2. Vaya a **Nueva consulta** y responda lo que pueda observar del router
   y del dispositivo (LEDs, Wi-Fi, resultados de ping, etc.). Deje
   **"No lo se"** en lo que desconozca: el sistema no lo interpretara
   como una respuesta negativa.
3. Presione **Evaluar**. El sistema mostrara:
   - una o varias **conclusiones** con su **recomendacion**,
   - la **traza** de reglas activadas con su explicacion y fuente,
   - o un aviso de **evidencia insuficiente** / **contradiccion**, segun
     el caso.
4. En **Historial** puede ver todas las consultas anteriores y abrir su
   detalle.
5. En **Base de conocimiento** puede revisar las 22 reglas del sistema,
   su prioridad, explicacion y fuente.

## 7. API minima

| Metodo | Ruta               | Funcion                                   |
|--------|--------------------|--------------------------------------------|
| GET    | `/salud`           | Verificar disponibilidad                   |
| GET    | `/reglas`          | Consultar la base de conocimiento          |
| POST   | `/consultas`       | Validar hechos, inferir y guardar          |
| GET    | `/consultas`       | Listar historial                           |
| GET    | `/consultas/{id}`  | Consultar hechos, resultados y traza       |

Un identificador de consulta inexistente en `GET /consultas/{id}`
devuelve `404`. Las entradas invalidas en `POST /consultas` son
rechazadas por la validacion de Pydantic (`422`).

## 8. Notas de diseno

- El motor de inferencia (`backend/motor.py`) es un motor propio en
  Python puro: interpreta reglas estructuradas desde JSON y compara
  condiciones mediante funciones explicitas por operador (`eq`, `neq`).
  **No usa `eval()`** sobre las condiciones.
- Un hecho ausente de la memoria de trabajo se trata como
  **desconocido**, nunca como falso.
- Cada regla se dispara **como maximo una vez** por consulta.
- Cuando varias reglas son candidatas a la vez, se resuelve el conflicto
  por **mayor prioridad**; en caso de empate, por **orden de
  identificador** (R01 antes que R02, etc.).
- Las contradicciones logicas explicitas (por ejemplo, "router apagado"
  junto con "IP asignada") se detectan **antes** de iniciar la
  inferencia y detienen el proceso con un mensaje explicativo.
- La traza devuelta por `POST /consultas` y `GET /consultas/{id}` incluye,
  por cada regla activada, sus **condiciones evaluadas**, el **hecho
  producido** (si aplica), la **explicacion** y la **fuente**, tal como
  exige el modulo de explicacion del enunciado.
- Documentacion completa del proyecto (ficha del tema, tabla de las 22
  reglas, matriz de casos de prueba y mapeo a la rubrica): ver
  `Documentacion_Sistema_Experto.docx`.
