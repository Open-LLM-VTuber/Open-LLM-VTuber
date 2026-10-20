# HANDOFF — Open-LLM-VTuber v1.2.1 en Docker + WSL2 (Windows)

> Archivo de traspaso generado al final de una sesión de depuración.
> **Cómo usarlo:** abre una tarea nueva en Cline y escribe:
> `@HANDOFF.md Léelo entero y continúa donde lo dejamos.`
> (o pega: `Lee d:\Open-LLM-VTuber\HANDOFF.md y continúa.`)
> Cuando ya no lo necesites, puedes borrarlo.

---

## 1. Objetivo del usuario

Ejecutar el proyecto local **Open-LLM-VTuber v1.2.1** en **Docker sobre WSL2 (Windows)** y usarlo desde el
navegador de Windows, con:
- LLM: `openai_llm` → **OpenRouter**, modelo `deepseek/deepseek-v4.1-flash`
- TTS: `edge_tts` (voz `es-CO-GonzaloNeural`)
- Personaje: "Mao" con persona de **tarotista** (en `conf/conf.yaml`)

## 2. Entorno

| Elemento | Valor |
|---|---|
| Carpeta del proyecto | `d:\Open-LLM-VTuber` (montada en WSL como `/mnt/d/Open-LLM-VTuber`) |
| Docker | Docker Desktop 27.4.0 / Compose v2.31 (integración WSL2) |
| Contenedor | `open-llm-vtuber` (imagen `open-llm-vtuber-open-llm-vtuber`) |
| Puertos | `12393:12393` (host:contenedor) |
| Config | `./conf/conf.yaml` (dentro del contenedor: `/app/conf/conf.yaml`) |
| Navegador | **Chrome** (el proyecto lo recomienda; Edge/Safari dan problemas) |
| URL | `http://localhost:12393` (nunca `0.0.0.0` en el navegador) |

## 3. Problemas encontrados y causas raíz (ambas RESUELTAS)

### Problema A — `ERR_EMPTY_RESPONSE` / la web no abría
- `run_server.py:139` lee **`conf.yaml` relativo al CWD** → `/app/conf.yaml` (no `/app/conf/conf.yaml`).
- `.dockerignore` excluye `/conf.yaml`, así que la imagen **no trae** ese archivo.
- El único que lo crea es el entrypoint `/usr/local/bin/start-app` del `dockerfile` (hace
  `ln -sf /app/conf/conf.yaml /app/conf.yaml`). Ese entrypoint es el `CMD` de la imagen.
- Al sobrescribir `command:` en `docker-compose.yml` (para forzar `uv add edge-tts`), **se perdía el symlink**.
- Entonces `upgrade_manager.sync_user_config()` copiaba `config_templates/conf.default.yaml`
  (que tiene **`host: 'localhost'`**) a `/app/conf.yaml` → Uvicorn bindeaba **127.0.0.1** dentro del
  contenedor → el puerto publicado no llegaba a Windows → `ERR_EMPTY_RESPONSE`.
- Prueba: log decía `Starting server on localhost:12393`; `/app/conf.yaml` era un **archivo regular**
  byte-idéntico a la plantilla; `connect_ex` a la IP del contenedor daba `111` (refused) y a
  127.0.0.1 `0` (open). Un contenedor de control `-p 18080:8000 --bind 0.0.0.0` respondía `HTTP 200` desde
  Windows → la red Docker/WSL2 estaba bien.

### Problema B — El agente respondía por texto pero **no había audio**
- Logs: `CRITICAL | tts.edge_tts:generate_audio:46 | Error: edge-tts unable to generate audio: 403,
  message='Invalid response status', url='wss://speech.platform.bing.com/...&Sec-MS-GEC-Version=1-143.0.3650.75'`
- En `/app/cache` quedaban `.mp3` de **0 bytes** → `edge_tts.py:48` devuelve `None` →
  `tts_manager.py:143` envía un **payload silencioso** (`"audio": None`) → texto sin voz.
- **Causa raíz real:** Microsoft hizo **obligatorio en octubre de 2026** el token de DRM
  **`Sec-MS-GEC` v2** (`Sec-MS-GEC-Version: 2-...`), y edge-tts solo lo soporta desde **7.3.0**
  (PR #492 del repo rany2/edge-tts: *"Adds support for the Sec-MS-GEC v2 token format, which Microsoft
  made mandatory in October 2026. This fixes the WSServerHandshakeError: 403"*; 7.3.1 añade
  *"Fix locale-dependent server date parsing"*).
- El contenedor tenía **edge-tts 7.2.7** (token v1 → 403) porque **`uv.lock:594` fija `edge-tts = "7.2.7"`**
  y **`uv add edge-tts` no actualiza** una versión ya bloqueada. El "forzar edge-tts al arrancar" nunca actualizó nada.
- Descartado con pruebas: la IP/región (Edge propio funciona), el reloj (contenedor == host == fecha real de
  Internet `Date: Sun, 18 Oct 2026 02:14:07 GMT`) y la red (el endpoint responde; `bing.com` 200).

## 4. Cambios aplicados (estado actual del repo)

**Archivo modificado: `docker-compose.yml`** (está **untracked** en git: `git status` lo muestra como nuevo):

```yaml
services:
  open-llm-vtuber:
    build:
      context: .
      dockerfile: dockerfile
    container_name: open-llm-vtuber
    ports:
      - "12393:12393"
    volumes:
      - ./conf:/app/conf
      - ./models:/app/models
    # (comentarios explicativos largos dentro del archivo)
    command: >-
      bash -c "uv add 'edge-tts>=7.3.0' && exec /usr/local/bin/start-app"
    restart: unless-stopped
```

Los **dos cambios clave** son:
1. `exec /usr/local/bin/start-app` → recrea el symlink `/app/conf.yaml` + enlaza
   `characters/avatars/backgrounds/live2d-models/model_dict.json` desde `/app/conf`.
2. `uv add 'edge-tts>=7.3.0'` → el `>=` **obliga** a uv a salir del 7.2.7 fijado en `uv.lock`
   (antes `uv add edge-tts` mantenía la versión bloqueada).

> ⚠️ **Nunca** cambies el `command` quitando `start-app` (ni quites el symlink), o vuelve `ERR_EMPTY_RESPONSE`.
> ⚠️ Si cambias el `command`, recuerda que `uv add` necesita **red** al arrancar; si falla, la app no arranca.

**Otros archivos:** `conf/conf.yaml` (config del usuario, `host: '0.0.0.0'`, edge_tts) — sin cambios.
`conf.yaml` (raíz, gitignored) es la config antigua nativa, **no se usa** en Docker.
**No se tocó** `pyproject.toml` ni `uv.lock` (ver pendiente 3).

### 4.1 Emisión programada (auditoría §4.3) — implementada

- `src/open_llm_vtuber/scheduler/service.py`: planificador **sin dependencias nuevas**
  (cron de 5 campos + `interval_minutes` en stdlib). Se descartó APScheduler para no
  regenerar `uv.lock`, que rompería el `uv sync --frozen` del build.
- `src/open_llm_vtuber/config_manager/scheduler.py` + sección `scheduler_config` en
  `conf/conf.yaml`, `conf.yaml` y las dos plantillas. **`enabled: false` por defecto**.
- `WebSocketHandler.trigger_proactive_speak()`: dispara `ai-speak-signal` solo si el
  cliente no tiene un turno en curso (guarda de A14); el scheduler reintenta 3 veces/10 s.
- `conversation_handler.py`: `ai-speak-signal` usa `data["text"]` si viene; si no, carga
  `proactive_speak_prompt` como antes.
- `server.py` crea el handler una vez y lo comparte con las rutas y el scheduler
  (`startup`/`shutdown`).

Para probarlo: poner `scheduler_config.enabled: true` en `conf/conf.yaml`, añadir un job
`interval_minutes: 1` (más simple que un cron a 2 minutos vista) y reiniciar
(`docker compose restart`, la config se lee al arrancar). **Hace falta un cliente conectado**
a `/proxy-ws` en el momento del disparo: el scheduler escribe sobre el overlay, así que sin
cliente el log dice `job '...' skipped, no overlay connected`; con el overlay abierto (o con
un script que se conecte a `/proxy-ws` y responda `frontend-playback-complete`) sale
`Scheduler: job '...' armed for ...` → `fired on <uid>` y el turno se oye.

