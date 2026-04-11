# Vet-es (enae-vet-es)

**Punto único de entrada** al repositorio: contexto del producto, enlaces operativos (Jira, código), cómo levantar el entorno local y dónde profundizar. Lee primero las secciones **Proyecto → Jira → Setup local** (unos minutos); el resto sirve para reglas de negocio, API y flujos de trabajo en Cursor.

**Repositorio en GitHub:** [2310-dot/vet-es](https://github.com/2310-dot/vet-es)

---

## Proyecto

Chatbot y asistente de reservas para clínica veterinaria (caso ENAE). El backend previsto es **Python**, **LangChain** / LangGraph, **FastAPI**; el bot no diagnostica ni prescribe: orienta a citación, FAQs y procedimientos internos, citando herramientas o documentos recuperados.


| Tecnología           | Rol                                                                           |
| -------------------- | ----------------------------------------------------------------------------- |
| **Python**           | Servicios, APIs, cadenas/agentes LangChain.                                   |
| **LangChain**        | Prompts, herramientas (citas, paciente, etc.), RAG sobre protocolos, memoria. |
| **FastAPI**          | Capa HTTP/API del bot.                                                        |
| **Canal / frontend** | **TBD** — web, WhatsApp u otro; pendiente de decisión.                        |


Detalle de implementación: [.cursor/skills/langchain-vet-chatbots/SKILL.md](.cursor/skills/langchain-vet-chatbots/SKILL.md), [.cursor/agents/backend-langchain-vet.md](.cursor/agents/backend-langchain-vet.md).

---

## Equipo


| Rol / área                            | Contacto / notas              |
| ------------------------------------- | ----------------------------- |
| Autor / mantenedor                    | Eliu Salvador Pérez Tantaleán |
| Otros roles (PM, revisores, rotación) | **TBD**                       |


---

## Jira

Proyecto **Vet-es** en Atlassian (enlaces clicables):

- [Resumen del proyecto VE](https://eliuperez4.atlassian.net/jira/software/projects/VE/summary)
- [Lista de issues / backlog](https://eliuperez4.atlassian.net/jira/software/projects/VE/issues)

---

## Setup local

Requisitos: **Python 3** compatible con las dependencias de `requirements.txt`.

```bash
python -m venv .venv
```

Activa el entorno virtual:

- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
- **Linux / macOS:** `source .venv/bin/activate`

Instala dependencias y arranca la API placeholder (`main.py`):

```bash
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

- Documentación interactiva: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- OpenAPI: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)
- API rápida: `GET /health` (JSON), `POST /chat` (cuerpo JSON `msg` + `session_id`), legado `POST /ask_bot` (form urlencoded).

**Demo de chat en el navegador (VE-19):** con la API en marcha, abre [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Escribe un mensaje y pulsa Send; la UI llama a `POST /chat` en el mismo origen. Para apuntar a otro despliegue, edita **solo** `static/chat_config.js` (`window.CHATBOT_API_BASE`). Si el HTML se sirve desde otro origen que la API, define `CORS_ALLOW_ORIGINS` en el entorno (lista separada por comas; ver `.env.example`) y reinicia el servidor.

**Tests (opcional):** con el venv activo, `python -m pip install -r requirements-dev.txt` si aplica, luego `pytest`.

### Pre-op RAG (VE-22)

- **Config** (chunk size, overlap, embedding model, source URL, `PREOP_RAG_CONFIG_VERSION`): `preop_rag/config.py`.
- **Demo local:** `python -m preop_rag.demo` (requiere `OPENAI_API_KEY`; usa `python -m preop_rag.demo --fake-embeddings` solo para comprobar el cableado sin API).
- **Tests:** `pytest` (e2e con HTML de fixture y vector store en memoria). Prueba opcional con red y OpenAI: `RUN_PREOP_RAG_LIVE=1 pytest -m preop_live`.

---

## Variables de entorno

Opcionales: el API arranca sin `.env`. Ver `.env.example` (OpenAI, CORS, RAG, memoria de chat).

### Session memory (VE-21) — English

In-process conversation store keyed by **trimmed** `session_id` (**case-sensitive**; `"A"` and `"a"` are different). `POST /chat` and `POST /ask_bot` share this store. Data is **not** persisted: a process restart clears everything.

| Variable | Default | Meaning |
| -------- | ------- | ------- |
| `CHAT_MEMORY_MAX_TURNS` | `50` | Max stored **user→assistant pairs** per session; oldest pairs dropped. |
| `CHAT_MEMORY_TTL_SECONDS` | `0` | If `0`, TTL is off (entries last until restart). If positive, a session with no activity for that many seconds (monotonic clock) is treated as empty on the next access. |

Concurrency: a single **`threading.Lock`** protects the store. Concurrent requests for the same session are serialized; under the lock, updates apply in order (**last write wins** for the stored transcript state after each completed handler).

Validation failures (`422` / `415` on `/chat` or `/ask_bot`) do **not** append to memory.
- **`OPENAI_API_KEY`**: obligatoria para que `POST /chat` y `POST /ask_bot` llamen al modelo. Sin ella, esas rutas responden **503** con un mensaje claro (no se usa clave en el repo; ver `.env.example`).
- **`OPENAI_CHAT_MODEL`** (opcional): modelo de chat OpenAI; por defecto `gpt-4o-mini` en `llm_service.py`.
- El **system prompt** base del asistente está en **`prompt.md`** en la raíz del repo (misma carpeta que `main.py`); el backend lo carga desde disco.

Otras variables (CORS, puerto, RAG, etc.) siguen en `.env.example`.

---

## Despliegue

**TBD** — entorno de producción, CI/CD, hosting y secretos: por definir cuando exista pipeline.

---

## Backlog / roadmap

Seguimiento del trabajo en Jira:

- [Issues del proyecto VE](https://eliuperez4.atlassian.net/jira/software/projects/VE/issues)

Roadmap de producto a alto nivel: **TBD** (p.ej. enlace a Confluence o épica cuando exista).

---

## Enlaces relevantes.


| Recurso                                                                      | Descripción                                |
| ---------------------------------------------------------------------------- | ------------------------------------------ |
| [Repositorio GitHub](https://github.com/2310-dot/vet-es)                     | Código fuente                              |
| [CLAUDE.md](CLAUDE.md)                                                       | Guía para asistentes de código en el repo  |
| [docs/event-storming-workflow.md](docs/event-storming-workflow.md)           | Flujo de reserva y reglas de capacidad     |
| [docs/pre-operative-considerations.md](docs/pre-operative-considerations.md) | Consideraciones preoperatorias (ES)        |
| [docs/jira/](docs/jira/)                                                     | Exports de tickets enriquecidos (ejemplos) |
| [.cursor/commands/implement.md](.cursor/commands/implement.md)               | Flujo ticket Jira → PR                     |
| [.cursor/commands/enrich.md](.cursor/commands/enrich.md)                     | Flujo de enriquecimiento de tickets        |


---

## Workflow (negocio)

Flujo principal de conversación a cita confirmada:

1. **Conversación → intención y slots** — El usuario habla con el bot; el bot identifica intención y datos necesarios.
2. **Solo día** — El usuario elige un **día**; no se pide hora quirúrgica al cliente (las gestiona el sistema por dentro).
3. **Reglas de capacidad** — Cuota **240 minutos** diarios, **límite de perros** por día, tiempos de servicio desde configuración o tabla maestra.
4. **Ventanas de ingreso** — Gatos 08:00–09:00; perros 09:00–10:30. Los horarios quirúrgicos no se muestran al cliente.
5. **Confirmación** — Instrucciones de ingreso + ayuno (última comida 8–12 h antes; agua hasta 1–2 h antes, según política de la clínica).

---

## Docs overview

La carpeta `docs/` es la fuente de verdad para reglas de negocio y mensajería.


| Documento                              | Uso                                                 |
| -------------------------------------- | --------------------------------------------------- |
| `docs/pre-operative-considerations.md` | Alcance de clínica, ayuno, transporte, alta (ES).   |
| Reglas de negocio / agenda             | En `docs/` cuando existan (p. ej. cuotas, límites). |
| `docs/jira/`                           | Tickets enriquecidos y ejemplos before/after.       |


Si añades documentos nuevos, enlázalos en **Enlaces relevantes** o en esta tabla.

---

## Consistencia

- **Capacidad y cuota:** lo descrito en **Workflow** debe alinearse con `docs/` y reglas en `.cursor/rules` si las hay.
- **Ventanas de ingreso y comunicación:** coherentes con `docs/pre-operative-considerations.md`.
- Al cambiar reglas en `docs/`, actualiza este README para evitar contradicciones.

---

## API (Chatbot v4 placeholder)

Definida en `main.py`:

- **GET /** — HTML placeholder para futura UI.
- **POST /ask_bot** — Cuerpo `application/x-www-form-urlencoded` (`msg`, `session_id`); respuesta JSON de prueba hasta integrar LangChain.

### Ejemplos

```bash
curl http://127.0.0.1:8000/

curl -X POST http://127.0.0.1:8000/ask_bot \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "msg=hello&session_id=s1"
```

Respuesta esperada (stub):

```json
{"msg": "hello", "session_id": "s1", "placeholder": true, "turn_count": 1}
```

`turn_count` is the number of completed user→assistant pairs stored for that `session_id` after the request (placeholder bot echoes the user message as the assistant line).

---

## Cursor workflows

- **Implementar ticket Jira:** p. ej. *"Implement VE-12"* — lee el ticket, planifica según AC, desarrolla, mueve estados y abre PR. Detalle: [.cursor/commands/implement.md](.cursor/commands/implement.md).
- **Enriquecer ticket:** *"Enrich VE-1"* o `/enrich` — refina criterios y alcance con el agente PM; publicar en Jira requiere tu aprobación. Detalle: [.cursor/commands/enrich.md](.cursor/commands/enrich.md).

## Despliegue

**URL de producción:** `https://vercel.com/2310-dots-projects/vet-es`

### Procedimiento

El proyecto se despliega automáticamente en Vercel al hacer push o merge
sobre la rama `main`.

- **Plataforma:** Vercel
- **Rama de producción:** `main`
- **Builds de preview:** generados automáticamente para cada Pull Request

### Variables de entorno

Las variables de entorno se gestionan **únicamente en el panel de Vercel**
(`Settings → Environment Variables`). No existe ningún `.env` commiteado.

Para desarrollo local, copiar `.env.example` y rellenar los valores:

```bash
cp .env.example .env.local
```