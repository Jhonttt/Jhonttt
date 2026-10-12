"""Piezas compartidas por todos los generadores del perfil.

- La paleta, en dos temas.
- La tipografía: Inter y JetBrains Mono van INCRUSTADAS en cada SVG, recortadas
  a los caracteres que ese SVG usa (unos pocos KB). Así el texto se ve igual en
  todas partes y, sobre todo, se puede MEDIR: los saltos de línea y las
  alineaciones se calculan con las métricas reales de la fuente, no a ojo.
- `Lienzo`, que monta un SVG y apunta qué caracteres usa cada fuente.
"""

from __future__ import annotations

import base64
import io
import json
import re
import urllib.request
from functools import lru_cache
from html import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

RAIZ = Path(__file__).resolve().parents[1]
ASSETS = RAIZ / "assets"
FUENTES = ASSETS / "source"
CACHE_ICONOS = FUENTES / "iconos"
DATOS = RAIZ / "datos" / "perfil.json"

# Ancho de diseño de todas las piezas: el que ocupa la columna del README en
# escritorio, para que se vean a tamaño real y no reescaladas.
ANCHO = 860

SIMPLE_ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/{}.svg"

TEMAS: dict[str, dict[str, str]] = {
    "dark": {
        "fondo": "#0d1117",
        "panel": "#11161d",
        "linea": "#262c36",
        "rejilla": "#1a2029",
        "tinta": "#e6edf3",
        "suave": "#9198a1",
        "tenue": "#3d444d",
        "acento": "#7c9dff",
        "acento2": "#a78bfa",
        "mapa": "#384252",
        # Escala de la actividad, de vacío a máximo.
        "escala": "#161b22,#1f2c4d,#2c4386,#4a6bd0,#7c9dff",
    },
    "light": {
        "fondo": "#ffffff",
        "panel": "#f6f8fa",
        "linea": "#e1e4e8",
        "rejilla": "#eef1f4",
        "tinta": "#1f2328",
        "suave": "#59636e",
        "tenue": "#c4cbd3",
        "acento": "#3b5bdb",
        "acento2": "#7048e8",
        "mapa": "#c5cdd7",
        "escala": "#eef1f5,#d2dcfb,#a3b8f6,#6c8eee,#3b5bdb",
    },
}

# --- tipografía ------------------------------------------------------------

# Marca de tiempo fija para las fuentes recortadas (segundos desde 1904, el
# origen de las fechas de OpenType): 2026-01-01.
FECHA_FIJA = 3850070400

# clave -> (fichero, ejes de la fuente variable, familia CSS, peso CSS)
_FUENTES = {
    "sans400": ("Inter.ttf", {"wght": 400, "opsz": 14}, "JA Sans", 400),
    "sans500": ("Inter.ttf", {"wght": 500, "opsz": 14}, "JA Sans", 500),
    "sans600": ("Inter.ttf", {"wght": 600, "opsz": 14}, "JA Sans", 600),
    "display": ("Inter.ttf", {"wght": 650, "opsz": 32}, "JA Display", 650),
    "mono400": ("JetBrainsMono.ttf", {"wght": 400}, "JA Mono", 400),
    "mono500": ("JetBrainsMono.ttf", {"wght": 500}, "JA Mono", 500),
}

_PILA = {
    "JA Sans": "'JA Sans', -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif",
    "JA Display": "'JA Display', 'JA Sans', -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif",
    "JA Mono": "'JA Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
}

# Estilos de texto: nombre -> (fuente, tamaño, espaciado entre letras en em).
ESTILOS = {
    "nombre": ("display", 52, -0.025),
    "titular": ("sans400", 19, -0.005),
    "seccion": ("mono500", 11, 0.12),
    "meta": ("mono400", 11, 0.04),
    "etiqueta": ("mono400", 12, 0.02),
    "cuerpo": ("sans400", 15, -0.003),
    "cuerpo-fuerte": ("sans500", 15, -0.003),
    "dato": ("sans600", 15, -0.005),
    "cifra": ("display", 30, -0.02),
    "cifra-pequena": ("sans600", 20, -0.01),
    "pequeno": ("sans400", 13, 0),
    "pequeno-fuerte": ("sans500", 13, 0),
    "mono-pequeno": ("mono400", 10.5, 0.03),
}


