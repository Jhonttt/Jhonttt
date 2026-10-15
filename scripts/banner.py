#!/usr/bin/env python3
"""Cabecera del perfil: el nombre a la izquierda y, detrás, un mapa del mundo
hecho de puntos del que sale una onda desde mi ciudad.

El mapa se construye de cero:
  1. Lee las costas de Natural Earth (TopoJSON de world-atlas, 1:110m) y
     decodifica sus arcos.
  2. Los proyecta con Equal Earth (Šavrič, Patterson y Jenny, 2018), la
     proyección de áreas iguales que usan hoy muchos atlas.
  3. Rasteriza la tierra y la muestrea en una retícula: cada celda con tierra
     es un punto.
  4. Cada punto tiene una animación de opacidad que empieza con un retraso
     proporcional a su distancia a la ciudad: eso es la onda. Todos comparten
     los mismos valores; solo cambia cuándo empiezan.

En móvil (ANCHO_MOVIL) el mapa ocupa la parte de arriba y el texto va debajo,
en vez de a su izquierda.

Uso: python scripts/banner.py
"""

from __future__ import annotations

import json
import math

import numpy as np
from PIL import Image, ImageDraw

from comun import ANCHO, ANCHO_MOVIL, FUENTES, TEMAS, Lienzo, datos, envolver, f1, guardar

PASO = 8.0            # separación de la retícula de puntos, en px
RADIO = 1.55          # radio de cada punto
LAT_MIN = -58         # fuera la Antártida

# La composición de cada versión: tamaño, escala del mapa (px por unidad de
# Equal Earth; el mundo mide ~5.4 x 2.6), dónde cae la ciudad y dónde empieza
# el texto. El alto de la de móvil depende de cuántas líneas ocupe el texto.
ESCRITORIO = {"ancho": ANCHO, "alto": 380, "escala": 172.0, "ciudad": (652, 150), "texto": (40, 118)}
MOVIL = {"ancho": ANCHO_MOVIL, "escala": 120.0, "ciudad": (262, 96), "texto": (28, 236)}

ONDA_PERIODO = 5.2    # s entre una onda y la siguiente
ONDA_VELOCIDAD = 165  # px/s
ONDA_ALCANCE = 640    # px a los que la onda ya se ha apagado

# Iconos de trazo (16x16) para las líneas de datos del banner.
ICONOS = {
    "lugar": '<path d="M8 14.5s5-4.3 5-8.5a5 5 0 0 0-10 0c0 4.2 5 8.5 5 8.5Z"/><circle cx="8" cy="6" r="1.8"/>',
    "estudios": '<path d="M1.5 6 8 3l6.5 3L8 9 1.5 6Z"/><path d="M4.5 7.5v3.2c0 .9 1.6 1.8 3.5 1.8s3.5-.9 3.5-1.8V7.5M14.5 6v4"/>',
    "trabajo": '<rect x="1.8" y="4.5" width="12.4" height="9" rx="1.6"/><path d="M5.5 4.5V3.2c0-.7.6-1.2 1.2-1.2h2.6c.7 0 1.2.5 1.2 1.2v1.3M1.8 8.5h12.4"/>',
    "idiomas": '<circle cx="8" cy="8" r="6.5"/><path d="M1.5 8h13M8 1.5c1.9 1.9 2.8 4.1 2.8 6.5S9.9 12.6 8 14.5M8 1.5C6.1 3.4 5.2 5.6 5.2 8s.9 4.6 2.8 6.5"/>',
    "codigo": '<path d="m5.5 4.5-3.5 3.5 3.5 3.5M10.5 4.5l3.5 3.5-3.5 3.5"/>',
}


# --- Equal Earth -----------------------------------------------------------

A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
M = math.sqrt(3) / 2


