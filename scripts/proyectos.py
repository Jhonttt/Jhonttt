#!/usr/bin/env python3
"""La tarjeta de proyectos, a partir de datos/perfil.json:

- Una cabecera con el número de sección y cuántos proyectos se destacan.
- Una fila por proyecto: nombre, tipo y año a la izquierda; descripción,
  tecnologías y el enlace principal a la derecha. En móvil, todo en una
  columna.

La cabecera y las filas se dibujan como piezas separadas para que cada fila
pueda ser un enlace distinto en el README: un SVG dentro de un <img> no puede
tener enlaces propios. Al compartir el mismo borde y el mismo fondo, se leen
como una sola tarjeta.

El enlace principal es la demo si el proyecto tiene una; si no, el repositorio.

Uso: python scripts/proyectos.py
"""

from __future__ import annotations

from comun import (
    IDIOMAS,
    Lienzo,
    datos,
    enlace_proyecto,
    envolver,
    es_movil,
    f1,
    guardar_versiones,
    medir,
)

X = 28
ANCHO_IZQ = 196          # columna del nombre, en escritorio
X_DER = 252              # dónde empieza la descripción, en escritorio
X_SEP = X_DER - 20       # la línea vertical que separa las dos columnas

TEXTOS = {
    "es": {
        "titulo": "Proyectos",
        "meta": "{n} destacados",
        "demo": "demo",
        "codigo": "código",
    },
    "en": {
        "titulo": "Projects",
        "meta": "{n} featured",
        "demo": "demo",
        "codigo": "code",
    },
}

# Iconos de trazo (16x16) para el enlace principal.
ICONOS = {
    "demo": '<circle cx="8" cy="8" r="6.5"/><path d="M1.5 8h13M8 1.5c1.9 1.9 2.8 4.1 2.8 6.5S9.9 12.6 8 14.5M8 1.5C6.1 3.4 5.2 5.6 5.2 8s.9 4.6 2.8 6.5"/>',
    "codigo": '<path d="m5.5 4.5-3.5 3.5 3.5 3.5M10.5 4.5l3.5 3.5-3.5 3.5"/>',
}


def _borde_cabecera(ancho: float, alto: float) -> str:
    """Borde superior de la tarjeta: esquinas de arriba redondeadas y el resto
    abierto, porque las filas continúan debajo."""
    return (
        f"M0.5 {f1(alto - 0.5)}V12.5A12 12 0 0 1 12.5 0.5"
        f"H{f1(ancho - 12.5)}A12 12 0 0 1 {f1(ancho - 0.5)} 12.5V{f1(alto - 0.5)}"
    )


def _borde_fila(ancho: float, alto: float, ultima: bool) -> str:
    """Borde de una fila: solo los lados y abajo. La última redondea las
    esquinas inferiores; las demás dejan una línea discontinua de separación."""
    if ultima:
        return (
            f"M0.5 0V{f1(alto - 12.5)}A12 12 0 0 0 12.5 {f1(alto - 0.5)}"
            f"H{f1(ancho - 12.5)}A12 12 0 0 0 {f1(ancho - 0.5)} {f1(alto - 12.5)}V0"
        )
    return f"M0.5 0V{f1(alto - 0.5)}M{f1(ancho - 0.5)} 0V{f1(alto - 0.5)}"


def _ancho_chip(nombre: str) -> float:
    return medir(nombre, "mono-pequeno") + 14


def _reparto_chips(tecnologias: list[str], ancho_max: float) -> list[list[str]]:
    filas: list[list[str]] = [[]]
    x = 0.0
    for nombre in tecnologias:
        w = _ancho_chip(nombre)
        if filas[-1] and x + w > ancho_max:
            filas.append([])
            x = 0.0
        filas[-1].append(nombre)
        x += w + 6
    return filas


def _chips(lz: Lienzo, x0: float, y: float, filas: list[list[str]]) -> None:
    t = lz.t
    for fila in filas:
        x = x0
        for nombre in fila:
            w = _ancho_chip(nombre)
            lz.raw(
                f'<rect x="{f1(x)}" y="{f1(y)}" width="{f1(w)}" height="20" rx="5" '
                f'fill="{t["panel"]}" stroke="{t["linea"]}"/>'
            )
            lz.raw(lz.texto(x + 7, y + 14, nombre, "mono-pequeno", "suave"))
            x += w + 6
        y += 26


def _enlace(lz: Lienzo, x: float, y: float, tipo: str, tx: dict) -> None:
    """Icono y etiqueta del enlace principal, alineado a la derecha."""
    t = lz.t
    etiqueta = tx["demo"] if tipo == "demo" else tx["codigo"]
    dibujo = ICONOS["demo" if tipo == "demo" else "codigo"]
    lz.raw(
        f'<g transform="translate({f1(x)} {f1(y - 11)}) scale(0.875)" fill="none" '
        f'stroke="{t["acento"]}" stroke-width="1.5" stroke-linecap="round" '
        f'stroke-linejoin="round">{dibujo}</g>'
    )
    lz.raw(lz.texto(x + 18, y, etiqueta, "mono-pequeno", "acento"))


