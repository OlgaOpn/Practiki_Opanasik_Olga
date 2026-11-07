"""Сборка статики (ПР 15): минификация CSS и JS в static/dist/.

    python build_assets.py

Исходники остаются читаемыми (static/css/style.css, static/js/forms.js),
браузер получает сжатые файлы app.min.css и app.min.js.
"""
import gzip
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent / "static"


def minify_css(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)          # комментарии
    css = re.sub(r"\s+", " ", css)                           # переносы и повторные пробелы
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)             # пробелы вокруг { } ; , >
    css = re.sub(r"([{;])\s*([\w-]+)\s*:\s*", r"\1\2:", css)  # пробел после «свойство:»
    css = css.replace(";}", "}")
    return css.strip()


def minify_js(js: str) -> str:
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    lines = []
    for line in js.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        lines.append(line)
    return "\n".join(lines)                                  # переносы строк оставляем — так безопасно для JS


def build() -> dict:
    dist = STATIC / "dist"
    dist.mkdir(exist_ok=True)
    report = {}
    for src, out, fn in [(STATIC / "css" / "style.css", dist / "app.min.css", minify_css),
                         (STATIC / "js" / "forms.js", dist / "app.min.js", minify_js)]:
        text = src.read_text(encoding="utf-8")
        small = fn(text)
        out.write_text(small, encoding="utf-8")
        report[src.name] = dict(source=len(text.encode()), minified=len(small.encode()),
                                source_gzip=len(gzip.compress(text.encode())), minified_gzip=len(gzip.compress(small.encode())))
    return report


if __name__ == "__main__":
    for name, r in build().items():
        print(f"{name}: {r['source']} → {r['minified']} байт ({100 - r['minified'] * 100 // r['source']}% меньше); "
              f"gzip: {r['source_gzip']} → {r['minified_gzip']}")