Verificado el 19/10/2026 con `interval_minutes: 1`:

```text
Scheduler: job 'preflight_test' armed for 2026-10-19 22:46
Scheduler started with 5 job(s) (timezone: Europe/Madrid)
Scheduler: job 'preflight_test' fired on d15fc559-... (attempt 1/3)
User input: Saluda brevemente: esta es la prueba de preflight del scheduler.
```

El cliente recibió `conversation-chain-start`, 5 chunks de `audio`, envió sus acks y recibió
`conversation-chain-end`. Ojo: la hora del `armed for` está en la zona configurada
(`Europe/Madrid`), mientras que las marcas de tiempo de loguru van en UTC; con el contenedor
en UTC se ven con 2 h de diferencia y es correcto. `scene` ya se aplica de verdad desde la
fase 3 (OBS WebSocket, ver §4.4).

### 4.2. Smoke test del pipeline (`scripts/smoke_test.py`)

Prueba el circuito completo **sin navegador**: `text-input` → LLM → TTS → `audio` →
`frontend-playback-complete` → `conversation-chain-end`. Abre dos conexiones a `/proxy-ws`:
una hace de overlay (cuenta el audio base64 y responde el ack que el backend espera) y otra
inyecta el texto como el conector de TikTok.

```powershell
cd d:\Open-LLM-VTuber
docker compose build                                        # el script es nuevo: la imagen hace COPY . /app
docker compose up -d
docker compose exec -T open-llm-vtuber uv run python scripts/smoke_test.py
# alternativa desde Windows (venv con httpx + websockets):
python scripts/smoke_test.py --url http://127.0.0.1:12393
```

Salida esperada: `ok web ... -> 200`, `ok overlay connected to /proxy-ws`, recuento de
`audio chunks/bytes` y `SMOKE TEST PASSED` (exit 0). Si falla, el mensaje distingue
servidor caído (`server unreachable`), turno sin cerrar (`no turn end within Ns`, sospechar
LLM/TTS o un turno ya en curso) y `error` del propio backend.

**Ejecutado contra el contenedor real el 19/10/2026** (pipeline completo: OpenRouter +
edge-tts + proxy):

```text
ok  web http://127.0.0.1:12393/ -> 200
ok  overlay connected to /proxy-ws

audio chunks : 2
audio bytes  : 290392
playback ack : 2
chain start  : True
chain end    : True
said         : [smirk] Hola, alma inquieta... los astros te trajeron hasta aquí por una razón.

SMOKE TEST PASSED
```

Dos avisos sacados de esa ejecución:

- **No lances el test mientras corre un `docker compose build`**: el build satura CPU/disco
  y el WebSocket cae con `ConnectionClosedError: sent 1011 (internal error) keepalive ping
  timeout`, que parece un fallo del backend y no lo es. Espera a que el build acabe.
- Si los acentos salen como `aqu├¡` es la consola de PowerShell, no el servidor: ejecuta
  antes `[Console]::OutputEncoding = [Text.Encoding]::UTF8` (o `chcp 65001`).

### 4.3 Fase 2 — A23 (formato de audio configurable) y A24 (resiliencia GPT-SoVITS)

Ficheros tocados:

| Fichero | Cambio |
|---|---|
| `config_manager/system.py` | nuevo `AudioExportConfig` (`system_config.audio_export`, default `wav`/`64k`) |
| `config_manager/tts.py` | `GPTSoVITSConfig`: `request_timeout`, `max_retries`, `retry_backoff`, `max_concurrency` (todos con default) |
| `utils/stream_audio.py` | `configure_audio_export()`, `get_audio_export_format()`, `audio_format` en el payload |
| `tts/gpt_sovits_tts.py` | timeout acotado, reintentos con backoff, `BoundedSemaphore`, validación de que el cuerpo es audio, `streaming_mode` default `false` |
| `tts/tts_factory.py` | pasa las 4 claves nuevas al engine |
| `server.py` | aplica `system_config.audio_export` al arrancar (fallback a `wav` si es inválido) |
| `conf/conf.yaml`, `conf.yaml`, `config_templates/*.yaml` | documentan las claves nuevas |
| `scripts/test_audio_hardening.py` | 12 tests nuevos (stdlib puro) |

Para llevarlo al contenedor ya construido (el build sigue sin ser reproducible, ver §6.8):

```powershell
docker cp src\open_llm_vtuber\config_manager\system.py        open-llm-vtuber:/app/src/open_llm_vtuber/config_manager/system.py
docker cp src\open_llm_vtuber\config_manager\tts.py           open-llm-vtuber:/app/src/open_llm_vtuber/config_manager/tts.py
docker cp src\open_llm_vtuber\utils\stream_audio.py           open-llm-vtuber:/app/src/open_llm_vtuber/utils/stream_audio.py
docker cp src\open_llm_vtuber\tts\gpt_sovits_tts.py           open-llm-vtuber:/app/src/open_llm_vtuber/tts/gpt_sovits_tts.py
docker cp src\open_llm_vtuber\tts\tts_factory.py              open-llm-vtuber:/app/src/open_llm_vtuber/tts/tts_factory.py
docker cp src\open_llm_vtuber\server.py                       open-llm-vtuber:/app/src/open_llm_vtuber/server.py
docker cp scripts\test_audio_hardening.py                     open-llm-vtuber:/app/scripts/test_audio_hardening.py
docker compose restart
```

> `conf/conf.yaml` se lee al arrancar: tras cambiar `audio_export.format` hay que reiniciar
> (no basta con recargar la página). El formato activo se registra en el log sólo si **no** es `wav`.

### 4.4 Fase 3 — OBS WebSocket v5 y contrato `stage-update` (auditoría §2.4)

Ficheros nuevos:

| Fichero | Qué hace |
|---|---|
| `src/open_llm_vtuber/scheduler/obs.py` | cliente **OBS WebSocket v5** sobre `websockets` (ya era dependencia): handshake + auth SHA256/base64, `connect`, `set_scene`, `start_stream`, `stop_stream`, `list_scenes`, `close`; reintenta la conexión una vez por llamada y **nunca lanza** (devuelve `bool`) |
| `src/open_llm_vtuber/utils/stage.py` | contrato del overlay: `build_stage_payload()` (sanea `props`, acota `duration_ms`, exige algo que cambiar) y `select_stage_targets()` (`first`/`all`/`client_uid`) |
| `web_tool/stage-test.html` | overlay de prueba: dos capas con crossfade, `props` posicionados en % y HUD con `h`. Acepta `?token=` y `?ws=` |
| `scripts/test_stage_obs.py` | **27 tests** sin red ni OBS real (`FakeOBSSocket`): payload, targeting, cliente v5 y scheduler |

Modificados: `config_manager/scheduler.py` (`OBSConfig` + `background`/`transition`/`duration_ms` en cada job), `websocket_handler.py` (`current_stage`, `broadcast_stage_update`, `fetch-stage`), `routes.py` (`GET`/`POST /api/stage`), `scheduler/service.py` (`_prepare_stage`, StartStream/StopStream, cierre limpio), `server.py`, las dos plantillas YAML y `conf/conf.yaml` (*este último está gitignored*: el cambio es solo para la copia local).

```yaml
scheduler_config:
  obs:                       # todo desactivado por defecto
    enabled: false           # true = conectar al arrancar y cambiar escenas
    host: '127.0.0.1'        # con la app en Docker: 'host.docker.internal'
    port: 4455
    password: ''
    timeout: 3.0
    start_stream: false            # StartStream cuando arranca el scheduler
    stop_stream_on_shutdown: false # StopStream al apagar el servidor
    switch_scenes: true            # los jobs pueden cambiar la escena
  jobs:
    - name: 'card_of_the_day'
      cron: '0 20 * * *'
      scene: 'tarot_main'                # SetCurrentProgramScene
      background: '/bg/tarot_table.png'  # stage-update al overlay
      transition: 'fade'                 # 'fade' | 'none'
      duration_ms: 800
```