def cabecera(tema: str, perfil: dict, tx: dict, ancho: float) -> str:
    n = len(perfil["proyectos"])
    desc = f"{tx['titulo']}: " + ", ".join(p["nombre"] for p in perfil["proyectos"]) + "."
    lz = Lienzo(ancho, 56, tema, tx["titulo"], desc)
    t = lz.t
    lz.raw(f'<rect width="{f1(ancho)}" height="56" fill="{t["fondo"]}"/>')
    lz.raw(f'<path d="{_borde_cabecera(ancho, 56)}" fill="none" stroke="{t["linea"]}"/>')
    lz.raw(
        f'<line x1="0.5" y1="55.5" x2="{f1(ancho - 0.5)}" y2="55.5" '
        f'stroke="{t["linea"]}" stroke-dasharray="2 4"/>'
    )
    lz.raw(lz.texto(X, 38, "04", "seccion", "acento"))
    lz.raw(lz.texto(X + medir("04", "seccion") + 12, 38, tx["titulo"], "seccion", "suave", mayus=True))
    lz.raw(lz.texto(ancho - X, 38, tx["meta"].format(n=n), "meta", "suave", anchor="end"))
    return lz.render()


def fila(tema: str, tx: dict, proyecto: dict, indice: int, ancho: float, ultima: bool) -> str:
    movil = es_movil(ancho)
    url, tipo = enlace_proyecto(proyecto)
    etiqueta = tx["demo"] if tipo == "demo" else tx["codigo"]

    if movil:
        x_texto = X
        ancho_texto = ancho - 2 * X
        y_indice, y_titulo = 22, 44
        titulo_lineas = envolver(proyecto["nombre"], "dato", ancho_texto)
        y_meta = y_titulo + (len(titulo_lineas) - 1) * 19 + 20
        y_desc = y_meta + 22
        desc_lineas = envolver(proyecto["descripcion"], "pequeno", ancho_texto)
        y_chips = y_desc + (len(desc_lineas) - 1) * 18 + 14
        filas_chips = _reparto_chips(proyecto["tecnologias"], ancho_texto)
        alto = y_chips + (len(filas_chips) - 1) * 26 + 20 + 18
    else:
        x_texto = X_DER
        ancho_texto = ancho - X - X_DER
        y_indice, y_titulo = 22, 44
        titulo_lineas = envolver(proyecto["nombre"], "dato", ANCHO_IZQ)
        y_meta = y_titulo + (len(titulo_lineas) - 1) * 19 + 20
        y_desc = 44
        desc_lineas = envolver(proyecto["descripcion"], "pequeno", ancho_texto)
        y_chips = y_desc + (len(desc_lineas) - 1) * 18 + 14
        filas_chips = _reparto_chips(proyecto["tecnologias"], ancho_texto)
        alto = max(y_chips + (len(filas_chips) - 1) * 26 + 20, y_meta + 4) + 18

    titulo = f"{proyecto['nombre']} — {etiqueta}"
    desc = (
        f"{proyecto['nombre']}. {proyecto['tipo']}. {proyecto['descripcion']} "
        f"{', '.join(proyecto['tecnologias'])}. {etiqueta}: {url}"
    )
    lz = Lienzo(ancho, alto, tema, titulo, desc)
    t = lz.t

    lz.raw(f'<rect width="{f1(ancho)}" height="{f1(alto)}" fill="{t["fondo"]}"/>')
    lz.raw(f'<path d="{_borde_fila(ancho, alto, ultima)}" fill="none" stroke="{t["linea"]}"/>')
    if not ultima:
        lz.raw(
            f'<line x1="0.5" y1="{f1(alto - 0.5)}" x2="{f1(ancho - 0.5)}" y2="{f1(alto - 0.5)}" '
            f'stroke="{t["linea"]}" stroke-dasharray="2 4"/>'
        )
    if not movil:
        lz.raw(
            f'<line x1="{f1(X_SEP)}" y1="18" x2="{f1(X_SEP)}" y2="{f1(alto - 18)}" '
            f'stroke="{t["linea"]}"/>'
        )

    lz.raw(lz.texto(X, y_indice, f"{indice:02d}", "mono-pequeno", "acento"))
    ancho_etiqueta = 18 + medir(etiqueta, "mono-pequeno")
    _enlace(lz, ancho - X - ancho_etiqueta, y_indice, tipo, tx)

    for i, linea in enumerate(titulo_lineas):
        lz.raw(lz.texto(X, y_titulo + i * 19, linea, "dato", "tinta"))
    lz.raw(lz.texto(X, y_meta, f"{proyecto['tipo']} · {proyecto['periodo']}", "mono-pequeno", "suave", mayus=True))

    for i, linea in enumerate(desc_lineas):
        lz.raw(lz.texto(x_texto, y_desc + i * 18, linea, "pequeno", "tinta"))
    _chips(lz, x_texto, y_chips, filas_chips)
    return lz.render()


def main() -> None:
    for idioma in IDIOMAS:
        perfil = datos(idioma)
        tx = TEXTOS[idioma]
        proyectos = perfil["proyectos"]
        guardar_versiones("proyectos", lambda tema, ancho: cabecera(tema, perfil, tx, ancho), idioma)
        for i, proyecto in enumerate(proyectos):
            guardar_versiones(
                f"proyecto-{i + 1}",
                lambda tema, ancho, p=proyecto, i=i: fila(tema, tx, p, i + 1, ancho, i == len(proyectos) - 1),
                idioma,
            )
        print(f"proyectos ({idioma}): {len(proyectos)}")


if __name__ == "__main__":
    main()