@lru_cache(maxsize=None)
def _fuente_bytes(clave: str) -> bytes:
    """La instancia estática de la fuente variable, serializada (instanciar es lento)."""
    fichero, ejes, _, _ = _FUENTES[clave]
    f = instancer.instantiateVariableFont(TTFont(FUENTES / fichero, recalcTimestamp=False), ejes)
    # Sin esto, fontTools graba la hora de cada guardado dentro de la fuente y
    # cada ejecución daría SVG distintos: un commit diario de todo para nada.
    f.recalcTimestamp = False
    f["head"].modified = FECHA_FIJA
    buf = io.BytesIO()
    f.save(buf)
    return buf.getvalue()


@lru_cache(maxsize=None)
def _metricas(clave: str) -> tuple[dict[int, int], int]:
    f = TTFont(io.BytesIO(_fuente_bytes(clave)))
    cmap = f.getBestCmap()
    hmtx = f["hmtx"].metrics
    anchos = {cp: hmtx[nombre][0] for cp, nombre in cmap.items()}
    return anchos, f["head"].unitsPerEm


def medir(texto: str, estilo: str) -> float:
    """Ancho exacto de un texto en píxeles, con las métricas de la fuente incrustada."""
    clave, tam, espaciado = ESTILOS[estilo]
    anchos, em = _metricas(clave)
    respaldo = anchos.get(ord("n"), em // 2)
    unidades = sum(anchos.get(ord(c), respaldo) for c in texto)
    return unidades / em * tam + espaciado * tam * max(len(texto) - 1, 0)


def envolver(texto: str, estilo: str, ancho_max: float) -> list[str]:
    """Parte un texto en líneas que caben en `ancho_max`, sin cortar palabras."""
    lineas: list[str] = []
    for parrafo in texto.split("\n"):
        actual = ""
        for palabra in parrafo.split():
            prueba = f"{actual} {palabra}".strip()
            if actual and medir(prueba, estilo) > ancho_max:
                lineas.append(actual)
                actual = palabra
            else:
                actual = prueba
        lineas.append(actual)
    return lineas


@lru_cache(maxsize=None)
def _subconjunto(clave: str, caracteres: str) -> str:
    """La fuente `clave` recortada a `caracteres`, en WOFF2 y base64."""
    f = TTFont(io.BytesIO(_fuente_bytes(clave)), recalcTimestamp=False)
    opciones = subset.Options()
    opciones.flavor = "woff2"
    opciones.layout_features = ["kern", "liga", "calt", "tnum", "case"]
    opciones.name_IDs = []
    opciones.notdef_outline = True
    recorte = subset.Subsetter(opciones)
    recorte.populate(text=caracteres + " ")
    recorte.subset(f)
    salida = io.BytesIO()
    f.flavor = "woff2"
    f.save(salida)
    return base64.b64encode(salida.getvalue()).decode()


# --- utilidades ------------------------------------------------------------

def datos() -> dict:
    return json.loads(DATOS.read_text(encoding="utf-8"))


def esc(texto) -> str:
    return escape(str(texto), quote=True)


def f1(x: float) -> str:
    """Número con un decimal como mucho y sin ceros de sobra."""
    return f"{x:.1f}".rstrip("0").rstrip(".")


def icono(slug: str) -> tuple[str, str]:
    """(título, trazado) de un icono de simple-icons, con caché en disco."""
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


# --- el lienzo -------------------------------------------------------------

class Lienzo:
    """Monta un SVG y lleva la cuenta de qué caracteres usa cada fuente."""

    def __init__(self, ancho: float, alto: float, tema: str, titulo: str, desc: str = ""):
        self.ancho, self.alto = ancho, alto
        self.tema = tema
        self.t = TEMAS[tema]
        self.titulo, self.desc = titulo, desc
        self.partes: list[str] = []
        self.defs: list[str] = []
        self.css: list[str] = []
        self._usados: dict[str, set[str]] = {}
        self._estilos: set[str] = set()

    def raw(self, svg: str) -> None:
        self.partes.append(svg)

    def defs_raw(self, svg: str) -> None:
        self.defs.append(svg)

    def color(self, clave: str) -> str:
        return self.t.get(clave, clave)

    def texto(self, x: float, y: float, contenido: str, estilo: str, color: str = "tinta",
              anchor: str = "start", extra: str = "", mayus: bool = False) -> str:
        """Devuelve (y apunta) un <text>. `color` es una clave del tema o un color."""
        if mayus:
            contenido = contenido.upper()
        self._apuntar(estilo, contenido)
        ancla = "" if anchor == "start" else f' text-anchor="{anchor}"'
        return (f'<text x="{f1(x)}" y="{f1(y)}" class="{estilo}" fill="{self.color(color)}"{ancla}{extra}>'
                f"{esc(contenido)}</text>")

    def tspan(self, contenido: str, estilo: str, color: str = "tinta", extra: str = "") -> str:
        self._apuntar(estilo, contenido)
        return f'<tspan class="{estilo}" fill="{self.color(color)}"{extra}>{esc(contenido)}</tspan>'

    def apuntar(self, estilo: str, contenido: str) -> None:
        """Para texto montado a mano (con tspans): que su fuente lo incluya."""
        self._apuntar(estilo, contenido)

    def _apuntar(self, estilo: str, contenido: str) -> None:
        clave = ESTILOS[estilo][0]
        self._usados.setdefault(clave, set()).update(contenido)
        self._estilos.add(estilo)

    def _css_fuentes(self) -> str:
        reglas = []
        for clave, chars in sorted(self._usados.items()):
            _, _, familia, peso = _FUENTES[clave]
            datos_fuente = _subconjunto(clave, "".join(sorted(chars)))
            reglas.append(
                f"@font-face{{font-family:'{familia}';font-weight:{peso};"
                f"src:url(data:font/woff2;base64,{datos_fuente}) format('woff2')}}"
            )
        for estilo in sorted(self._estilos):
            clave, tam, espaciado = ESTILOS[estilo]
            _, _, familia, peso = _FUENTES[clave]
            reglas.append(
                f".{estilo}{{font-family:{_PILA[familia]};font-weight:{peso};font-size:{f1(tam)}px;"
                f"letter-spacing:{espaciado}em;font-kerning:normal}}"
            )
        return "".join(reglas)

    def render(self) -> str:
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{f1(self.ancho)}" height="{f1(self.alto)}" '
            f'viewBox="0 0 {f1(self.ancho)} {f1(self.alto)}" role="img" aria-labelledby="titulo desc">'
            f'<title id="titulo">{esc(self.titulo)}</title><desc id="desc">{esc(self.desc or self.titulo)}</desc>'
            f"<style>{self._css_fuentes()}{''.join(self.css)}</style>"
            f"{defs}{''.join(self.partes)}</svg>\n"
        )


def tarjeta(lienzo: Lienzo, indice: str, titulo: str, meta: str = "") -> float:
    """Fondo, borde y cabecera comunes de una tarjeta. Devuelve la y donde empieza el contenido."""
    t = lienzo.t
    lienzo.raw(
        f'<rect x="0.5" y="0.5" width="{f1(lienzo.ancho - 1)}" height="{f1(lienzo.alto - 1)}" rx="12" '
        f'fill="{t["fondo"]}" stroke="{t["linea"]}"/>'
    )
    lienzo.raw(lienzo.texto(28, 38, indice, "seccion", "acento"))
    lienzo.raw(lienzo.texto(28 + medir(indice, "seccion") + 12, 38, titulo, "seccion", "suave", mayus=True))
    if meta:
        lienzo.raw(lienzo.texto(lienzo.ancho - 28, 38, meta, "meta", "suave", anchor="end"))
    lienzo.raw(f'<line x1="28" y1="56.5" x2="{f1(lienzo.ancho - 28)}" y2="56.5" stroke="{t["linea"]}"/>')
    return 56