Comportamiento (todo **best-effort**):

- **OBS apagado o mal configurado** ⇒ un `warning` y el segmento se emite igual: solo se pierde el cambio de escena.
- **`stage-update` se cachea** en el handler: el overlay que conecta tarde (o recarga el Browser Source) lo recibe al conectar o al mandar `fetch-stage`.
- **`props` ausente conserva** los props anteriores (un job solo-fondo no borra las cartas); `props: []` sí los limpia.
- **`POST /api/stage`** permite al operador cambiar el overlay sin esperar a un job; el token es el mismo de A22 (`VTUBER_WS_TOKEN`, cabecera `Authorization: Bearer …` o `?token=`).

```powershell
# ver el último stage (401 si hay token y no se envía)
curl.exe http://127.0.0.1:12393/api/stage
# cambiarlo a mano; delivered = nº de overlays que lo recibieron
curl.exe -X POST http://127.0.0.1:12393/api/stage -H 'Content-Type: application/json' `
  -d '{"stage":"tarot_main","background":"/bg/tarot_table.png","props":[{"id":"card_1","src":"/bg/cards/death.png","x":0.7,"y":0.5}],"duration_ms":600}'
```

Prueba manual (**obligatoria**, aquí no se puede ejecutar OBS junto con Docker):

1. Sin OBS: `python scripts/test_stage_obs.py`, `node scripts/test_overlay_wire.js` y abrir
   `http://localhost:12393/web-tool/stage-test.html` (con `?token=…` si A22 está activo). El `POST`
   de arriba debe devolver `delivered: 1` y verse el crossfade.
2. Con OBS 28+: *Herramientas → Configuración del servidor WebSocket*, activarlo, poner
   `scheduler_config.obs.enabled: true` y la contraseña, crear las escenas (`starting_soon`,
   `tarot_main`, `ending`) y añadir el overlay como **Browser Source**
   (`http://127.0.0.1:12393/web-tool/overlay.html`, 1920×1080; `stage-test.html` solo si se quiere
   probar el contrato sin audio). Tras reiniciar, el log debe mostrar
   `Scheduler: OBS scenes available: …`; al disparar un job, `SetCurrentProgramScene` (y `StartStream`
   si `start_stream: true`). `overlay.html` **sí** manda `frontend-playback-complete`, así que el turno
   cierra cuando termina el audio y no por timeout (A18); `stage-test.html` no lo manda y por eso el
   turno acaba en `No playback completion ...; closing the turn anyway`.

Para llevarlo al contenedor ya construido (el build sigue sin ser reproducible, §6.8):

```powershell
docker cp src\open_llm_vtuber\utils\stage.py open-llm-vtuber:/app/src/open_llm_vtuber/utils/stage.py
docker cp src\open_llm_vtuber\scheduler open-llm-vtuber:/app/src/open_llm_vtuber/scheduler
docker cp src\open_llm_vtuber\config_manager\scheduler.py open-llm-vtuber:/app/src/open_llm_vtuber/config_manager/scheduler.py
docker cp src\open_llm_vtuber\routes.py open-llm-vtuber:/app/src/open_llm_vtuber/routes.py
docker cp src\open_llm_vtuber\server.py open-llm-vtuber:/app/src/open_llm_vtuber/server.py
docker cp src\open_llm_vtuber\websocket_handler.py open-llm-vtuber:/app/src/open_llm_vtuber/websocket_handler.py
docker cp web_tool\stage-test.html open-llm-vtuber:/app/web_tool/stage-test.html
docker cp web_tool\overlay.html open-llm-vtuber:/app/web_tool/overlay.html
docker cp web_tool\overlay-protocol.js open-llm-vtuber:/app/web_tool/overlay-protocol.js
docker compose restart
```

### 4.5 Fase 3 — overlay de producción (audio + `frontend-playback-complete`)

Cierra el pendiente §6.11: el overlay reproduce el audio de cada turno y responde el ack, así que el
backend ya no espera `PLAYBACK_ACK_TIMEOUT` (180 s) en cada frase (A18).

| Fichero | Contenido |
|---|---|
| `web_tool/overlay-protocol.js` | **Lógica pura** del protocolo, sin DOM ni Web Audio: cola de chunks, `audio-play-start`, un `frontend-playback-complete` por flanco de `backend-synth-complete` cuando la cola se vacía, `interrupt-signal`, `fetch-stage` al reconectar y enrutado de `stage-update` / `full-text` / `expression` |
| `web_tool/overlay.html` | **Browser Source** de OBS: capas con crossfade, `props`, subtítulo, un `<audio>` con los chunks en orden y HUD oculto (`h` o `?debug=1`). Socket por defecto **`/proxy-ws`** (A1), con `?token=` (A22) y `?ws=` para apuntar a `/client-ws` |
| `scripts/test_overlay_protocol.js` | **13 tests** de Node (`node:test`) con socket y reproductor falsos: sin OBS, sin navegador y sin backend |
| `tests/fixtures/overlay-wire.json` | **Los bytes reales**: por cada escenario, las cadenas exactas de `json.dumps()` que el backend pasa a `websocket_send`, separadas en «antes del ack» y «después del ack» |
| `scripts/export_overlay_fixtures.py` | Genera ese fixture ejecutando los builders **reales** (`build_stage_payload`, `prepare_audio_payload`, `finalize_conversation_turn`, `build_interrupt_signal`). Solo los bytes de audio son sintéticos |
| `scripts/test_overlay_wire.js` | **10 tests** que reproducen el fixture por `overlay-protocol.js`: productor y consumidor contra los mismos bytes |
| `scripts/test_overlay_fixtures.py` | **9 tests**: el fixture commiteado no está obsoleto y cubre el contrato |

**Por qué hace falta el fixture (§6.11):** los dos suites anteriores se equivocaban por separado. Python se
probaba contra sus propias suposiciones y el JS contra mensajes escritos a mano; si ambos no coincidían
(por ejemplo `audio: null` vs `audio: ""`), los dos pasaban y **el directo quedaba mudo**. El fixture
elimina el supuesto intermedio.

> La captura ya destapó una cosa: el servidor manda `force-new-message` y `conversation-chain-end`
> **después** de recibir el ack, no antes. Por eso cada turno se guarda partido en `frames` (antes del
> ack) y `after_ack` (después), y el test comprueba que el `chain-end` **no** repite el ack.

Decisiones del contrato:

- **`audio: null`** y **`forwarded: true`** se muestran como subtítulo y **no** bloquean el ack: son los
  avisos de los demás clientes del grupo (A21).
- **`interrupt-signal`** para el audio y vacía la cola **sin** ack: ese turno lo cierra el servidor por la
  vía de la interrupción.
- Un chunk que **no se puede reproducir** (autoplay bloqueado, `error` del `<audio>`) se da por terminado
  para que el turno no se quede colgado.
- Al **reconectar** se manda `fetch-stage` (el servidor cachea el último `stage-update`) y se descarta la
  cola; los callbacks viejos del reproductor **no** pueden ackar el turno nuevo.

```powershell
# lógica del overlay (no necesita Python, ni Docker, ni OBS)
node scripts/test_overlay_protocol.js
# productor y consumidor contra los mismos bytes (fixture real del backend)
node scripts/test_overlay_wire.js
# el fixture sigue correspondiendo al código de hoy
python scripts/test_overlay_fixtures.py
# tras tocar stage.py / stream_audio.py / conversation_utils.py: regenerar y commitear
python scripts/export_overlay_fixtures.py
python scripts/export_overlay_fixtures.py --check   # exit 1 si está obsoleto
# comprobar que el JS sigue siendo válido
node --check web_tool/overlay-protocol.js
```

Ojo: el overlay **no** pinta Live2D ni hace lip-sync; dibuja escenario, props y subtítulo y reproduce la
voz. Para el avatar hay que añadir el Live2D Web SDK (o seguir usando la UI oficial como Browser Source).

### 4.6 Mecánica de tarot — tirada real + props de texto

Hasta aquí el "tarotista" era un prompt y cuatro frases programadas: no había baraja. Ahora un job puede
**barajar, sacar cartas, ponerlas en el escenario y decírselas al LLM**, sin arte y sin platós nuevos.

