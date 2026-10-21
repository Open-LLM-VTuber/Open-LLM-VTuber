# Despliegue en la nube — Fase 1 (Google Cloud)

Prueba de concepto: **el agente vive en GCP**, **OBS y el conector de TikTok
siguen en tu PC**. Al final de esta guía puedes estar en directo el mismo día.

```
        TU PC (Windows)                                GCP · Ubuntu 24.04
┌────────────────────────────────┐          ┌──────────────────────────────────┐
│ OBS                            │          │ Caddy (80/443, TLS automático)   │
│  └ Browser Source ─────────────┼── HTTPS ─┤   └─ vtuber-app:12393 (FastAPI)  │
│      overlay.html?token=…      │◄─ WSS ───┤       /proxy-ws  /client-ws     │
│      avatar + audio            │          │       /web-tool  /api/*          │
│  └ RTMP ──► TikTok LIVE        │          │  LLM: API (OpenRouter, …)        │
│                                │          │  TTS: edge-tts (API Microsoft)   │
│ run_tiktok_live.py ────────────┼── WSS ───┤  SIN GPU · SIN TikTokLive        │
│  (lee el chat de TikTok FR)    │          │  SIN OBS                         │
└────────────────────────────────┘          └──────────────────────────────────┘
```

**Reparto de responsabilidades**

| Pieza | Dónde | Por qué |
|---|---|---|
| Servidor del agente (`uvicorn`) | VM de GCP | Es lo que tu PC ya no puede con Docker |
| TTS (`edge-tts`) y LLM (API) | VM de GCP | Sin GPU, coste por token/carácter |
| Render del avatar y vídeo | OBS en tu PC | El contenedor **no** renderiza ni codifica vídeo |
| Emisión a TikTok | OBS en tu PC | Sube el RTMP con tu clave de emisión |
| Lectura del chat de TikTok | Conector en tu PC | Evita pedir el chat desde una IP de datacenter |

**Qué NO incluye esta fase:** multi-cliente, backups automáticos, control
remoto de OBS, grabación en la nube ni el conector dentro de la imagen.

---

## 1. Requisitos y coste

- Un dominio (o subdominio) que puedas editar: `vtuber.tudominio.com`.
- Proyecto de GCP con facturación activa.
- Cuenta de TikTok **habilitada para LIVE** (en algunas regiones pide seguidores).
- OBS actualizado y conexión de subida estable (5 Mbps sobran para 1080p30).
- En el PC: Python **3.12** (TikTokLive soporta 3.10–3.13; **3.14 no**).

Coste orientativo de la prueba (París, `europe-west9`):

| Concepto | Aprox. |
|---|---|
| `e2-medium` (2 vCPU compartidas, 4 GB) | ~25–30 USD/mes |
| Disco `pd-balanced` 30 GB | ~3 USD/mes |
| IP estática **conectada** | sin coste (solo se cobra si está suelta) |
| Salida (audio mp3 + WS) | céntimos: 28 MB/hora por overlay |
| LLM | el único variable: 0,5–3 USD por directo de 3 h |

Si el build inicial se queda sin memoria, sube un escalón a `e2-standard-2`
(8 GB) solo durante la compilación (ver §3.5).

---

## 2. Crear la infraestructura en GCP

Sustituye `PROJECT_ID` y el dominio. Todos los comandos son de **Cloud Shell**
o de tu `gcloud` local.

```bash
gcloud config set project PROJECT_ID
gcloud services enable compute.googleapis.com

# 1) IP estática regional (sobrevive a reinicios de la VM)
gcloud compute addresses create vtuber-ip --region=europe-west9
gcloud compute addresses describe vtuber-ip \
  --region=europe-west9 --format="value(address)"
```

Apunta esa IP: es la que va en el DNS.

