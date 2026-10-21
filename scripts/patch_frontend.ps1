# Make the prebuilt official web UI work on this deployment.
#
# The upstream `build` bundle hardcodes:
#   DEFAULT_WS_URL   = "ws://127.0.0.1:12393/client-ws"
#   DEFAULT_BASE_URL = "http://127.0.0.1:12393"
# and parseModelUrl() calls `new URL(model_url)` without a base. With the app
# published on host port 8080 (Windows reserves 12393) the UI connected to the
# wrong port, never received `set-model-and-conf`, and then requested
# /undefined/undefined.model3.json. Deriving both URLs from window.location and
# resolving relative model URLs fixes that for any host/port (LAN, tunnel...).
#
# Optionally sets the default background to one of the files in backgrounds/.
#
# Usage (from the repository root):
#   powershell -ExecutionPolicy Bypass -File scripts/patch_frontend.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/patch_frontend.ps1 `
#       -BackgroundImage fondo_egipcio.jpg
#
# Re-run it after every scripts/fetch_frontend.ps1 (that script calls it too).

param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [string]$BackgroundImage = ""
)

$ErrorActionPreference = "Stop"

$frontend = Join-Path $Root "frontend-build"
$assets = Join-Path $frontend "assets"
if (-not (Test-Path $assets)) {
    throw "frontend-build/assets not found. Run scripts/fetch_frontend.ps1 first."
}

$jsFile = Get-ChildItem $assets -Filter "main-*.js" | Select-Object -First 1
if (-not $jsFile) {
    throw "No main-*.js bundle found under $assets."
}

$text = [System.IO.File]::ReadAllText($jsFile.FullName)
$original = $text

$replacements = @(
    @{
        Name = "WebSocket default URL"
        Old  = 'DEFAULT_WS_URL="ws://127.0.0.1:12393/client-ws"'
        New  = 'DEFAULT_WS_URL=(location.protocol==="https:"?"wss:":"ws:")+"//"+location.host+"/client-ws"'
        Required = $true
    },
    @{
        Name = "HTTP base URL"
        Old  = 'DEFAULT_BASE_URL="http://127.0.0.1:12393"'
        New  = 'DEFAULT_BASE_URL=location.origin'
        Required = $true
    },
    @{
        Name = "relative model URL resolution"
        Old  = 'function parseModelUrl(i){try{const o=new URL(i),'
        New  = 'function parseModelUrl(i){try{const o=new URL(i,location.origin),'
        Required = $true
    },
    @{
        Name = "absolute model URL from the message"
        Old  = 'const Vt=_e+Gt.model_info.url;Gt.model_info.url=Vt'
        New  = 'Gt.model_info.url=new URL(Gt.model_info.url,location.origin).href'
        Required = $true
    }
)

foreach ($item in $replacements) {
    if ($text.Contains($item.Old)) {
        $text = $text.Replace($item.Old, $item.New)
        Write-Host "patched: $($item.Name)"
    } elseif ($item.New -and $text.Contains($item.New)) {
        Write-Host "already patched: $($item.Name)"
    } elseif ($item.Required) {
        throw "Pattern not found: $($item.Name). The bundle changed; update this script."
    }
}

# The UI persists the server URL in localStorage. A saved 12393 value would
# override the patched defaults, so drop those keys once at startup. The model
# info cached there may also carry the old URL.
$indexPath = Join-Path $frontend "index.html"
$index = [System.IO.File]::ReadAllText($indexPath)
if (-not $index.Contains('data-server-url-migration')) {
    $snippet = @"
    <script data-server-url-migration>
      // Drop server settings saved for the old 12393 port; the bundle now
      // derives them from location.
      try {
        ["wsUrl", "baseUrl", "modelInfo"].forEach(function (key) {
          var value = localStorage.getItem(key);
          if (value && (value.indexOf("127.0.0.1:12393") !== -1 || value.indexOf("localhost:12393") !== -1)) {
            localStorage.removeItem(key);
          }
        });
      } catch (error) {}
    </script>
"@
    $index = $index.Replace("</head>", "$snippet</head>")
    [System.IO.File]::WriteAllText($indexPath, $index, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "patched: old 12393 settings in localStorage are discarded"
}

# Drop any saved server URL that points to a different host/port than the page
# (the host port can change when Windows reserves another range).
if (-not $index.Contains('data-server-url-migration-v2')) {
    $snippet2 = @"
    <script data-server-url-migration-v2>
      // Keep only server settings that match the page origin.
      try {
        ["wsUrl", "baseUrl"].forEach(function (key) {
          var raw = localStorage.getItem(key);
          if (!raw) return;
          try {
            var value = JSON.parse(raw);
            var url = new URL(value, location.origin);
            if (url.host !== location.host) localStorage.removeItem(key);
          } catch (error) {
            localStorage.removeItem(key);
          }
        });
        var info = localStorage.getItem("modelInfo");
        if (info && info.indexOf(location.host) === -1) localStorage.removeItem("modelInfo");
      } catch (error) {}
    </script>
"@
    $index = $index.Replace("</head>", "$snippet2</head>")
    [System.IO.File]::WriteAllText($indexPath, $index, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "patched: saved server URLs for other ports are discarded"
}

# Default background (optional). The official UI stores the selection in
# localStorage["backgroundUrl"]; this only changes the fallback used when there
# is no selection yet, and migrates the old ceiling image.
if ($BackgroundImage) {
    $bgPath = Join-Path $Root "backgrounds\$BackgroundImage"
    if (-not (Test-Path $bgPath)) {
        Write-Warning "backgrounds\$BackgroundImage does not exist; background default left unchanged."
    } else {
        $oldBg = 'ceiling-window-room-night.jpeg'
        if ($text.Contains($oldBg)) {
            $text = $text.Replace($oldBg, $BackgroundImage)
            Write-Host "patched: default background -> $BackgroundImage"
        } else {
            Write-Warning "Default background pattern not found; background default left unchanged."
        }

        $indexPath = Join-Path $frontend "index.html"
        $index = [System.IO.File]::ReadAllText($indexPath)
        if (-not $index.Contains('data-default-background')) {
            $snippet = @"
    <script data-default-background>
      // Migrate the stock background to the show background. A background
      // picked by the operator in the UI is respected.
      try {
        var key = "backgroundUrl";
        var current = localStorage.getItem(key);
        if (!current || current.indexOf("ceiling-window-room-night.jpeg") !== -1) {
          localStorage.setItem(key, JSON.stringify(location.origin + "/bg/$BackgroundImage"));
        }
      } catch (error) {}
    </script>
"@
            $index = $index.Replace("</head>", "$snippet</head>")
            [System.IO.File]::WriteAllText($indexPath, $index, (New-Object System.Text.UTF8Encoding($false)))
            Write-Host "patched: backgroundUrl default in index.html"
        }
    }
}

if ($text -ne $original) {
    [System.IO.File]::WriteAllText($jsFile.FullName, $text, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host ""
    Write-Host "Patched bundle: $($jsFile.Name)"
} else {
    Write-Host "Nothing to patch (already up to date)."
}

Write-Host "Restart/reload the UI: docker compose up -d --force-recreate (or Ctrl+F5)."