| Fichero | Contenido |
|---|---|
| `utils/tarot.py` | **nuevo**, stdlib pura: 22 arcanos mayores en español (nombre, palabras clave, lectura al derecho y invertida), `draw_cards(count, seed=…)` sin repetir cartas, `build_draw_props()` y `build_tarot_brief()` |
| `utils/stage.py` | un prop puede ser imagen (`src`) **o tarjeta de texto** (`label`/`sublabel`, recortados a 64/96 caracteres); si vienen los dos gana `src` |
| `scheduler/service.py` | `_draw()` dibuja **una sola vez por disparo**, `_prepare_stage(job, drawn)` manda las cartas como props y `_compose_text()` pone el brief delante de `job.text` |
| `config_manager/scheduler.py` | campos nuevos de job: `draw` (0–3), `draw_seed` (0 = aleatoria) y `question` |
| `web_tool/overlay.html` | pinta los props de texto como tarjeta (`.card`), compartiendo posición/rotación con las imágenes |

Configuración (ya viene en `conf.yaml`, `conf/conf.yaml` y las dos plantillas):

```yaml
    - name: 'card_of_the_day'
      cron: '0 20 * * *'
      scene: 'tarot_main'
      draw: 1                                    # 1-3 cartas
      # draw_seed: 2024                          # fijo = misma tirada siempre
      question: '¿Qué energía trae el día?'      # opcional, va al brief del LLM
```

Decisiones:

- La tirada se dibuja **antes** del `stage-update` y antes del turno: el overlay y el LLM ven **las mismas
  cartas** (dibujar dos veces sería un bug garantizado).
- `draw_seed` fijo ⇒ misma tirada en cada disparo (ensayos y demos); `0` ⇒ distinta cada vez.
- Un `draw` inválido **no** rompe el segmento: se registra y el job se habla sin cartas.
- Posiciones según el tamaño: 1 carta al centro, 2 a `0.36/0.64`, 3 a `0.28/0.50/0.72`; `y = 0.68` deja la
  mitad superior libre para el avatar.
- **Sin arte**: `label` = "La Torre", `sublabel` = "ruptura · verdad · derrumbe · invertida". Cuando haya
  cartas dibujadas se cambia el prop a `src` y el scheduler no se toca.

#### Donaciones: regalo → gracias → pregunta → tirada

Un regalo **no** se lee en el mismo turno: sería adivinar qué quiere saber el donante. El flujo es de dos
pasos y el segundo solo ocurre si el donante escribe.

| Paso | Quién | Qué pasa |
|---|---|---|
| 1 | conector (`GiftEvent`) | `PendingDonors.remember(donante, regalo, monedas)` y encola un `text-input`: *"dale las gracias… pregúntale qué quiere saber… **no leas cartas todavía**"* |
| 2 | el donante comenta | `PendingDonors.consume(donante)` → encola `{"type":"tarot-draw","asker":"pepe","question":"…","count":1}` con prioridad de regalo |
| 3 | servidor (`_handle_tarot_draw`) | `draw_tarot(..., asker="pepe")` → cartas en el overlay y brief `Pregunta de pepe: …` + `Responde directamente a pepe` |

| Fichero | Contenido |
|---|---|
| `utils/donations.py` | **nuevo**, stdlib pura: `PendingDonors` (un uso, TTL 10 min), `build_gift_thanks()`, `build_donor_draw_payload()` |
| `live/tiktok_live.py` | la cola pasa a llevar **frames** (`text-input` o `tarot-draw`) en vez de solo texto; `on_gift` arma la pregunta y `on_comment` la convierte en tirada si viene del donante |
| `websocket_handler.py` | `_handle_tarot_draw()` (frame `tarot-draw`) y `_run_brief_turn()` como red de seguridad para no dejar al conector esperando |
| `utils/tarot.py`, `utils/tarot_commands.py` | `asker` en el brief y en el `summary()` de la tirada |

Decisiones:

- **Un solo uso**: responder consume la entrada, así un regalo no compra lecturas infinitas.
- **Caduca a los 10 minutos** (`DEFAULT_TTL_SECONDS`): un regalo de las 19:00 no convierte un comentario de
  las 23:30 en una lectura pagada.
- Si el donante comenta **sin** haber regalado, es un comentario normal; si regala y no vuelve a escribir,
  se queda en el agradecimiento.
- El `asker` viaja también en `POST /api/tarot/draw` (`"asker": "pepe"`), por si quieres tirar desde un
  panel para una persona concreta.

#### Bajo demanda (operador y chat)

La tirada por horario es la base; además se puede disparar a mano o desde el chat:

| Vía | Cómo | Qué hace |
|---|---|---|
| HTTP | `POST /api/tarot/draw` | Baraja, manda el `stage-update` al overlay y (si `speak: true`) arranca el turno que lee las cartas |
| HTTP | `GET /api/tarot` | Devuelve la última tirada (`cards`, `question`, `stage`) para un HUD de operador |
| Chat | `!carta`, `!tirada 3`, `!carta ¿me cambiaré de trabajo?` | Se intercepta **antes** del LLM: dibuja, pone las cartas y el turno pasa a ser proactivo con el brief. El comando no entra en el historial |

| Fichero | Contenido |
|---|---|
| `utils/tarot_commands.py` | **nuevo**, stdlib pura: `parse_draw_command()` (`!carta`/`!tirada N`/`/carta`) y `build_draw_result()` → cartas + payload + brief + `summary()` |
| `websocket_handler.py` | `draw_tarot(count, question, seed, target_client, speak)` compartido por la ruta y el chat; `current_draw` para `GET /api/tarot`; `_handle_conversation_trigger` intercepta el comando |
| `routes.py` | `init_tarot_route()`: `GET /api/tarot`, `POST /api/tarot/draw` (token A22, `count` 1–3, `seed` opcional) |

Decisiones:

- El comando tiene que **abrir el mensaje**: al principio (`!carta`) o justo detrás de dos puntos/comilla, porque el conector de TikTok envía `pepe dice: "!carta …"`. Así "me encanta tu !carta" sigue siendo un comentario normal.
- Si el turno proactivo se rechaza (ya hay uno en marcha), el comando cae a un **turno de texto normal** con el brief: las cartas se leen igual y el conector recibe su `conversation-chain-end` (si no, esperaría a su watchdog de 90 s).
- Un comando **mal formado** (`!tirada 9`) se registra y sigue como mensaje normal: se pierde una tirada, no la frase del espectador.
- `speak` viene **apagado** por defecto en HTTP: quién habla depende del despliegue (proxy/conector). Si se activa, usa `target` (por defecto el primer socket, que es el overlay en el montaje recomendado).
- El chat habla **en el cliente que escribió el comando**, igual que un `text-input` normal; así el audio viaja por el proxy a todos los clientes.
- `GET /api/tarot` no dispara nada: solo lee la última tirada.

#### Arte de las cartas (mazo real, dominio público)

- **Mazo real**: `backgrounds/cards/major_00.jpg … major_21.jpg`, el **Rider–Waite–Smith** (1909) de
  Pamela Colman Smith. Licencia **dominio público** (Commons: `PD-old-80-expired`), sin atribución
  obligatoria; fuente, orden y condiciones en `backgrounds/cards/README.md`.
- **Cómo llegó**: `scripts/fetch_tarot_art.ps1` descarga miniaturas **960 px** de Wikimedia
  (`thumb.wikimedia.org`; el servicio ya solo expone ese bucket). 22 ficheros, **≈11,5 MB**.
  `-Force` vuelve a bajarlos.
- `build_draw_props()` devuelve **props de imagen**: `src: /bg/cards/major_16.jpg`, `rot: 180` para las
  invertidas (carta del revés, como en una mesa real) y escala **0.85 / 0.7 / 0.55** para 1, 2 o 3 cartas,
  de modo que nunca se solapen.
- **Mazo de reserva sin licencia**: los `.svg` que genera `scripts/make_tarot_cards.py` siguen ahí
  (`--check` detecta desfase). Para usarlos: `build_draw_props(drawn, art_ext="svg")`.