```bash
# 2) VM Ubuntu 24.04 LTS, 2 vCPU / 4 GB / 30 GB
gcloud compute instances create vtuber-poc \
  --zone=europe-west9-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-balanced \
  --address=vtuber-ip \
  --tags=vtuber-web

# 3) Cortafuegos: SOLO 80 y 443. El puerto 12393 no se abre nunca.
gcloud compute firewall-rules create allow-vtuber-web \
  --allow=tcp:80,tcp:443 \
  --target-tags=vtuber-web \
  --source-ranges=0.0.0.0/0
```

**DNS antes de arrancar Caddy** (Let's Encrypt valida el dominio):

```
Tipo A   vtuber   →   IP_ESTÁTICA
```

Si usas Cloudflare, deja el registro en **DNS only** (nube gris) hasta que el
certificado esté emitido; el proxy naranja puede romper el desafío HTTP-01.

Comprueba desde tu PC, **contra el DNS público** (no el del ISP):

```powershell
nslookup vtuber.tudominio.com 8.8.8.8
```

El nombre tiene que coincidir **exactamente** con `DOMAIN` en `.env`. Un typo
(`vtube` vs `vtuber`) da `Non-existent domain` y Caddy no podrá emitir el
certificado, aunque la VM y el firewall estén perfectos.

---

## 3. Preparar la VM

### 3.1 Entrar e instalar Docker

```bash
gcloud compute ssh vtuber-poc --zone=europe-west9-a

sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker            # o cierra y vuelve a entrar por SSH
docker version
```

### 3.2 Swap (el primer build descarga torch/CUDA)

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

### 3.3 Código y ficheros que no están en git

Sube primero tu rama con los ficheros nuevos (`docker-compose.prod.yml`,
`Caddyfile`, `.env.example`, `doc/DESPLIEGUE-NUBE.md`, `pyproject.toml`,
`uv.lock`):

```powershell
cd D:\Open-LLM-VTuber
git remote -v                      # mira cómo se llama tu remoto (fork/origin)
git status --short                 # revisa lo que vas a subir
git add -A
# si NO quieres subir el puntero del submódulo `frontend`:
# git restore --staged frontend
git commit -m "chore(deploy): kit de despliegue en GCP (fase 1)"
git push fork feat/mvp-tarot-hardening
```

En la VM:

```bash
git clone --branch feat/mvp-tarot-hardening \
  https://github.com/TU_USUARIO/Open-LLM-VTuber.git ~/vtuber
cd ~/vtuber
mkdir -p conf frontend-build           # montajes que deben existir
ls docker-compose.prod.yml Caddyfile .env.example
```

> `conf/conf.yaml` está en `.gitignore`: cópialo desde tu PC.
>
> En Windows, `gcloud compute scp` usa `pscp` y **no expande `~`**, y el
> directorio puede ser de `root` (Docker crea los montajes). Sube el fichero a
> `/tmp` y colócalo con `sudo install`:
>
> ```powershell
> gcloud compute scp .\conf\conf.yaml vtuber-poc:/tmp/conf.yaml --zone=europe-west9-a
> ```
>
> ```bash
> gcloud compute ssh vtuber-poc --zone=europe-west9-a
> sudo mkdir -p ~/vtuber/conf
> sudo install -o "$USER" -g "$USER" -m 644 /tmp/conf.yaml ~/vtuber/conf/conf.yaml
> sudo chown -R "$USER:$USER" ~/vtuber
> ls -l ~/vtuber/conf/conf.yaml
> ```

### 3.4 Configurar `.env` y `conf.yaml`

```bash
cd ~/vtuber
cp .env.example .env
TOKEN=$(openssl rand -base64 32)
sed -i "s#^VTUBER_WS_TOKEN=.*#VTUBER_WS_TOKEN=$TOKEN#" .env
sed -i "s#^DOMAIN=.*#DOMAIN=vtuber.tudominio.com#" .env
sed -i "s#^ACME_EMAIL=.*#ACME_EMAIL=tu@correo.com#" .env
sed -i "s#^VTUBER_CORS_ORIGINS=.*#VTUBER_CORS_ORIGINS=https://vtuber.tudominio.com#" .env
grep -v '^#' .env | grep .              # apunta el token: lo usarás en el PC
```

En `conf/conf.yaml` (con `nano conf/conf.yaml`) revisa estas claves:

```yaml
system_config:
  host: '0.0.0.0'          # imprescindible: si no, Caddy no llega al contenedor
  port: 12393
  enable_proxy: true       # expone /proxy-ws para el conector
  audio_export:
    format: 'mp3'          # ~8 KB/s en vez de ~64 KB/s por Internet

live_config:
  tiktok_live:
    enabled: false         # el conector NO corre aquí

scheduler_config:
  obs:
    enabled: false         # OBS está en tu PC; la nube no lo alcanza
```

Y la clave del LLM en `character_config.agent_settings.llm_configs.openai_llm`
(`llm_api_key`), junto con `base_url` y `model` si usas OpenRouter.

Comprueba:

```bash
grep -n "host: '0.0.0.0'\|format: 'mp3'\|enable_proxy" conf/conf.yaml
```

> ⚠️ `conf/conf.yaml` lleva la clave del LLM en claro. No lo subas al repo
> (ya está en `.gitignore` y en `.dockerignore`), y **rota la clave** si alguna
> vez se ha compartido por chat, captura o commit accidental.

> Si decides no distribuir el modelo Live2D, borra `live2d-models/mao_pro/`
> **pero deja la carpeta `live2d-models/` creada**: `server.py` la monta con
> `StaticFiles`, que aborta el arranque si el directorio no existe.

### 3.5 Construir y arrancar

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f open-llm-vtuber
```

Esperado en el log:

```
Starting server on 0.0.0.0:12393
WebSocket token auth enabled (VTUBER_WS_TOKEN is set)
Audio export format: mp3 (64k)
Uvicorn running on http://0.0.0.0:12393
```

Caddy arranca cuando el contenedor está `healthy` y emite el certificado:

```bash
docker compose -f docker-compose.prod.yml logs -f caddy
```

> **Si el build muere** (`Killed`, `exit code 137`): es memoria. Para la VM,
> cambia a 8 GB, compila, y vuelve a bajarla:
> ```bash
> gcloud compute instances stop vtuber-poc --zone=europe-west9-a
> gcloud compute instances set-machine-type vtuber-poc \
>   --zone=europe-west9-a --machine-type=e2-standard-2
> gcloud compute instances start vtuber-poc --zone=europe-west9-a
> ```

---

## 4. Verificar el servidor antes de tocar TikTok

En la VM:

```bash
cd ~/vtuber
set -a; . ./.env; set +a          # carga DOMAIN y VTUBER_WS_TOKEN

# 1) TLS + página del overlay
curl -sI "https://$DOMAIN/web-tool/overlay.html" | head -n 3
# Si el DNS aún no resuelve desde la propia VM:
# curl -sI --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/web-tool/overlay.html"

# 2) El token protege la API: 401 sin él, 200 con él
curl -s -o /dev/null -w "sin token: %{http_code}\n" "https://$DOMAIN/api/metrics"
curl -s -H "Authorization: Bearer $VTUBER_WS_TOKEN" \
  "https://$DOMAIN/api/metrics" | head -c 300; echo

# 3) edge-tts correcto (7.3.x, ya no hace falta `uv add` al arrancar)
docker compose -f docker-compose.prod.yml exec open-llm-vtuber \
  python -c "import importlib.metadata as m; print('edge-tts', m.version('edge-tts'))"

# 4) TikTokLive NO debe estar en la imagen
docker compose -f docker-compose.prod.yml exec open-llm-vtuber \
  python -c "import importlib.util as u; print('TikTokLive:', u.find_spec('TikTokLive') is not None)"
```

Resultado esperado: `HTTP/2 200`, `sin token: 401`, un JSON de métricas,
`edge-tts 7.3.1`, `TikTokLive: False`.

---

## 5. Tu PC: OBS

### 5.1 Fuente de navegador

1. OBS → **Fuentes → + → Navegador**.
2. Ancho **1920**, alto **1080**.
3. URL (una sola línea):

```
https://vtuber.tudominio.com/web-tool/overlay.html?token=TU_TOKEN&avatar=/avatars/mao.png&debug=1
```

4. Desmarca **“Apagar la fuente cuando no esté visible”**.
5. Desmarca **“Actualizar el navegador cuando la escena se activa”** (así no
   se reconecta el WebSocket en cada cambio de escena).
6. `debug=1` muestra el HUD (estado del WS, última tirada). Quítalo cuando
   todo funcione.

El fondo de la página es transparente: no hace falta “capturar ventana”.

### 5.2 Prueba de punta a punta (sin TikTok)

Abre en Chrome:

```
https://vtuber.tudominio.com/web-tool/operator.html?token=TU_TOKEN
```

Pulsa **“Tirar 1 carta”** con **“leer en voz alta”** marcado. Debe ocurrir:

- el overlay de OBS muestra la carta y el subtítulo,
- suena la voz de edge-tts por la fuente del navegador,
- el HUD pasa por `connected` → `chain-end`.

Si hay voz pero no la oyes fuera del directo: **Propiedades avanzadas de audio
→ Monitorear y emitir** en la fuente del navegador.

### 5.3 Emisión a TikTok

- OBS → **Ajustes → Emisión**. Si tu OBS lista **TikTok**, elige el servicio y
  conecta la cuenta. Si no, usa **Servidor personalizado** con la **URL RTMP**
  y la **clave de emisión** que te da TikTok LIVE.
- Formato: 1080×1920 (vertical) o 1920×1080, 30 fps, 4–6 Mbps.
- La emisión sale **de tu PC**, no de la VM: la IP de GCP nunca habla con el
  RTMP de TikTok.
- TikTok puede exigir cuenta habilitada para LIVE; compruébalo antes del show.

---

## 6. Tu PC: conector de TikTok

El conector corre **fuera de Docker**, en un entorno propio. No instala torch ni
el servidor: solo la librería de TikTok y lo que necesita para leer `conf.yaml`.

### 6.1 Entorno de Python

TikTokLive 7.0.1 soporta **Python 3.10–3.13**. Si tu `python` por defecto es
3.14, crea el entorno con 3.12:

```powershell
cd D:\Open-LLM-VTuber
py -0p                                  # lista los intérpretes instalados
# si no tienes 3.12:
# winget install -e --id Python.Python.3.12

py -3.12 -m venv .venv-connector
.\.venv-connector\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install "TikTokLive>=7,<8" websockets pyyaml pydantic loguru chardet
```

> `TikTokLive` arrastra `httpx`, `websockets-proxy`, `eulerapisdk`, etc.
> `pyyaml`, `pydantic`, `loguru` y `chardet` son para validar `conf.yaml`.

### 6.2 Configuración del conector

`scripts/run_tiktok_live.py` lee **`conf.yaml` en la raíz del repo**, no
`conf/conf.yaml`. Copia el segundo sobre el primero y edita tres claves:

```powershell
Copy-Item conf\conf.yaml conf.yaml -Force
notepad conf.yaml
```

```yaml
live_config:
  tiktok_live:
    enabled: true
    unique_id: "astrologia_egipcia"                    # sin @
    proxy_url: "wss://vtuber.tudominio.com/proxy-ws"   # el servidor de GCP
```

`proxy_url` debe ser **`wss://`** (TLS). El conector añade el token solo, a
partir de `VTUBER_WS_TOKEN`.

### 6.3 Arrancar

```powershell
$env:VTUBER_WS_TOKEN = "TU_TOKEN"        # el mismo del .env de la VM
$env:TIKTOKLIVE_REGION = "FR"            # cuenta francesa (ver §7)

python scripts\run_tiktok_live.py
```

Log esperado:

```
TikTok connector connected to proxy wss://vtuber.tudominio.com/proxy-ws
TikTokLive webcast region forced to FR
```

Prueba: desde otra cuenta, comenta `!carta` en el directo. El overlay debe
tirar una carta y leerla. El conector espera a que el overlay termine de
reproducir (`conversation-chain-end`); si el overlay no está abierto, cada turno
tarda 90 s (`TURN_TIMEOUT`) y luego continúa.

Para reiniciarlo: `Ctrl+C` y el mismo comando. El script reintenta cada 5 s si
la conexión cae, si el proxy se reinicia o si el directo termina; así sobrevive
a un reinicio del servidor a mitad de show.

---

## 7. Sala francesa desde LatAm

**TikTokLive 7.0.1 no tiene parámetro `region` ni `webcast_url`.** Lo que hace:

- elige al azar un *preset* de navegador (`Locations`: GB, CA, AU, NZ, ZA, IE,
  JM, BZ, TT) que solo cambia el fingerprint (`region`, `tz_name`, `lang`);
- resuelve el `room_id` por `unique_id` y pide la URL firmada al **firmador de
  Euler Stream** (`api.eulerstream.com`), que devuelve además las cookies
  `tt-target-idc`;
- abre el WebSocket de la sala con esas credenciales.

Por eso una sala francesa se puede leer desde Chile: la región la resuelve el
firmador, no tu IP. Aun así, dejé tres variables **opcionales** en
`src/open_llm_vtuber/live/tiktok_live.py` para los casos que fallan:

| Variable | Para qué | Ejemplo |
|---|---|---|
| `TIKTOKLIVE_REGION` | Fuerza `region`/`priority_region` del fingerprint | `FR` |
| `TIKTOKLIVE_SIGN_API_KEY` | Clave de Euler Stream; sube el límite gratuito del firmador | `euler_xxx` |
| `TIKTOKLIVE_PROXY` | Proxy HTTP/SOCKS para **HTTP y WebSocket** | `http://user:pass@eu-proxy:3128` |

```powershell
$env:TIKTOKLIVE_REGION = "FR"
# $env:TIKTOKLIVE_SIGN_API_KEY = "..."
# $env:TIKTOKLIVE_PROXY = "http://user:pass@host:3128"
```

**Diagnóstico rápido**

| Síntoma en el log | Causa probable | Arreglo |
|---|---|---|
| `SignatureRateLimitError` / HTTP `429` | límite del firmador gratuito | `TIKTOKLIVE_SIGN_API_KEY` |
| `UserOfflineError` | la cuenta no está en vivo, `unique_id` mal, o TikTok oculta la sala a tu IP | comprobar el directo; si persiste, `TIKTOKLIVE_PROXY` europeo |
| `SignAPIError … empty request. Are you being detected by TikTok?` | IP bloqueada por TikTok | proxy europeo |
| `WebcastBlockedError` (`Handshake-Msg`) | firma/sesión/proxy rechazados | probar otro proxy; no usar `sessionid` |
| Timeout / `ConnectError` | red o firmador caído | reintentar (el script lo hace) |
| Comentas y no responde | overlay cerrado o sin `/proxy-ws` | abrir el overlay en OBS |

**Plan B si tu IP no puede leer la sala:** corre el conector dentro de la VM.
Publica el puerto solo en loopback (descomenta `ports` en
`docker-compose.prod.yml`), instala el mismo entorno en Ubuntu y apunta
`proxy_url` a `ws://127.0.0.1:12393/proxy-ws`. Ventaja: red europea.
Inconveniente: TikTok ve una IP de datacenter, que es justo lo que evitamos.

---

## 8. Operación diaria

**Orden de arranque:** el servidor ya está corriendo 24/7 → OBS (abre el
overlay) → emisión en TikTok → conector en el PC.

```bash
# En la VM
cd ~/vtuber
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f --tail=200 open-llm-vtuber
docker compose -f docker-compose.prod.yml restart open-llm-vtuber

# Métricas del turno (p95 < 8 s es el criterio del proyecto)
set -a; . ./.env; set +a
curl -s -H "Authorization: Bearer $VTUBER_WS_TOKEN" \
  "https://$DOMAIN/api/metrics" | head -c 400; echo

# Vaciar el audio cacheado (seguro entre directos)
docker compose -f docker-compose.prod.yml exec open-llm-vtuber \
  sh -c 'rm -rf /app/cache/*'

# Actualizar código
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

**Backup** (solo estado; el código está en git):

```bash
cd ~/vtuber
tar czf ~/backup-$(date +%F).tgz conf avatars backgrounds characters
```

**Coste:** si dejas de probar, `gcloud compute instances stop vtuber-poc
--zone=europe-west9-a` detiene la facturación de CPU/RAM (el disco sigue).
Para parar del todo: `instances delete` + `addresses delete vtuber-ip
--region=europe-west9`.

---

## 9. Problemas típicos de esta fase

| Síntoma | Causa | Arreglo |
|---|---|---|
| `ERR_CONNECTION_REFUSED` en el dominio | DNS mal o puerto 80 cerrado | `nslookup`, regla de firewall |
| Caddy: `no such host` / `challenge failed` | Cloudflare proxy naranja o DNS sin propagar | DNS only; esperar |
| `502` desde Caddy | app no escucha en `0.0.0.0` | `system_config.host` y reiniciar |
| La página abre pero el overlay no conecta | token distinto al del `.env` | mismo `VTUBER_WS_TOKEN` |
| El overlay conecta y no hay audio | TTS 403 o formato | ver `edge-tts 7.3.1`; logs del contenedor |
| La UI oficial `/` no tiene voz | no manda el token | no la uses; usa overlay/operator |
| El conector dice `connected` y no pasa nada | chat sin eventos o sala no live | probar `!carta`; revisar §7 |
| Turnos de 90 s | overlay no conectado a `/proxy-ws` | abrir el overlay primero |
| Build `Killed` | 4 GB insuficientes | swap + `e2-standard-2` |
| Disco lleno | imágenes viejas | `docker system prune -af` |

---

## 10. Aviso legal antes de vender

- **TikTokLive** está publicado bajo **Modified AGPL-3.0** y su propio README
  dice que *no* es una API lista para producción. En esta fase es una
  herramienta que **tú** instalas en tu PC para la prueba: no la empaquetes ni
  la distribuyas dentro del producto que vendas sin revisar la licencia.
  Alternativa comercial: la API WebSocket de Euler Stream (de pago).
- Leer el chat con una librería no oficial incumple potencialmente los términos
  de TikTok y el riesgo recae en la cuenta que emite. Etiqueta el contenido
  como generado por IA cuando corresponda.
- **edge-tts** usa un endpoint no oficial de Microsoft; para un producto con
  SLA, presupuesta ElevenLabs/Azure/GPT-SoVITS.
- El código del proyecto es **MIT** (conserva el aviso). El avatar ya no usa
  Live2D; el arte que pongas necesita su propia licencia comercial
  (`doc/OVERLAY-AVATAR.md`).

---

## 11. Checklist de “está funcionando”

1. `curl -sI https://$DOMAIN/web-tool/overlay.html` → `200`.
2. `/api/metrics` → `401` sin token y `200` con token.
3. `edge-tts 7.3.1` y `TikTokLive: False` dentro del contenedor.
4. OBS: el HUD del overlay dice `connected`.
5. Operador → “Tirar 1 carta” + leer → cartas y voz en OBS.
6. Log del conector: `TikTok connector connected to proxy wss://…`.
7. Un comentario real (`!carta`) produce tirada y respuesta; `/api/metrics`
   da p95 < 8 s.
8. El directo de TikTok se ve desde otro dispositivo.




