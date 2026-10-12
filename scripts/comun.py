"""Piezas compartidas por todos los generadores del perfil.

Solo biblioteca estándar: lo importan también los scripts que corren en el
workflow diario, que no instala nada.
"""

from __future__ import annotations

import json
import re
import urllib.request
from html import escape
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ASSETS = RAIZ / "assets"
CACHE_ICONOS = ASSETS / "source" / "iconos"
DATOS = RAIZ / "datos" / "perfil.json"

# Versión fijada de simple-icons: los trazados no cambian entre ejecuciones.
SIMPLE_ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/{}.svg"

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# Una sola paleta, en dos temas. El fondo oscuro es el de GitHub para que las
# tarjetas se fundan con la página en vez de flotar encima.
TEMAS: dict[str, dict[str, str]] = {
    "dark": {
        "fondo": "#0d1117",
        "panel": "#10151c",
        "linea": "#262c36",
        "tinta": "#e6edf3",
        "suave": "#8b949e",
        "tenue": "#3d444d",
        "acento": "#6ea8fe",
        "acento2": "#a5c8ff",
        # Escala del calendario de actividad, de vacío a máximo.
        "escala": "#161b22,#1b2a44,#24427a,#3a6cc4,#6ea8fe",
    },
    "light": {
        "fondo": "#ffffff",
        "panel": "#f6f8fa",
        "linea": "#d8dee4",
        "tinta": "#1f2328",
        "suave": "#59636e",
        "tenue": "#c8d1da",
        "acento": "#0969da",
        "acento2": "#54aeff",
        "escala": "#eff2f5,#cfe2ff,#8cbcff,#3d8bfd,#0969da",
    },
}


def datos() -> dict:
    return json.loads(DATOS.read_text(encoding="utf-8"))


def esc(texto: str) -> str:
    return escape(str(texto), quote=True)


def icono(slug: str) -> tuple[str, str]:
    """Devuelve (título, trazado) de un icono de simple-icons, con caché en disco."""
    CACHE_ICONOS.mkdir(parents=True, exist_ok=True)
    fichero = CACHE_ICONOS / f"{slug}.svg"
    if not fichero.exists():
        with urllib.request.urlopen(SIMPLE_ICONS.format(slug), timeout=20) as r:
            fichero.write_bytes(r.read())
    svg = fichero.read_text(encoding="utf-8")
    titulo = re.search(r"<title>(.*?)</title>", svg)
    trazado = re.search(r'<path d="([^"]+)"', svg)
    if not trazado:
        raise ValueError(f"el icono {slug} no tiene trazado")
    return (titulo.group(1) if titulo else slug), trazado.group(1)


def guardar(nombre: str, svg_por_tema: dict[str, str]) -> None:
    """Escribe assets/<nombre>-dark.svg y assets/<nombre>-light.svg."""
    ASSETS.mkdir(parents=True, exist_ok=True)
    for tema, svg in svg_por_tema.items():
        (ASSETS / f"{nombre}-{tema}.svg").write_text(svg, encoding="utf-8", newline="\n")


def ancho_texto(texto: str, tam: float, mono: bool = False) -> float:
    """Ancho aproximado de un texto. SVG no mide, así que se estima."""
    if mono:
        return len(texto) * tam * 0.6
    estrechas = sum(c in "ijlrtf.,:;·'|! " for c in texto)
    anchas = sum(c in "mwMW" for c in texto)
    mayus = sum(c.isupper() for c in texto)
    normales = len(texto) - estrechas - anchas
    return tam * (normales * 0.54 + estrechas * 0.3 + anchas * 0.82 + mayus * 0.1)


def marco(t: dict[str, str], ancho: int, alto: int, indice: str, titulo: str, meta: str, cuerpo: str, desc: str = "") -> str:
    """El marco común de las tarjetas: número de sección, título y un dato a la derecha."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" role="img" aria-labelledby="titulo desc">
<title id="titulo">{esc(titulo)}</title>
<desc id="desc">{esc(desc or titulo)}</desc>
<rect x="0.5" y="0.5" width="{ancho - 1}" height="{alto - 1}" rx="14" fill="{t["fondo"]}" stroke="{t["linea"]}"/>
<text x="36" y="54" font-family="{MONO}" font-size="17" fill="{t["acento"]}">{esc(indice)}</text>
<text x="74" y="54" font-family="{SANS}" font-size="20" font-weight="600" fill="{t["tinta"]}">{esc(titulo)}</text>
<text x="{ancho - 36}" y="54" text-anchor="end" font-family="{MONO}" font-size="16" fill="{t["suave"]}">{esc(meta)}</text>
<line x1="36" y1="80" x2="{ancho - 36}" y2="80" stroke="{t["linea"]}"/>
{cuerpo}
</svg>
"""