- **Sin arte**: `build_draw_props(drawn, art_prefix=None)` → tarjetas de texto (`label`/`sublabel`).
  Los tests del fixture cubren las dos rutas (`tarot_draw_three_cards` y `tarot_draw_text_fallback`).
- **Tu propio mazo**: deja `<id>.jpg` con los mismos nombres y ya está; si usas otro formato, cambia
  `CARD_ART_EXT` en `utils/tarot.py`. El scheduler y el HUD no se tocan.
- `.gitignore` abre `!/backgrounds/cards/**` para que el mazo viaje en el repo; el resto de `backgrounds/`
  sigue siendo local.

#### HUD de operador (`web_tool/operator.html`)

Página estática servida por el propio backend: `http://localhost:12393/web-tool/operator.html`
(con `?token=…` si A22 está activo; la añade a todas las peticiones).

| Panel | De dónde lee |
|---|---|
| Escenario | `GET /api/stage` → stage, fondo, nº de props, hora del último cambio |
| Última tirada | `GET /api/tarot` → donante, pregunta y cartas (posición, invertida, palabras clave) |
| Botones | `POST /api/tarot/draw` con `count` 1 o 3; casilla **«leer en voz alta»** (manda `speak`) y campo de pregunta |

Refresca cada **2 s** y muestra el error tal cual si el servidor responde 401/500. No usa librerías ni
build: un solo HTML con CSS/JS.

```powershell
# arte de las cartas (determinista; --check detecta desfase)
python scripts/make_tarot_cards.py
python scripts/make_tarot_cards.py --check

# tirada de 3 cartas y que la lea en voz alta
curl.exe -X POST http://127.0.0.1:12393/api/tarot/draw -H "Content-Type: application/json" `
  -d '{"count":3,"question":"¿Cambio de trabajo?","speak":true}'
# solo pintar las cartas (sin hablar)
curl.exe -X POST http://127.0.0.1:12393/api/tarot/draw -H "Content-Type: application/json" -d '{"count":1}'
# qué hay ahora mismo en pantalla
curl.exe http://127.0.0.1:12393/api/tarot

# pintar cartas a mano en el overlay (sin baraja)
curl.exe -X POST http://127.0.0.1:12393/api/stage -H "Content-Type: application/json" `
  -d '{"stage":"card_of_the_day","props":[{"id":"card_1","label":"La Torre","sublabel":"ruptura, verdad","x":0.5,"y":0.68}]}'

# tests
python scripts/test_tarot.py            # 32 tests: baraja, tirada, props, arte, brief
python scripts/test_tarot_commands.py   # 19 tests: comandos y resultado compartido
python scripts/test_donations.py        # 16 tests: donantes, TTL y frames
python scripts/test_stage_obs.py        # 38 tests: contrato + draw del scheduler
```

## 5. Estado verificado (¡importante!)


| Comprobación | Resultado |
|---|---|
| Contenedor | `Up ... 0.0.0.0:12393->12393/tcp` ✅ |
| `conf.yaml` leído | `Using user-provided conf.yaml` ✅ |
| Bind de Uvicorn | `Starting server on 0.0.0.0:12393` / `Uvicorn running on http://0.0.0.0:12393` ✅ |
| Web desde Windows | `HTTP 200`, `<title>Open-LLM-Vtuber</title>`, `/web-tool/` → 200 ✅ |
| LLM | `Initializing LLM: openai_llm` → `https://openrouter.ai/api/v1, deepseek/deepseek-v4.1-flash` ✅ |
| edge-tts | actualizado en runtime **7.2.7 → 7.3.1** ✅ |
| DRM | `SEC_MS_GEC_VERSION: 2-143.0.3650.75` (v2) ✅ |
| **TTS real** | `TTS OK size = 11232 bytes` (antes 0 bytes + 403) ✅ |
| **Smoke test** | `audio chunks 2 / 290392 bytes / playback ack 2 / chain end True` → `SMOKE TEST PASSED`, exit 0 ✅ |
| **Scheduler** | `Scheduler started with 5 job(s)` → `job 'preflight_test' fired on <uid>`; el cliente recibe audio, ack y `conversation-chain-end` ✅ |
| **Stage/OBS** | ⏳ contrato, cliente v5 y wiring cubiertos por `python scripts/test_stage_obs.py` (38 tests tras añadir la tirada), overlay de producción por `node scripts/test_overlay_protocol.js` (13) y **contrato cruzado** con los bytes reales (`node scripts/test_overlay_wire.js` = 11, `python scripts/test_overlay_fixtures.py` = 10). La baraja por `python scripts/test_tarot.py` (25). La prueba con OBS real es manual (§6.10) |
| **Mecánica de tarot** | ✅ **Hecha** (§4.6): 22 arcanos, tirada 1–3 sin repetir, **mazo real Rider–Waite–Smith** (dominio público, `/bg/cards`, invertidas rotadas 180°), mazo SVG de reserva, props de texto como último recurso, brief para el LLM, `POST /api/tarot/draw`, `GET /api/tarot`, **HUD de operador** (`web_tool/operator.html`), comandos `!carta`/`!tirada N` y **regalos en dos pasos** con `gift_reading`. ⏳ falta solo la prueba en vivo (§6.12) |

## 6. Pendientes / siguientes pasos

1. **[Comprobar arranque]** El contenedor arranca en frío en **~7-9 min**. Hay que esperar a ver en el log
   `INFO:     Uvicorn running on http://0.0.0.0:12393 (Press CTRL+C to quit)` y entonces abrir
   **`http://localhost:12393` en Chrome** y probar voz + chat.
   ```powershell
   cd d:\Open-LLM-VTuber
   docker compose logs -f        # espera la línea "Uvicorn running"
   ```
2. **[Acelerar el arranque — recomendado]** El 80% de la espera es cargar el modelo ASR (239 MB) desde `D:\`
   (drvfs es lentísimo). Mover `models/` a un **volumen Docker** (ext4 nativo) baja el arranque a ~30 s:
   ```yaml
   volumes:
     - ./conf:/app/conf
     - ollv_models:/app/models      # en vez de ./models:/app/models
   volumes:
     ollv_models:
   ```
   (hay que volver a colocar el modelo `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17` en el volumen, p.ej. con `docker cp`).
3. **[Fix duradero opcional]** Que la imagen ya nazca con edge-tts ≥ 7.3.0 (sin depender de red en cada arranque):
   editar `pyproject.toml`: `"edge-tts>=7.0.0"` → `"edge-tts>=7.3.0"` **y regenerar `uv.lock`**
   (`uv lock --upgrade-package edge-tts`), porque el `dockerfile` usa `uv sync --frozen` y **si el lock no
   coincide el build falla**. Luego `docker compose build`.
4. **[Plan B si edge-tts vuelve a romperse]** TTS **100% local** (sin red): `sherpa_onnx_tts`
   (ya instalado `sherpa-onnx 1.10.46`; solo falta un modelo VITS de
   https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models y 3 líneas en `conf/conf.yaml`) o
   `piper_tts` (requiere `uv add piper-tts` + `models/piper/<voz>.onnx`).
5. **[Ruido no fatal]** MCP: `Failed to connect to server 'time': Timed out ... 30.0 seconds` al arrancar
   (se instala/descarga la 1ª vez). `ddg-search` sí conecta. Si molesta, quitar `"time"` de
   `mcp_enabled_servers` en `conf/conf.yaml`.
6. **[Reinicio automático]** `restart: unless-stopped` reinicia el contenedor **si ya existe**.
   Tras un `docker compose down` hay que hacer `docker compose up -d` una vez.
   Para que arranque solo al encender el PC: Docker Desktop → Settings → General →
   "Start Docker Desktop when you sign in".
7. **[Limpieza]** Dentro del contenedor quedan restos de pruebas **efímeros**: `/tmp/test_tts.py`, `/tmp/t.mp3`.
   El script de prueba en Windows está en `%TEMP%\test_tts.py`.
8. **[Contenedor vs. imagen]** El scheduler y `scripts/smoke_test.py` ya están **commiteados**
   (`2da6d3d`, `ea648d5`, `881a899` en la rama `feat/mvp-tarot-hardening`), pero la imagen que usa el
   contenedor actual se construyó **antes**: dentro del contenedor funcionan solo porque se copiaron
   a mano con `docker cp`. `docker compose restart` (o `stop` + `start`) los conserva, pero
   **`docker compose up -d` sin `--build` recrea el contenedor desde la imagen vieja y los pierde**.
   Mientras el build no sea reproducible (`#17 exporting layers` se queda colgado), la alternativa es
   volver a copiarlos y reiniciar:
   ```powershell
   docker cp src\open_llm_vtuber\scheduler open-llm-vtuber:/app/src/open_llm_vtuber/scheduler
   docker cp src\open_llm_vtuber\config_manager\scheduler.py open-llm-vtuber:/app/src/open_llm_vtuber/config_manager/scheduler.py
   docker cp src\open_llm_vtuber\config_manager\main.py open-llm-vtuber:/app/src/open_llm_vtuber/config_manager/main.py
   docker cp src\open_llm_vtuber\server.py open-llm-vtuber:/app/src/open_llm_vtuber/server.py
   docker cp src\open_llm_vtuber\routes.py open-llm-vtuber:/app/src/open_llm_vtuber/routes.py
   docker cp src\open_llm_vtuber\websocket_handler.py open-llm-vtuber:/app/src/open_llm_vtuber/websocket_handler.py
   docker cp src\open_llm_vtuber\conversations\conversation_handler.py open-llm-vtuber:/app/src/open_llm_vtuber/conversations/conversation_handler.py
   docker cp scripts\smoke_test.py open-llm-vtuber:/app/scripts/smoke_test.py
   docker compose restart
   ```
