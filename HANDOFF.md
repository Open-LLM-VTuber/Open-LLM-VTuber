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

## 7. Chuleta de comandos

```powershell
cd d:\Open-LLM-VTuber

docker compose up -d                  # crear/arrancar
docker compose ps                     # estado + puertos
docker compose logs -f                # seguir logs (espera "Uvicorn running on http://0.0.0.0:12393")
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


