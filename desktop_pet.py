import os
import sys
import webview

# Configure WebView2 for true alpha channel transparency
os.environ["WEBVIEW2_DEFAULT_BACKGROUND_COLOR"] = "0"

TRANSPARENT_CSS = """
html, body, #root {
    background: transparent !important;
    background-color: transparent !important;
    overflow: hidden !important;
}
/* Optional: floating control hint */
#root > div {
    background: transparent !important;
}
"""

def on_loaded(window):
    # Inject CSS to guarantee transparency
    window.load_css(TRANSPARENT_CSS)
    print("Desktop Pet overlay initialized with transparent background.")

def main():
    port = 12393
    url = f"http://localhost:{port}/"
    print(f"Connecting Desktop Pet to: {url}")
    
    # Create borderless, transparent, always-on-top window
    window = webview.create_window(
        title="AI Influencer - Desktop Pet",
        url=url,
        transparent=True,
        frameless=True,
        on_top=True,
        width=520,
        height=780,
        x=1350,
        y=200
    )
    
    window.events.loaded += on_loaded
    webview.start(gui="edgechromium", debug=False)

if __name__ == "__main__":
    main()