def equal_earth(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Proyección Equal Earth. Grados de entrada; unidades de la proyección a la salida."""
    lam = np.radians(lon)
    phi = np.radians(lat)
    th = np.arcsin(M * np.sin(phi))
    th2 = th * th
    th6 = th2 * th2 * th2
    x = lam * np.cos(th) / (M * (A1 + 3 * A2 * th2 + th6 * (7 * A3 + 9 * A4 * th2)))
    y = th * (A1 + A2 * th2 + th6 * (A3 + A4 * th2))
    return x, y


# --- TopoJSON --------------------------------------------------------------

def anillos_de_tierra() -> list[list[np.ndarray]]:
    """Polígonos de tierra como listas de anillos (lon, lat). El primero es el exterior."""
    topo = json.loads((FUENTES / "land-110m.json").read_text(encoding="utf-8"))
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcos = []
    for arco in topo["arcs"]:
        q = np.cumsum(np.array(arco, dtype=float), axis=0)
        arcos.append(np.column_stack([q[:, 0] * sx + tx, q[:, 1] * sy + ty]))

    def anillo(indices: list[int]) -> np.ndarray:
        trozos = []
        for k, i in enumerate(indices):
            a = arcos[i] if i >= 0 else arcos[~i][::-1]
            trozos.append(a if k == 0 else a[1:])
        return np.vstack(trozos)

    poligonos = []
    for geom in topo["objects"]["land"]["geometries"]:
        partes = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]]
        for poligono in partes:
            anillos = [anillo(r) for r in poligono]
            if anillos[0][:, 1].max() < LAT_MIN:
                continue
            poligonos.append(anillos)
    return poligonos


def puntos_del_mapa(perfil: dict, geo: dict) -> np.ndarray:
    """Centros de los puntos de tierra en coordenadas del banner."""
    lugar = perfil["ubicacion"]
    cx, cy = equal_earth(np.array([lugar["lon"]]), np.array([lugar["lat"]]))
    ANCHO, ALTO = geo["ancho"], geo["alto"]
    (CIUDAD_X, CIUDAD_Y), ESCALA_MAPA = geo["ciudad"], geo["escala"]

    def a_banner(x, y):
        # Del espacio de la proyección al del banner: la ciudad cae en (CIUDAD_X, CIUDAD_Y).
        return CIUDAD_X + (x - cx[0]) * ESCALA_MAPA, CIUDAD_Y - (y - cy[0]) * ESCALA_MAPA

    sobre = 4  # sobremuestreo del rasterizado
    lienzo = Image.new("L", (int(ANCHO * sobre), int(ALTO * sobre)), 0)
    dibujo = ImageDraw.Draw(lienzo)
    for anillos in anillos_de_tierra():
        for k, r in enumerate(anillos):
            x, y = equal_earth(r[:, 0], r[:, 1])
            bx, by = a_banner(x, y)
            dibujo.polygon(list(zip(bx * sobre, by * sobre)), fill=0 if k else 255)
    tierra = np.asarray(lienzo) > 0

    puntos = []
    lado = int(PASO * sobre)
    for y in np.arange(PASO / 2, ALTO, PASO):
        for x in np.arange(PASO / 2, ANCHO, PASO):
            # Una celda es tierra si lo es una parte razonable de ella, no solo su centro.
            x0, y0 = int((x - PASO / 2) * sobre), int((y - PASO / 2) * sobre)
            celda = tierra[y0:y0 + lado, x0:x0 + lado]
            if celda.size and celda.mean() > 0.22:
                puntos.append((x, y))
    return np.array(puntos)


# --- SVG -------------------------------------------------------------------

def alto_movil(perfil: dict) -> float:
    """El alto de la versión de móvil: lo que ocupe el texto bajo el mapa."""
    x0, y0 = MOVIL["texto"]
    lineas = envolver(perfil["titular"], "titular", MOVIL["ancho"] - 2 * x0)
    return y0 + 88 + len(lineas) * 26 + 18 + len(perfil["banner"]) * 26 + 10


def construir(tema: str, perfil: dict, puntos: np.ndarray, geo: dict) -> str:
    t = TEMAS[tema]
    ANCHO, ALTO = geo["ancho"], geo["alto"]
    movil = ANCHO < ESCRITORIO["ancho"]
    lz = Lienzo(ANCHO, ALTO, tema, f"{perfil['nombre']} — {perfil['titular']}",
                f"{perfil['nombre']}. {perfil['titular']}. {perfil['ubicacion']['texto']}.")
    ccx, ccy = geo["ciudad"]
    # El mapa se apaga donde va el texto, para que respire: en escritorio hacia
    # la izquierda y en móvil hacia abajo.
    if movil:
        fundido = (
            '<linearGradient id="fundido" x1="0" x2="0" y1="0" y2="1">'
            '<stop offset="0" stop-color="#fff" stop-opacity="1"/>'
            '<stop offset="0.3" stop-color="#fff" stop-opacity="1"/>'
            '<stop offset="0.52" stop-color="#fff" stop-opacity="0.16"/>'
            '<stop offset="1" stop-color="#fff" stop-opacity="0.06"/></linearGradient>'
        )
    else:
        fundido = (
            '<linearGradient id="fundido" x1="0" x2="1" y1="0" y2="0">'
            '<stop offset="0" stop-color="#fff" stop-opacity="0.14"/>'
            '<stop offset="0.38" stop-color="#fff" stop-opacity="0.3"/>'
            '<stop offset="0.62" stop-color="#fff" stop-opacity="1"/>'
            '<stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>'
        )

    lz.defs_raw(
        f'<clipPath id="marco"><rect x="0.5" y="0.5" width="{ANCHO - 1}" height="{ALTO - 1}" rx="12"/></clipPath>'
        f"{fundido}"
        '<linearGradient id="fundido-v" x1="0" x2="0" y1="0" y2="1">'
        '<stop offset="0" stop-color="#000" stop-opacity="0.85"/><stop offset="0.16" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="0.84" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.85"/></linearGradient>'
        f'<mask id="mascara"><rect width="{ANCHO}" height="{ALTO}" fill="url(#fundido)"/>'
        f'<rect width="{ANCHO}" height="{ALTO}" fill="url(#fundido-v)"/></mask>'
        f'<radialGradient id="halo" cx="{ccx / ANCHO:.3f}" cy="{ccy / ALTO:.3f}" r="{0.6 if movil else 0.42}">'
        f'<stop offset="0" stop-color="{t["acento"]}" stop-opacity="0.16"/>'
        f'<stop offset="1" stop-color="{t["acento"]}" stop-opacity="0"/></radialGradient>'
    )

    lz.raw('<g clip-path="url(#marco)">')
    lz.raw(f'<rect width="{ANCHO}" height="{ALTO}" fill="{t["fondo"]}"/>')
    lz.raw(f'<rect width="{ANCHO}" height="{ALTO}" fill="url(#halo)"/>')

    # Capa base: todos los puntos, quietos, algo más encendidos cuanto más cerca
    # de la ciudad (un foco suave que no depende de la animación).
    base = "".join(
        f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{RADIO}" fill-opacity="'
        f'{0.55 + 0.45 * max(0.0, 1 - math.hypot(x - ccx, y - ccy) / 520):.2f}"/>'
        for x, y in puntos
    )
    lz.raw(f'<g mask="url(#mascara)"><g fill="{t["mapa"]}">{base}</g>')

    # Capa de la onda: los mismos puntos en el color de acento, encendiéndose al
    # paso de la onda. Solo los que la onda alcanza.
    onda = []
    for x, y in puntos:
        d = math.hypot(x - ccx, y - ccy)
        fuerza = max(0.0, 1 - d / ONDA_ALCANCE) ** 1.15
        if fuerza < 0.04:
            continue
        inicio = d / ONDA_VELOCIDAD - 0.1 * ONDA_PERIODO
        onda.append(
            f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{RADIO}" opacity="0">'
            f'<animate attributeName="opacity" values="0;{fuerza:.2f};0" keyTimes="0;0.1;0.42" '
            f'dur="{ONDA_PERIODO}s" begin="{inicio:.2f}s" repeatCount="indefinite"/></circle>'
        )
    lz.raw(f'<g fill="{t["acento"]}">{"".join(onda)}</g></g>')

    # La ciudad: un punto fijo y dos anillos que se expanden.
    for k in range(2):
        empieza = f"{k * ONDA_PERIODO / 4}s"
        lz.raw(
            f'<circle cx="{ccx}" cy="{ccy}" r="4" fill="none" stroke="{t["acento"]}" stroke-width="1.2" opacity="0">'
            f'<animate attributeName="r" values="4;22" dur="{ONDA_PERIODO / 2}s" begin="{empieza}" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.75;0" dur="{ONDA_PERIODO / 2}s" begin="{empieza}" repeatCount="indefinite"/>'
            f"</circle>"
        )
    lz.raw(f'<circle cx="{ccx}" cy="{ccy}" r="5.5" fill="{t["fondo"]}"/>')
    lz.raw(f'<circle cx="{ccx}" cy="{ccy}" r="3.4" fill="{t["acento"]}"/>')
    lx, ly = ccx + 16, ccy - 14
    lz.raw(f'<path d="M{ccx + 4} {ccy - 4}L{lx - 3} {ly + 4}" stroke="{t["suave"]}" stroke-width="1" opacity="0.6"/>')
    lz.raw(lz.texto(lx, ly, perfil["ubicacion"]["ciudad"], "meta", "tinta", mayus=True))
    lz.raw("</g>")

    # El texto.
    x0, y0 = geo["texto"]
    lz.raw(lz.texto(x0, y0, perfil["saludo"], "seccion", "acento", mayus=True))
    lz.raw(lz.texto(x0 - 2, y0 + 54, perfil["nombre"], "nombre", "tinta"))
    y = y0 + 88
    for linea in envolver(perfil["titular"], "titular", ANCHO - 2 * x0 if movil else 360):
        lz.raw(lz.texto(x0, y, linea, "titular", "suave"))
        y += 26
    y += 18
    for clave, texto in perfil["banner"]:
        lz.raw(f'<g transform="translate({x0} {y - 12})" fill="none" stroke="{t["suave"]}" stroke-width="1.3" '
               f'stroke-linecap="round" stroke-linejoin="round">{ICONOS[clave]}</g>')
        lz.raw(lz.texto(x0 + 26, y, texto, "pequeno", "tinta"))
        y += 26

    lz.raw(f'<rect x="0.5" y="0.5" width="{ANCHO - 1}" height="{ALTO - 1}" rx="12" fill="none" stroke="{t["linea"]}"/>')
    return lz.render()


def main() -> None:
    perfil = datos()
    for nombre, geo in (("banner", ESCRITORIO), ("banner-movil", {**MOVIL, "alto": alto_movil(perfil)})):
        puntos = puntos_del_mapa(perfil, geo)
        guardar(nombre, {tema: construir(tema, perfil, puntos, geo) for tema in TEMAS})
        print(f"{nombre}: {len(puntos)} puntos de tierra")


if __name__ == "__main__":
    main()
