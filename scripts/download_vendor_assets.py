import os
import sys
import urllib.request

ASSETS = [
    # Tailwind CSS Play CDN
    (
        "https://cdn.tailwindcss.com/3.4.1",  # バージョン固定のPlay CDNスクリプト
        "web/vendor/tailwind/tailwindcss.js"
    ),
    # FontAwesome CSS
    (
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
        "web/vendor/fontawesome/css/all.min.css"
    ),
    # FontAwesome Webfonts
    (
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2",
        "web/vendor/fontawesome/webfonts/fa-solid-900.woff2"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.ttf",
        "web/vendor/fontawesome/webfonts/fa-solid-900.ttf"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.woff2",
        "web/vendor/fontawesome/webfonts/fa-regular-400.woff2"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.ttf",
        "web/vendor/fontawesome/webfonts/fa-regular-400.ttf"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2",
        "web/vendor/fontawesome/webfonts/fa-brands-400.woff2"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.ttf",
        "web/vendor/fontawesome/webfonts/fa-brands-400.ttf"
    ),
    # Prism.js core & theme
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css",
        "web/vendor/prism/themes/prism-tomorrow.min.css"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js",
        "web/vendor/prism/prism.min.js"
    ),
    # Prism.js components
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-clike.min.js",
        "web/vendor/prism/components/prism-clike.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js",
        "web/vendor/prism/components/prism-python.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-javascript.min.js",
        "web/vendor/prism/components/prism-javascript.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-typescript.min.js",
        "web/vendor/prism/components/prism-typescript.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-c.min.js",
        "web/vendor/prism/components/prism-c.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-cpp.min.js",
        "web/vendor/prism/components/prism-cpp.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-csharp.min.js",
        "web/vendor/prism/components/prism-csharp.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-java.min.js",
        "web/vendor/prism/components/prism-java.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-go.min.js",
        "web/vendor/prism/components/prism-go.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-rust.min.js",
        "web/vendor/prism/components/prism-rust.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-php.min.js",
        "web/vendor/prism/components/prism-php.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-ruby.min.js",
        "web/vendor/prism/components/prism-ruby.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js",
        "web/vendor/prism/components/prism-bash.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-powershell.min.js",
        "web/vendor/prism/components/prism-powershell.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-sql.min.js",
        "web/vendor/prism/components/prism-sql.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-markup.min.js",
        "web/vendor/prism/components/prism-markup.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js",
        "web/vendor/prism/components/prism-json.min.js"
    ),
    (
        "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-yaml.min.js",
        "web/vendor/prism/components/prism-yaml.min.js"
    ),
    # Marked.js (Markdown parser)
    (
        "https://cdn.jsdelivr.net/npm/marked@12.0.0/marked.min.js",
        "web/vendor/marked/marked.min.js"
    ),
    # DOMPurify (HTML Sanitizer)
    (
        "https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js",
        "web/vendor/dompurify/purify.min.js"
    )
]

def download_assets():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    print(f"Vendor assets download starting ({len(ASSETS)} items)...")
    for url, rel_path in ASSETS:
        dest_path = os.path.join(base_dir, rel_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        print(f"Downloading: {url} -> {rel_path}")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(dest_path, "wb") as f:
            f.write(data)
        print(f"  OK ({len(data):,} bytes)")

    print("\nAll vendor assets downloaded successfully!")

if __name__ == "__main__":
    download_assets()