9. **[Cerrar la Fase 2 con datos]** A23 y A24 ya están implementados (ver §4.3 y §9.4); lo que falta
   es el criterio empírico de la fase. Durante el próximo directo de 30–60 min, consultar
   `GET /api/metrics` cada pocos minutos y comprobar `turn_seconds.p95 < 8`, `first_audio_seconds.p95`
   estable, `queue.max_depth` acotado y `without_audio` a 0. Si el ancho de banda es el problema,
   cambiar `system_config.audio_export.format` a `'mp3'` y repetir: el tráfico debe caer ~10×.
10. **[Fase 3 · prueba manual pendiente]** El contrato `stage-update`, el cliente OBS y el overlay de
    producción están probados sin red (`python scripts/test_stage_obs.py` = 27 tests;
    `node scripts/test_overlay_protocol.js` = 13 tests) y **cruzados** contra los bytes reales
    (`node scripts/test_overlay_wire.js` = 10 tests; `python scripts/test_overlay_fixtures.py` = 9), pero
    **aquí no se puede ejecutar OBS junto con
    Docker**. Protocolo completo en §4.4: (a) sin OBS, abrir `/web-tool/stage-test.html` y comprobar que
    `POST /api/stage` devuelve `delivered: 1` y cambia el fondo; (b) con OBS 28+ y
    `obs.enabled: true`, añadir `/web-tool/overlay.html` como Browser Source, ver
    `Scheduler: OBS scenes available: …` en el log y el cambio de escena al disparar un job.
    **No bloquea el resto del MVP**: el código de la fase 3 está cerrado y cubierto por tests.
11. **[Audio de la Fase 3 — hecho]** El overlay de producción (`web_tool/overlay.html` +
    `overlay-protocol.js`, §4.5) ya reproduce los mensajes `audio` en orden y manda
    `frontend-playback-complete`, así que el turno cierra al terminar el audio. Falta lo de siempre: el
    arte definitivo y el lip-sync con Live2D (el overlay pinta escenario/props/subtítulo y la voz).
13. **[Prueba en vivo del tarot — pendiente de motor]** El código está cerrado; falta ejecutarlo con
    servidor real. **Aquí el motor de Docker no responde** (`docker info` se cuelga), así que el orden es:
    1. `docker compose up -d --build` y esperar `Uvicorn running on http://0.0.0.0:12393`.
    2. `python scripts/smoke_test.py` → `SMOKE TEST PASSED` (LLM + TTS vivos).
    3. `python scripts/tarot_smoke.py --no-speak` → cartas en el socket + `GET /api/tarot` correcto
       (no necesita TTS).
    4. `python scripts/tarot_smoke.py` → además audio, `frontend-playback-complete` y
       `conversation-chain-end` en menos de 120 s.
    5. OBS: Browser Source `http://localhost:12393/web-tool/overlay.html` y, en otra ventana,
       `http://localhost:12393/web-tool/operator.html`; pulsar **Tirada de 3** y ver las tres cartas
       (las invertidas salen del revés). El HUD debe reflejar stage, props y la tirada.
    6. TikTok: arrancar `scripts/run_tiktok_live.py`, mandar un regalo de prueba (≥ `min_gift_coins`) y
       comprobar el turno de agradecimiento + «¿qué quieres saber?»; después comentar con la pregunta y
       ver la tirada dirigida a ese usuario. Probar también `!carta` y `!tirada 3` en un comentario.
    7. Qué mirar: `Tarot: 3 card(s) -> 1 overlay(s)` en el log, `Scheduler: job '…' drew …` si es por
       horario, y `GET /api/tarot` con `asker`/`question`/`cards`.

## 7. Chuleta de comandos

```powershell
cd d:\Open-LLM-VTuber

powershell -ExecutionPolicy Bypass -File scripts\docker_up.ps1   # preflight (conf.yaml, host, motor) + up -d + espera
docker compose up -d                  # crear/arrancar
docker compose ps                     # estado + puertos
docker compose logs -f                # seguir logs (espera "Uvicorn running on http://0.0.0.0:12393")
docker compose stop                   # PARAR sin eliminar el contenedor (up -d lo reanuda)
docker compose down                   # parar y eliminar (habrá que volver a up -d)
docker compose up -d --force-recreate # recrear (tras cambiar el compose)
docker compose restart                # reiniciar manteniendo el contenedor

# Comprobaciones
curl.exe -s -o NUL -w "%{http_code}" http://localhost:12393/            # -> 200
docker compose exec -T open-llm-vtuber uv pip show edge-tts             # -> Version: 7.3.1
docker compose exec -T open-llm-vtuber ls -la /app/conf.yaml            # -> symlink a /app/conf/conf.yaml
docker compose exec -T open-llm-vtuber sh -c "grep -n 'host:' /app/conf.yaml"   # -> host: '0.0.0.0'
docker compose exec -T open-llm-vtuber ls -la /app/cache                # los .mp3 deben pesar > 0 bytes
```

## 8. Notas de la sesión anterior (para no repetir trabajo)

- El log de Uvicorn imprime **`config.host` textual**: si vuelve a aparecer `http://localhost:12393` en vez de
  `http://0.0.0.0:12393`, es que **no se está leyendo tu conf.yaml** (symlink perdido) — problema A.
- El script **no acepta `--host`** por CLI (`run_server.py` solo define `--verbose` y `--hf_mirror`);
  host/port salen **solo** del YAML.
- El `ENV CONFIG_FILE=/app/conf/conf.yaml` del `dockerfile` es **código muerto** (ningún Python lo lee).
- `uv add` **no** actualiza una versión ya fijada en `uv.lock`; hay que usar `>=version` o
  `uv lock --upgrade-package <pkg>`.
- Al dejar procesos `uv` huérfanos (shell cerrado) se quedan al 99% CPU reteniendo el lock del venv y
  bloquean cualquier otro `uv`; se soluciona recreando el contenedor.
- La documentación oficial (FAQ y Quick Start) **no** cubre aún este fallo de edge-tts.
- No se debe usar `network_mode: host` (en Docker Desktop para Windows no expone el localhost de Windows).

### 8.1 `ERROR: conf.yaml is required.` al arrancar el contenedor

Sale del entrypoint (`/usr/local/bin/start-app`, generado en el `dockerfile`) cuando **no existe
`/app/conf/conf.yaml` dentro del contenedor**. `run_server.py` lee `read_yaml("conf.yaml")`, o sea
`/app/conf.yaml`, y el entrypoint crea ese symlink → `/app/conf/conf.yaml`; si no hay fichero, sale con
`exit 1` antes de llegar a Python.

