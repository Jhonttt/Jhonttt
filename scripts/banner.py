#!/usr/bin/env python3
"""Banner animado del perfil: un retrato en semitono que se recompone en el
nombre y en los logos del stack.

Cada forma es un semitono estático completo, con todo su detalle, que aparece
y desaparece con la opacidad de su grupo. Por encima, unas cientos de
partículas viajeras hacen el trayecto de una forma a la siguiente; el reparto
entre formas se resuelve como un problema de asignación (Hungarian) para que
ninguna cruce el banner sin necesidad.

Uso, desde la raíz del repositorio:
    python scripts/banner.py

Necesita: pip install -r scripts/requirements.txt
Lee la foto de assets/source/retrato.png y el resto de datos/perfil.json.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from svgelements import Path as TrazadoSVG

from comun import ASSETS, MONO, SANS, TEMAS, datos, esc, guardar, icono

W, H = 1200, 540
# La zona de las partículas, a la izquierda.
ZX, ZY, ZW, ZH = 40, 40, 480, 460

VIAJERAS = 760
DETALLE = 2300          # puntos del retrato estático
SEPARACION_MIN = 7.5    # paso mínimo de la retícula, en píxeles
INTRO = 2.6             # segundos que tardan en llegar al principio
QUIETO = 3.8            # segundos que se queda cada forma
CAMBIO = 1.4            # segundos de viaje entre formas
FUNDIDO = 0.28          # lo que tarda un semitono en aparecer o irse
SEMILLA = 20041
RETRATO = ASSETS / "source" / "retrato.png"
FUENTE = ASSETS / "source" / "Inter.ttf"

NOMBRES_VISIBLES = {"openjdk": "java", "vuedotjs": "vue", "nextdotjs": "next.js", "nodedotjs": "node.js"}


# --- formas ----------------------------------------------------------------

def reticula(paso: float) -> np.ndarray:
    """Centros de una retícula hexagonal que cubre la zona, en coordenadas locales."""
    puntos = []
    fila = 0
    y = paso / 2
    while y < ZH:
        x = paso / 2 + (paso / 2 if fila % 2 else 0)
        while x < ZW:
            puntos.append((x, y))
            x += paso
        y += paso * 0.866
        fila += 1
    return np.array(puntos)


def muestrear(mascara: np.ndarray, paso: float) -> np.ndarray:
    pts = reticula(paso)
    xi = np.clip(pts[:, 0].astype(int), 0, ZW - 1)
    yi = np.clip(pts[:, 1].astype(int), 0, ZH - 1)
    return pts[mascara[yi, xi]]


def paso_para(mascara: np.ndarray, objetivo: int) -> float:
    """El paso de retícula que deja cerca de `objetivo` puntos dentro de la máscara."""
    area = float(mascara.sum())
    return max(SEPARACION_MIN, (area / (0.866 * objetivo)) ** 0.5)


def conectado_al_borde(claro: np.ndarray) -> np.ndarray:
    """Píxeles claros unidos al borde: el fondo de la foto, no los brillos de la cara."""
    alto, ancho = claro.shape
    visto = np.zeros_like(claro)
    cola: deque[tuple[int, int]] = deque()
    for x in range(ancho):
        cola.extend(((0, x), (alto - 1, x)))
    for y in range(alto):
        cola.extend(((y, 0), (y, ancho - 1)))
    while cola:
        y, x = cola.popleft()
        if visto[y, x] or not claro[y, x]:
            continue
        visto[y, x] = True
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < alto and 0 <= nx < ancho:
                cola.append((ny, nx))
    return visto


def lienzo(imagen: Image.Image) -> Image.Image:
    """Encaja una imagen en la zona, centrada, sin deformarla."""
    escala = min(ZW / imagen.width, ZH / imagen.height)
    imagen = imagen.resize((round(imagen.width * escala), round(imagen.height * escala)), Image.LANCZOS)
    fondo = Image.new(imagen.mode, (ZW, ZH), 0 if imagen.mode == "L" else (255, 255, 255))
    fondo.paste(imagen, ((ZW - imagen.width) // 2, ZH - imagen.height))
    return fondo


def forma_retrato(tema: str) -> tuple[np.ndarray, np.ndarray]:
    foto = lienzo(Image.open(RETRATO).convert("RGB"))
    gris = np.asarray(ImageOps.grayscale(foto), dtype=float) / 255
    mascara = ~conectado_al_borde(gris > 0.9)
    # Cierra los huecos del contorno para que el pelo no se deshilache.
    m = Image.fromarray((mascara * 255).astype("uint8")).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(5))
    mascara = np.asarray(m) > 127

    # Contraste estirado solo con los píxeles de la persona.
    dentro = gris[mascara]
    lo, hi = np.percentile(dentro, 2), np.percentile(dentro, 98)
    luz = np.clip((gris - lo) / max(hi - lo, 1e-6), 0, 1)

    paso = paso_para(mascara, DETALLE)
    pts = muestrear(mascara, paso)
    l = luz[pts[:, 1].astype(int), pts[:, 0].astype(int)]
    # En oscuro, puntos de luz sobre negro: lo claro pesa más. En claro, tinta
    # sobre papel: pesa lo oscuro. Un mínimo para que la silueta no se pierda.
    v = l if tema == "dark" else 1 - l
    v = 0.16 + 0.84 * v ** 1.1
    radios = v * paso * 0.56
    return pts, radios


def forma_texto(texto: str) -> tuple[np.ndarray, np.ndarray]:
    lienzo_txt = Image.new("L", (ZW * 2, ZH * 2), 0)
    dibujo = ImageDraw.Draw(lienzo_txt)
    # Fuente incluida en el repositorio: con una del sistema, el workflow
    # (Linux) dibujaría otro banner que el de un Windows o un Mac.
    fuente = ImageFont.truetype(str(FUENTE), 360)
    fuente.set_variation_by_axes([32, 700])
    caja = dibujo.textbbox((0, 0), texto, font=fuente)
    dibujo.text((-caja[0] + 20, -caja[1] + 20), texto, fill=255, font=fuente)
    recorte = lienzo_txt.crop(lienzo_txt.getbbox())
    recorte.thumbnail((ZW - 30, ZH - 30))
    zona = Image.new("L", (ZW, ZH), 0)
    zona.paste(recorte, ((ZW - recorte.width) // 2, (ZH - recorte.height) // 2))
    mascara = np.asarray(zona) > 127
    paso = paso_para(mascara, 1400)
    pts = muestrear(mascara, paso)
    return pts, np.full(len(pts), paso * 0.36)


def forma_icono(slug: str) -> tuple[np.ndarray, np.ndarray]:
    _, d = icono(slug)
    lado = 360
    escala = lado / 24
    capa = np.zeros((ZH, ZW), dtype=bool)
    # Cada subtrazado se rellena aparte y se combinan con XOR: es la regla
    # evenodd, la que hace que los agujeros de los logos sean agujeros.
    for sub in TrazadoSVG(d).as_subpaths():
        sub = TrazadoSVG(sub)
        n = max(32, int(sub.length() * escala / 2))
        puntos = [sub.point(t) for t in np.linspace(0, 1, n)]
        poligono = [((p.x * escala) + (ZW - lado) / 2, (p.y * escala) + (ZH - lado) / 2) for p in puntos]
        img = Image.new("1", (ZW, ZH), 0)
        ImageDraw.Draw(img).polygon(poligono, fill=1)
        capa ^= np.asarray(img, dtype=bool)
    paso = paso_para(capa, 1500)
    pts = muestrear(capa, paso)
    return pts, np.full(len(pts), paso * 0.38)


# --- viajeras --------------------------------------------------------------

def elegir(pts: np.ndarray, radios: np.ndarray, n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """n puntos de una forma para las viajeras; si no hay bastantes, se repiten."""
    idx = rng.choice(len(pts), size=n, replace=len(pts) < n)
    return pts[idx], radios[idx]


def asignar(desde: np.ndarray, hasta: np.ndarray) -> np.ndarray:
    filas, cols = linear_sum_assignment(cdist(desde, hasta, "sqeuclidean"))
    orden = np.empty(len(desde), dtype=int)
    orden[filas] = cols
    return orden


# --- SVG -------------------------------------------------------------------

def f(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".")


def construir(tema: str, perfil: dict) -> str:
    t = TEMAS[tema]
    rng = np.random.default_rng(SEMILLA)

    claves = perfil["transformaciones"]
    formas, colores, rotulos = [], [], []
    for clave in claves:
        if clave == "retrato":
            formas.append(forma_retrato(tema))
            colores.append(t["tinta"])
            rotulos.append("retrato")
        elif clave == "nombre":
            nombre = perfil["nombre"].split()[0]
            formas.append(forma_texto(nombre))
            colores.append(t["tinta"])
            rotulos.append(nombre.lower())
        else:
            formas.append(forma_icono(clave))
            colores.append(t["acento"])
            rotulos.append(NOMBRES_VISIBLES.get(clave, icono(clave)[0].lower()))

    n_formas = len(formas)
    ciclo = n_formas * (QUIETO + CAMBIO)

    # Las viajeras: una posición por forma, encadenadas por asignación.
    posiciones, radios = [], []
    actual = None
    for pts, rad in formas:
        p, r = elegir(pts, rad, VIAJERAS, rng)
        if actual is not None:
            orden = asignar(actual, p)
            p, r = p[orden], r[orden]
        posiciones.append(p)
        radios.append(r)
        actual = p
    # Cierra el ciclo. La vuelta al retrato va al punto libre más cercano, no al
    # de salida, para que el último viaje también sea corto. El salto que eso
    # deja al reiniciar no se ve: ocurre con el retrato estático encendido, y
    # cada viajera descansa sobre un punto idéntico de ese semitono.
    cierre = asignar(posiciones[-1], posiciones[0])
    vuelta_p, vuelta_r = posiciones[0][cierre], radios[0][cierre]

    dispersion = np.column_stack([rng.uniform(-80, ZW + 80, VIAJERAS), rng.uniform(-60, ZH + 60, VIAJERAS)])

    # Tiempos clave del ciclo: quieta, viaja, quieta, viaja… y vuelta a empezar.
    tiempos = [0.0]
    for k in range(n_formas):
        tiempos.append(k * (QUIETO + CAMBIO) + QUIETO)
        tiempos.append((k + 1) * (QUIETO + CAMBIO))
    key_times = ";".join(f"{x / ciclo:.4f}" for x in tiempos)
    key_splines = ";".join(["0 0 1 1", "0.7 0 0.3 1"] * n_formas)

    def valores(lista, fmt, ultimo=None):
        seq = []
        for k in range(n_formas):
            seq += [fmt(lista[k]), fmt(lista[k])]
        seq.append(fmt(lista[0] if ultimo is None else ultimo))
        return ";".join(seq)

    viajeras = []
    for i in range(VIAJERAS):
        trs = valores([posiciones[k][i] for k in range(n_formas)], lambda p: f"{f(p[0])} {f(p[1])}", vuelta_p[i])
        rs = valores([radios[k][i] for k in range(n_formas)], f, vuelta_r[i])
        d0 = dispersion[i]
        p0 = posiciones[0][i]
        viajeras.append(
            f'<circle r="0">'
            f'<animateTransform attributeName="transform" type="translate" dur="{INTRO}s" fill="freeze" '
            f'values="{f(d0[0])} {f(d0[1])};{f(p0[0])} {f(p0[1])}" calcMode="spline" keyTimes="0;1" keySplines="0.2 0.7 0.2 1"/>'
            f'<animate attributeName="r" dur="{INTRO}s" fill="freeze" values="0;{f(radios[0][i])}"/>'
            f'<animateTransform attributeName="transform" type="translate" begin="{INTRO}s" dur="{ciclo}s" '
            f'repeatCount="indefinite" values="{trs}" keyTimes="{key_times}" calcMode="spline" keySplines="{key_splines}"/>'
            f'<animate attributeName="r" begin="{INTRO}s" dur="{ciclo}s" repeatCount="indefinite" '
            f'values="{rs}" keyTimes="{key_times}" calcMode="spline" keySplines="{key_splines}"/>'
            f"</circle>"
        )
    color_viajeras = valores(colores, str)

    # Visibilidad de cada semitono estático (y de su rótulo) a lo largo del ciclo.
    def visibilidad(k: int) -> tuple[str, str]:
        llega = k * (QUIETO + CAMBIO)
        se_va = llega + QUIETO
        if k == 0:
            pts = [(0, 1), (se_va, 1), (se_va + FUNDIDO, 0), (ciclo - FUNDIDO, 0), (ciclo, 1)]
        else:
            pts = [(0, 0), (llega - FUNDIDO, 0), (llega, 1), (se_va, 1), (se_va + FUNDIDO, 0), (ciclo, 0)]
        return ";".join(str(v) for _, v in pts), ";".join(f"{x / ciclo:.4f}" for x, _ in pts)

    estaticos, rotulos_svg, pasos = [], [], []
    ancho_paso = 40
    for k, ((pts, rad), color) in enumerate(zip(formas, colores)):
        vals, kt = visibilidad(k)
        anim = f'<animate attributeName="opacity" begin="{INTRO}s" dur="{ciclo}s" repeatCount="indefinite" values="{vals}" keyTimes="{kt}"/>'
        intro = (
            f'<animate attributeName="opacity" dur="{INTRO}s" fill="freeze" values="0;0;1" keyTimes="0;0.85;1"/>'
            if k == 0 else ""
        )
        puntos = "".join(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}"/>' for (x, y), r in zip(pts, rad))
        estaticos.append(f'<g fill="{color}" opacity="0">{intro}{anim}{puntos}</g>')
        rotulos_svg.append(
            f'<text x="680" y="446" font-family="{MONO}" font-size="19" fill="{t["suave"]}" opacity="0">'
            f'{intro}{anim}<tspan fill="{t["acento"]}">›</tspan> {esc(rotulos[k])}</text>'
        )
        x = 680 + k * (ancho_paso + 6)
        pasos.append(
            f'<rect x="{x}" y="468" width="{ancho_paso}" height="4" rx="2" fill="{t["tenue"]}"/>'
            f'<rect x="{x}" y="468" width="{ancho_paso}" height="4" rx="2" fill="{t["acento"]}" opacity="0">{intro}{anim}</rect>'
        )

    nombre = esc(perfil["nombre"])
    linea = esc(perfil["linea"])
    lugar = esc(perfil["lugar"])
    usuario = esc(perfil["usuario"].lower())

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="titulo desc">
<title id="titulo">{nombre} — {linea}</title>
<desc id="desc">Retrato en semitono que se recompone en el nombre y en los logos de su stack.</desc>
<defs>
<clipPath id="marco"><rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="18"/></clipPath>
<radialGradient id="halo" cx="0.5" cy="0.55" r="0.5"><stop offset="0" stop-color="{t["acento"]}" stop-opacity="0.10"/><stop offset="1" stop-color="{t["acento"]}" stop-opacity="0"/></radialGradient>
<pattern id="reticula" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{t["linea"]}" stroke-width="1" opacity="0.55"/></pattern>
<linearGradient id="desvanecer" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.9"/><stop offset="0.5" stop-color="#fff" stop-opacity="0.25"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<mask id="mascara"><rect width="{W}" height="{H}" fill="url(#desvanecer)"/></mask>
</defs>
<g clip-path="url(#marco)">
<rect width="{W}" height="{H}" fill="{t["fondo"]}"/>
<rect width="{W}" height="{H}" fill="url(#reticula)" mask="url(#mascara)"/>
<ellipse cx="{ZX + ZW / 2}" cy="{ZY + ZH / 2 + 20}" rx="300" ry="280" fill="url(#halo)"/>
<g transform="translate({ZX} {ZY})">
{"".join(estaticos)}
<g fill="{t["tinta"]}"><animate attributeName="fill" begin="{INTRO}s" dur="{ciclo}s" repeatCount="indefinite" values="{color_viajeras}" keyTimes="{key_times}" calcMode="discrete"/>{"".join(viajeras)}</g>
</g>
<line x1="600" y1="64" x2="600" y2="476" stroke="{t["linea"]}"/>
</g>
<text x="680" y="132" font-family="{MONO}" font-size="17" letter-spacing="4" fill="{t["suave"]}">HOLA, SOY</text>
<text x="676" y="206" font-family="{SANS}" font-size="68" font-weight="700" letter-spacing="-2" fill="{t["tinta"]}">{nombre}</text>
<text x="680" y="252" font-family="{SANS}" font-size="28" fill="{t["suave"]}">{linea}</text>
<g font-family="{MONO}" font-size="19" fill="{t["suave"]}">
<text x="680" y="324"><tspan fill="{t["tenue"]}">@</tspan> {usuario}</text>
<text x="680" y="360"><tspan fill="{t["tenue"]}">◎</tspan> {lugar}</text>
</g>
{"".join(rotulos_svg)}
{"".join(pasos)}
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{t["linea"]}"/>
</svg>
"""


def main() -> None:
    perfil = datos()
    guardar("banner", {tema: construir(tema, perfil) for tema in TEMAS})
    for tema in TEMAS:
        tam = (ASSETS / f"banner-{tema}.svg").stat().st_size
        print(f"banner-{tema}.svg  {tam / 1024:.0f} KB")


if __name__ == "__main__":
    main()
