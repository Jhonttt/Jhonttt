#!/usr/bin/env python3
"""La tarjeta de proyectos, en formato compacto, desde datos/perfil.json:

- Una cabecera con el número de sección y cuántos proyectos se destacan.
- Una fila por proyecto, de una sola línea en escritorio: número, nombre, tipo,
  tecnologías y el enlace principal. En móvil, el nombre arriba y el tipo con
  las tecnologías debajo.

La descripción larga no se dibuja para que la tarjeta ocupe poco; sigue en el
texto alternativo de cada imagen, para lectores de pantalla y buscadores.

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
    es_movil,
    f1,
    guardar_versiones,
    medir,
)

X = 28                    # margen lateral
ALTO_CABECERA = 56
ALTO_FILA = 44            # una línea, en escritorio
ALTO_FILA_MOVIL = 58      # dos líneas, en móvil
X_NOMBRE = 58
X_TIPO = 306              # columna del tipo, en escritorio
X_TEC = 520               # columna de las tecnologías, en escritorio

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


def _recortar(texto: str, estilo: str, ancho_max: float) -> str:
    """El texto, con puntos suspensivos si no cabe en `ancho_max`."""
    if medir(texto, estilo) <= ancho_max:
        return texto
    recorte = texto
    while recorte and medir(recorte + "…", estilo) > ancho_max:
        recorte = recorte[:-1]
    return recorte.rstrip(" ·,") + "…"


def _tecnologias(items: list[str], ancho_max: float) -> str:
    """Las tecnologías que caben en `ancho_max`, con un +N si quedan fuera."""
    texto, usados = "", 0
    for i, item in enumerate(items):
        prueba = f"{texto} · {item}" if texto else item
        resto = len(items) - i - 1
        sufijo = f" +{resto}" if resto else ""
        if medir(prueba + sufijo, "mono-pequeno") > ancho_max:
            break
        texto, usados = prueba, i + 1
    resto = len(items) - usados
    return texto + (f" +{resto}" if resto else "")


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
    lz = Lienzo(ancho, ALTO_CABECERA, tema, tx["titulo"], desc)
    t = lz.t
    lz.raw(f'<rect width="{f1(ancho)}" height="{ALTO_CABECERA}" fill="{t["fondo"]}"/>')
    lz.raw(f'<path d="{_borde_cabecera(ancho, ALTO_CABECERA)}" fill="none" stroke="{t["linea"]}"/>')
    lz.raw(
        f'<line x1="0.5" y1="{f1(ALTO_CABECERA - 0.5)}" x2="{f1(ancho - 0.5)}" '
        f'y2="{f1(ALTO_CABECERA - 0.5)}" stroke="{t["linea"]}" stroke-dasharray="2 4"/>'
    )
    lz.raw(lz.texto(X, 38, "04", "seccion", "acento"))
    lz.raw(lz.texto(X + medir("04", "seccion") + 12, 38, tx["titulo"], "seccion", "suave", mayus=True))
    lz.raw(lz.texto(ancho - X, 38, tx["meta"].format(n=n), "meta", "suave", anchor="end"))
    return lz.render()


def fila(tema: str, tx: dict, proyecto: dict, indice: int, ancho: float, ultima: bool) -> str:
    movil = es_movil(ancho)
    url, tipo = enlace_proyecto(proyecto)
    etiqueta = tx["demo"] if tipo == "demo" else tx["codigo"]
    alto = ALTO_FILA_MOVIL if movil else ALTO_FILA

    titulo = f"{proyecto['nombre']} — {etiqueta}"
    desc = (
        f"{proyecto['nombre']}. {proyecto['tipo']} · {proyecto['periodo']}. {proyecto['descripcion']} "
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

    ancho_etiqueta = 18 + medir(etiqueta, "mono-pequeno")
    y_enlace = 24 if movil else 27

    if movil:
        y1, y2 = 24, 44
        hueco_nombre = ancho - X_NOMBRE - X - ancho_etiqueta - 12
        nombre = _recortar(proyecto["nombre"], "dato", hueco_nombre)
        lz.raw(lz.texto(X, y1, f"{indice:02d}", "mono-pequeno", "acento"))
        lz.raw(lz.texto(X_NOMBRE, y1, nombre, "dato", "tinta"))
        _enlace(lz, ancho - X - ancho_etiqueta, y_enlace, tipo, tx)

        meta_tipo = f"{proyecto['tipo']} · "
        meta = meta_tipo + _tecnologias(proyecto["tecnologias"], ancho - X_NOMBRE - X - medir(meta_tipo, "mono-pequeno"))
        lz.raw(lz.texto(X_NOMBRE, y2, meta, "mono-pequeno", "suave"))
    else:
        y = 27
        hueco_nombre = X_TIPO - X_NOMBRE - 12
        nombre = _recortar(proyecto["nombre"], "dato", hueco_nombre)
        lz.raw(lz.texto(X, y, f"{indice:02d}", "mono-pequeno", "acento"))
        lz.raw(lz.texto(X_NOMBRE, y, nombre, "dato", "tinta"))
        tipo_texto = _recortar(proyecto["tipo"].upper(), "mono-pequeno", X_TEC - X_TIPO - 16)
        lz.raw(lz.texto(X_TIPO, y, tipo_texto, "mono-pequeno", "suave"))

        hueco_tec = ancho - X - ancho_etiqueta - 16 - X_TEC
        tecnologias = _tecnologias(proyecto["tecnologias"], hueco_tec)
        lz.raw(lz.texto(X_TEC, y, tecnologias, "mono-pequeno", "suave"))
        _enlace(lz, ancho - X - ancho_etiqueta, y_enlace, tipo, tx)

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