| Causa | Cómo se detecta | Arreglo |
|---|---|---|
| Se lanzó la **imagen sin volumen** (`docker run <imagen>` o "Run" de Docker Desktop) | `docker inspect <contenedor> --format '{{json .Mounts}}'` no muestra `/app/conf` como *bind* | `docker compose up -d` desde `d:\Open-LLM-VTuber` (el compose monta `./conf:/app/conf`) |
| Bind mount a una ruta equivocada (p. ej. `-v ./conf.yaml:/app/conf.yaml`, o `-v ./conf:/app/conf` lanzado desde **otro** directorio) | dentro del contenedor `ls -l /app/conf` está vacío o es un directorio creado por Docker | montar el **directorio** `...\Open-LLM-VTuber\conf` en `/app/conf` y no sobrescribir `command:` (el symlink lo crea `start-app`) |
| No existe `conf/conf.yaml` en el host (está en `.gitignore`, un clon nuevo no lo tiene) | `Test-Path conf\conf.yaml` → `False` | `Copy-Item conf.yaml conf\conf.yaml` (o `config_templates\conf.default.yaml` + `host: '0.0.0.0'`) |
| Docker Desktop todavía arrancando | `docker info` → `Internal Server Error ... /v1.47/version` | esperar a "Engine running" / reiniciar Docker Desktop |

Comando único que comprueba todo lo anterior y arranca:

```powershell
cd d:\Open-LLM-VTuber
powershell -ExecutionPolicy Bypass -File scripts\docker_up.ps1        # añade -Build para reconstruir
```

El script se coloca en la raíz, crea `conf\conf.yaml` si falta, avisa si `system_config.host` no es
`0.0.0.0`, verifica el motor, hace `docker compose up -d`, espera `Uvicorn running` y comprueba con
`ls -l /app/conf/conf.yaml /app/conf.yaml` que el symlink existe. Los mensajes del entrypoint ahora
(tras `docker compose build`) también dicen qué montar y apuntan a este script.

> **OBS con la app en Docker:** el contenedor no ve el `127.0.0.1` de Windows. Pon
> `scheduler_config.obs.host: host.docker.internal` (y `enabled: true`), deja el servidor WebSocket de
> OBS escuchando en el puerto 4455 y acepta el aviso del Firewall de Windows. El overlay sí se abre
> desde Windows en `http://localhost:12393/web-tool/stage-test.html`.



## 9. Seguridad y observabilidad (auditoría A22 y §5.3) — guía de uso

Implementado en `src/open_llm_vtuber/security.py`, `metrics.py` y `routes.py`, cableado en `server.py`.
**Todo es opt-in:** sin variables de entorno el comportamiento es el de antes (show local sin auth), así que
no puede romper una instalación existente.

### 9.1 Variables de entorno

| Variable | Para qué sirve | Sin definir |
|---|---|---|
| `VTUBER_WS_TOKEN` | Si **no** está vacía, todo handshake de `/client-ws` y `/proxy-ws` debe presentarla (`?token=...` o `Authorization: Bearer ...`); si falta o no coincide, el servidor cierra con código **1008** (el cliente ve un 403 en el handshake). `GET /api/metrics` responde **401** `{"error":"unauthorized"}`. La comparación es en tiempo constante (`hmac.compare_digest`). | sin auth (como antes) |
| `VTUBER_CORS_ORIGINS` | Orígenes extra **separados por comas** que pueden leer respuestas cross-origin (p. ej. un overlay en otro dominio). Se normalizan (se descarta el `/` final). `*` reactiva el comodín antiguo, pero ahora con `allow_credentials=False` (el comodín con credenciales es lo que los navegadores rechazan y lo que A22 quería quitar). | sólo loopback (`localhost`, `127.x`, `[::1]`) + el `host` de `conf.yaml` (http/https, con puerto) + regex para los rangos RFC 1918 en cualquier puerto |
| `VTUBER_METRICS_WINDOW` | Cuántos turnos y muestras de cola se guardan en memoria (ventana del p95). | `200` |

> ⚠️ **La UI del navegador NO añade el token.** No hay ninguna referencia a `client-ws` ni a `token` en
> `frontend/`: si defines `VTUBER_WS_TOKEN`, `http://localhost:12393` seguirá abriendo pero el WebSocket
> será rechazado (sin voz ni animación). Los clientes que **sí** lo soportan son
> `scripts/smoke_test.py --token ...` y `scripts/run_tiktok_live.py` (lee la variable del entorno).
> Para el show local en Docker: **déjala sin definir**; úsala cuando el puerto salga de tu máquina
> (LAN, túnel, Cloudflare) o cuando el overlay sea un cliente propio.

Cómo pasarlas al contenedor (el `docker-compose.yml` actual **no** las pasa, son opt-in):

```powershell
# opción rápida: variable en la sesión + recrear
$env:VTUBER_WS_TOKEN = 'un-secreto-largo-y-aleatorio'
docker compose up -d --force-recreate
docker compose exec -T open-llm-vtuber sh -c 'echo $VTUBER_WS_TOKEN'   # comprobar que llegó
```

```yaml
# opción permanente: añadir al servicio open-llm-vtuber de docker-compose.yml
    environment:
      VTUBER_WS_TOKEN: "${VTUBER_WS_TOKEN}"
      VTUBER_CORS_ORIGINS: "https://overlay.example,https://otro.example"
```

### 9.2 `GET /api/metrics` (criterio de aceptación: p95 del turno < 8 s)

Read-only, no toca el estado de la conversación, se puede consultar en mitad de un directo.
Forma del JSON (`metrics.turn_metrics.snapshot()`):

| Campo | Contenido |
|---|---|
| `turns` | `started`, `completed`, `interrupted`, `failed`, `active`, `overlaps` (segundo trigger con el turno anterior aún abierto) y `without_audio` (turnos completados sin audio) |
| `turn_seconds`, `first_audio_seconds`, `queue.wait_seconds` | `count`, `avg`, `p50`, `p95`, `max` de la ventana |
| `queue` | `depth` (última muestra) y `max_depth` del proxy |
| `active_turns` | `key`, `kind` y `elapsed_s` de los turnos en curso |
| `last_turn` | último turno cerrado (`outcome`, `duration_s`, `first_audio_s`) |
| `targets` | `p95_turn_seconds: 8.0` y `p95_ok` (`null` mientras no haya turnos) |

```powershell
# sin token definido
curl.exe -s http://localhost:12393/api/metrics

# con token definido: 401 sin credencial, 200 con ella
curl.exe -s -o NUL -w "%{http_code}`n" http://localhost:12393/api/metrics
curl.exe -s -H "Authorization: Bearer $env:VTUBER_WS_TOKEN" http://localhost:12393/api/metrics
curl.exe -s "http://localhost:12393/api/metrics?token=$env:VTUBER_WS_TOKEN"
```

### 9.3 Comprobaciones de esta capa (lo que era "pendiente" en §6)

```powershell
# 1) lint + formato: lo mismo que ejecuta .pre-commit-config.yaml.
#    El CI (.github/workflows/ruff.yml) sólo ejecuta el check, no el formateo.
uv run pre-commit run --all-files

# alternativa sin uv, con el ruff standalone (v0.9.6, la misma que fija el pre-commit):
#   ruff check .          -> "All checks passed!"
#   ruff format --check . -> sólo config_manager/asr.py queda fuera, y ya venía así de upstream

# 2) tests de seguridad + métricas (stdlib puro: 39 pasan, 5 se saltan sin numpy/torch)
uv run python scripts/test_security_metrics.py

# 3) smoke end-to-end (necesita servidor + LLM + TTS reales)
uv run python scripts/smoke_test.py --url http://127.0.0.1:12393
uv run python scripts/smoke_test.py --url http://127.0.0.1:12393 --token $env:VTUBER_WS_TOKEN

# 4) tests de A23/A24 (formato de audio + resiliencia de GPT-SoVITS)
uv run python scripts/test_audio_hardening.py

# 5) tests de la fase 3 (contrato stage-update + cliente OBS v5, sin red ni OBS)
uv run python scripts/test_stage_obs.py

# 6) lógica del overlay de producción (§4.5): solo necesita Node, nada más
node scripts/test_overlay_protocol.js

