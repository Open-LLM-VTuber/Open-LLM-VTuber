# Avatar sin Live2D (overlay de OBS)

El overlay de producción (`web_tool/overlay.html`) **no usa Live2D**. Dibuja un
fondo, imágenes/tarjetas, subtítulos, la voz y —desde esta capa— un personaje
que respira, parpadea y pulsa cuando habla. Así el show no carga el modelo
`mao_pro` ni el SDK de Cubism, y `LICENSE-Live2D.md` deja de aplicar al
producto que sirves a tus clientes.

## Uso

La URL del overlay acepta estos parámetros:

| Parámetro | Para qué |
|---|---|
| `avatar` | Imagen del personaje (``/avatars/astrologo.png``) |
| `avatar-blink` | Imagen con los ojos cerrados (opcional) |
| `avatar-talk` | Imagen hablando (opcional) |
| `avatar-x` | Centro horizontal, 0..1 (por defecto `0.27`) |
| `avatar-y` | Centro vertical, 0..1 (por defecto `0.52`) |
| `avatar-scale` | Escala, 0.05..10 (por defecto `1`) |
| `token` | Token compartido (A22) |

```
https://tu-dominio/web-tool/overlay.html?token=...&avatar=/avatars/astrologo.png
https://tu-dominio/web-tool/overlay.html?token=...&avatar=/avatars/astrologo.png&avatar-blink=/avatars/astrologo_parpadeo.png&avatar-talk=/avatars/astrologo_habla.png
```

- **Respiración**: CSS, bucle de 4,6 s.
- **Parpadeo**: cambia a `avatar-blink` durante 130 ms cada 3–6,5 s. Sin esa
  imagen no parpadea (no inventa un gesto raro).
- **Habla**: `is-talking` se activa cuando el `<audio>` empieza una frase y se
  desactiva al terminar o al interrumpir. Con `avatar-talk` cambia el frame;
  sin él, pulsa ligeramente.
- El avatar es una **capa propia**: una tirada de tarot reemplaza los `props`
  y nunca lo borra.

## Cambiarlo en vivo

```powershell
$body = @{ avatar = "/avatars/otro.png" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri https://tu-dominio/api/stage `
  -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer $env:VTUBER_WS_TOKEN" } `
  -Body $body
```

En bash/macOS:

```bash
curl -X POST https://tu-dominio/api/stage \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $VTUBER_WS_TOKEN" \
  -d '{"avatar": "/avatars/otro.png"}'
```

Sin `avatar` en el payload, el personaje se queda como está. El servidor cachea
el último `stage-update`, así que al recargar el overlay se restaura.

## Arte: especificaciones

- PNG con transparencia y fondo recortado (el overlay lo dibuja con sombra).
- Se muestra a `82vh` de alto (tope 1800 px) y `60vw` de ancho: con 1080p son
  ~885 px, así que prepara el original a **1000–1800 px de alto**.
- Encuadre de medio cuerpo o cuerpo entero mirando al centro; el centro cae en
  `x=0.27`, `y=0.52` (lado izquierdo, para dejar sitio a las cartas).
- `avatar-blink` y `avatar-talk` deben usar **el mismo lienzo y la misma
  posición** que `avatar`: si no están alineados, el personaje "salta" al
  cambiar de frame.
- Peso ideal < 2 MB. Nombre sin espacios ni acentos (`astrologo.png`).
- Los ficheros van en `avatars/` y se sirven en `/avatars/...`. Ese montaje
  solo permite `.png`, `.jpg`, `.jpeg`, `.gif` y `.svg` (`AvatarStaticFiles`).

## OBS

1. Fuente → **Navegador**, 1920×1080, URL del overlay con `token` y `avatar`.
2. Desactiva "Apagar la fuente cuando no esté visible".
3. El fondo sale transparente con alfa: no hace falta "capturar ventana" ni
   mantener Chrome en primer plano.
4. El audio de la fuente es la voz del agente; súbelo en el mezclador de OBS.

## Qué se puede retirar del despliegue

- `live2d-models/mao_pro/` (el modelo sample). **Deja la carpeta
  `live2d-models/` creada aunque quede vacía**: `server.py` la monta con
  `StaticFiles`, que falla al arrancar si el directorio no existe.
- El uso de la UI oficial `/` en producción: esa página sí carga Live2D desde
  `model_dict.json`. El operador usa `/web-tool/operator.html`.
- Con ello, `LICENSE-Live2D.md` ya no cubre nada de lo que distribuyes.

## Licencias del arte (esto sí importa al vender)

- Encarga el personaje con **licencia comercial por escrito** que cubra:
  emisión en directo, alojamiento en tu servidor y sublicencia a tus clientes.
- Si lo generas con IA, revisa los términos del generador (uso comercial,
  propiedad del output). Evita estilos de artistas vivos, personajes con marca
  y parecidos reconocibles.
- El código sigue siendo **MIT**: conserva el aviso de copyright al distribuirlo.

## Pruebas

```powershell
node scripts/test_overlay_avatar.js     # idle / blink / talking + timers
node scripts/test_overlay_protocol.js   # turnos y ack de audio
python scripts/test_stage_obs.py        # contrato stage-update (incluye avatar)
```