# 7) contrato cruzado backend -> overlay con los bytes reales
node scripts/test_overlay_wire.js            # 11 tests (Node)
python scripts/test_overlay_fixtures.py      # 10 tests (Python)
python scripts/export_overlay_fixtures.py    # regenerar tras tocar el backend
python scripts/export_overlay_fixtures.py --check   # exit 1 si el fixture es viejo

# 8) baraja y tirada de tarot (§4.6)
python scripts/test_tarot.py                 # 33 tests, sin dependencias
python scripts/test_tarot_commands.py        # 19 tests: !carta / !tirada y payload compartido
python scripts/test_donations.py             # 16 tests: donantes pendientes, TTL y frames
python scripts/make_tarot_cards.py --check   # el mazo SVG de reserva sigue al día
python scripts/fetch_tarot_art.ps1           # (re)descarga el mazo RWS (dominio público)

# 9) prueba en vivo del tarot (necesita servidor arrancado)
python scripts/tarot_smoke.py --no-speak     # cartas + API, sin TTS
python scripts/tarot_smoke.py                # + audio, ack y chain-end
```

**Estado en esta máquina (Windows, sin `uv`):** los pasos 2, 4 y 5 se ejecutan con el Python del
sistema (`python scripts/test_security_metrics.py` -> `Ran 39 tests ... OK (skipped=5)`,
`python scripts/test_audio_hardening.py` -> `Ran 12 tests ... OK`,
`python scripts/test_stage_obs.py` -> `Ran 27 tests ... OK`); los pasos 1 y 3 requieren `uv sync`
(el `pyproject.toml` exige `>=3.10,<3.13` y aquí hay Python 3.14). El paso 1 se puede hacer con el
ruff standalone **0.9.6** (la versión que fija el pre-commit): `ruff check` + `ruff format --check`
sobre los ficheros tocados en la fase 3 -> `All checks passed!` / `8 files already formatted`.
Los YAML se validaron cargándolos con `SchedulerConfig` (pydantic) en un venv temporal: las dos
plantillas y `conf/conf.yaml` dan `obs.enabled=False`, `port=4455` y 4 jobs.
El paso 7 **no necesita nada instalado**: el exportador pone shims de `loguru`/`numpy`/`pydantic`/`pydub`
solo si faltan y sustituye el decodificado de audio por un chunk determinista, así que aquí da
`Ran 9 tests ... OK` y `pass 10 / fail 0`.

### 9.4 Fase 2 — audio configurable (A23) y resiliencia de GPT-SoVITS (A24)

Ambos son **retrocompatibles**: si no se toca el `conf.yaml`, el comportamiento es el de antes
(salvo que ahora un fallo de GPT-SoVITS se reintenta y se registra en vez de perderse en silencio).

**A23 — formato del audio que viaja por el WebSocket**

```yaml
system_config:
  audio_export:
    format: 'wav'   # 'wav' (LAN: menos latencia, sin transcodificar) | 'mp3'
    bitrate: '64k'  # sólo se usa con mp3
```

| | WAV (default) | MP3 64k |
|---|---|---|
| Tráfico (24 kHz mono, base64) | ~64 KB/s | ~8 KB/s (~10× menos) |
| Latencia extra por frase | ~0 | transcodificación con ffmpeg |
| Requisito | ninguno | `ffmpeg` con `libmp3lame` (ya está en la imagen) |
| Cuándo usarlo | OBS/overlay en la misma máquina | overlay en otra máquina o por túnel |

El payload de audio incluye `"audio_format": "wav"|"mp3"` (también en los payloads silenciosos),
para que un overlay propio elija el MIME del `data:` URL; los reproductores con WebAudio
(`decodeAudioData`) lo detectan solos. El esquema sólo acepta `wav` o `mp3`: un typo impide arrancar
con un error de validación claro (la clave entera es opcional y por defecto vale `wav`).

**A24 — reintentos, timeout y semáforo en `tts/gpt_sovits_tts.py`**

```yaml
tts_config:
  tts_model: 'gpt_sovits_tts'
  gpt_sovits_tts:
    api_url: 'http://127.0.0.1:9880/tts'
    media_type: 'wav'
    streaming_mode: 'false'
    request_timeout: 20.0   # segundos por intento
    max_retries: 2          # reintentos tras timeout / 5xx / cuerpo no-audio
    retry_backoff: 0.5      # espera del 1.er reintento; se duplica
    max_concurrency: 2      # peticiones simultáneas contra GPT-SoVITS
```

- Un **`4xx` no se reintenta** (URL o `ref_audio_path` mal): falla rápido y queda en el log.
- Un `200` que **no es audio** (GPT-SoVITS con el modelo sin cargar devuelve HTML) se detecta por
  la firma del cuerpo y se reintenta, en vez de guardar un `.wav` corrupto.
- Agotados los reintentos **se lanza la excepción**: `TTSTaskManager` ya la convierte en payload
  silencioso, así que el turno sigue y las frases mantienen el orden (antes se devolvía `None` y
  la frase desaparecía sin más).
- `max_concurrency` bajo = GPU/CPU sin saturar; súbelo sólo si tu GPT-SoVITS soporta batching real.
- `streaming_mode` sigue en `'false'`: el pipeline espera el WAV completo por frase.

**Comprobación rápida (sin servidor real):** `python scripts/test_audio_hardening.py` cubre el
cambio de formato/bitrate, el payload silencioso, la validación de la config, el timeout acotado,
el reintento de errores de transporte, el agotamiento de `5xx`, el `4xx` sin reintento, el `200`
no-audio, `max_retries: 0` y el tope de concurrencia con 6 hilos en paralelo.


## 10. CI (GitHub Actions) en el fork

En un fork los workflows no se ejecutan hasta habilitarlos una sola vez:
`https://github.com/<usuario>/Open-LLM-VTuber/actions` →
*"I understand my workflows, go ahead and enable them"*. La API no sirve para
eso: hasta que no se aprueban, `GET /actions/workflows` devuelve
`total_count: 0` y `PUT /actions/workflows/{id}/enable` responde 404 porque el
workflow aún no tiene `id`.

### 10.1 Por qué el check Ruff estaba en rojo

`astral-sh/ruff-action@v3` resuelve la versión desde `pyproject.toml`
(`ruff>=0.8.6` → la última, 0.17.1), no desde `.pre-commit-config.yaml`.
Con esa versión el árbol no pasa:

| árbol | violaciones con ruff 0.17.1 |
| --- | --- |
| `origin/main` (`992309c`) | 927 |
| esta rama | 1038 (las 927 + 111 de los módulos nuevos) |

O sea: el check ya fallaba en `main`, así que no podía bloquear ninguna PR.
El workflow fija ahora `version: "0.9.6"` (la misma que el pre-commit); con
ella `ruff check .` no reporta nada.

### 10.2 Validación hecha

- Run `Ruff` sobre `94f764e` → `success`; el log del job muestra
  `Successfully installed ruff version 0.9.6` y `ruff check` sin salida.
- Reproducido en local con el `ruff.exe` 0.17.1 de la release: HEAD 1039 líneas
  de salida vs. 927 en un worktree limpio de `origin/main` (cuadra con el CI).
- El workflow sólo ejecuta `ruff check`; el formato se comprueba con
  `ruff format --check .` en local (ver §9.3).

### 10.3 Consultar los runs sin `gh`

```powershell
# token de Git Credential Manager, sin imprimirlo
$cred = ("protocol=https`nhost=github.com`n`n" | git credential fill)
$tok = ($cred | Where-Object { $_ -like 'password=*' }) -replace '^password=',''
$h = @{ Authorization = "Bearer $tok"; Accept = 'application/vnd.github+json' }
Invoke-RestMethod -Uri 'https://api.github.com/repos/guarodriguezpa/Open-LLM-VTuber/actions/runs?per_page=5' -Headers $h |
    Select-Object -ExpandProperty workflow_runs |
    Select-Object name, head_branch, status, conclusion, html_url
```

Nota: al abrir una PR contra el upstream, los workflows corren en el repo base;
si el autor es un colaborador nuevo quedan en `action_required` hasta que un
mantenedor los apruebe, así que verás los checks "Waiting approval".

