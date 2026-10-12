#!/usr/bin/env python3
"""Tarjetas de presentación: la ficha "sobre mí" y el stack.

Solo biblioteca estándar. Los iconos salen de simple-icons y se guardan en
assets/source/iconos, así que sin red también funciona.

Uso: python scripts/ficha.py
"""

from __future__ import annotations

from comun import MONO, SANS, TEMAS, datos, esc, guardar, icono, marco

ANCHO = 1200
# Nombres de simple-icons que no son los que usa la gente.
NOMBRES = {"openjdk": "Java"}
COL_VALOR = 260


def sobre_mi(t: dict[str, str], perfil: dict) -> str:
    filas = perfil["ficha"]
    alto_fila = 58
    alto = 80 + 16 + len(filas) * alto_fila + 16
    partes = []
    for i, (clave, valor) in enumerate(filas):
        y = 80 + 16 + i * alto_fila
        partes.append(
            f'<text x="36" y="{y + 36}" font-family="{MONO}" font-size="17" fill="{t["suave"]}">{esc(clave)}</text>'
            f'<text x="{COL_VALOR}" y="{y + 37}" font-family="{SANS}" font-size="23" fill="{t["tinta"]}">{esc(valor)}</text>'
        )
        if i < len(filas) - 1:
            partes.append(
                f'<line x1="36" y1="{y + alto_fila}" x2="{ANCHO - 36}" y2="{y + alto_fila}" '
                f'stroke="{t["linea"]}" stroke-dasharray="2 5"/>'
            )
    return marco(t, ANCHO, alto, "01", "Sobre mí", f"{perfil['lugar'].lower()} · europe/madrid", "".join(partes),
                 desc="Ficha de presentación: qué estudio, desde dónde y en qué ando.")


def stack(t: dict[str, str], perfil: dict) -> str:
    grupos = perfil["stack"]
    alto_fila = 112
    columna = 150
    tam = 38
    alto = 80 + 8 + len(grupos) * alto_fila + 8
    partes = []
    total = 0
    for i, grupo in enumerate(grupos):
        y = 80 + 8 + i * alto_fila
        partes.append(f'<text x="36" y="{y + 54}" font-family="{MONO}" font-size="17" fill="{t["suave"]}">{esc(grupo["grupo"])}</text>')
        for j, slug in enumerate(grupo["iconos"]):
            titulo, d = icono(slug)
            titulo = NOMBRES.get(slug, titulo)
            x = COL_VALOR + j * columna
            escala = tam / 24
            partes.append(
                f'<g transform="translate({x} {y + 22}) scale({escala:.4f})"><path d="{d}" fill="{t["tinta"]}"/></g>'
                f'<text x="{x}" y="{y + 90}" font-family="{SANS}" font-size="16" fill="{t["suave"]}">{esc(titulo)}</text>'
            )
            total += 1
        if i < len(grupos) - 1:
            partes.append(
                f'<line x1="36" y1="{y + alto_fila}" x2="{ANCHO - 36}" y2="{y + alto_fila}" '
                f'stroke="{t["linea"]}" stroke-dasharray="2 5"/>'
            )
    return marco(t, ANCHO, alto, "02", "Con qué trabajo", f"{total} herramientas", "".join(partes),
                 desc="Lenguajes, frameworks, bases de datos y herramientas que uso.")


# Iconos de trazo de 16x16 para los botones: no dependen de ninguna fuente.
ICONOS_CONTACTO = {
    "web": '<circle cx="8" cy="8" r="6.5"/><path d="M1.5 8h13M8 1.5c2 2 2.8 4.2 2.8 6.5S10 12.5 8 14.5M8 1.5C6 3.5 5.2 5.7 5.2 8S6 12.5 8 14.5"/>',
    "linkedin": '<rect x="1.5" y="1.5" width="13" height="13" rx="2.5"/><path d="M5 7v4.5M5 4.6v.1M8 11.5V7m0 2.2c0-1.4.9-2.2 2-2.2s1.8.8 1.8 2.2v2.3"/>',
    "email": '<rect x="1.5" y="3" width="13" height="10" rx="2"/><path d="m2 4 6 5 6-5"/>',
}


def boton(t: dict[str, str], clave: str, texto: str) -> str:
    alto = 44
    ancho = round(len(texto) * 7.8 + 92)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" role="img" aria-labelledby="t">
<title id="t">{esc(texto)}</title>
<rect x="0.5" y="0.5" width="{ancho - 1}" height="{alto - 1}" rx="10" fill="{t["fondo"]}" stroke="{t["linea"]}"/>
<g transform="translate(18 14)" fill="none" stroke="{t["acento"]}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">{ICONOS_CONTACTO[clave]}</g>
<text x="46" y="27" font-family="{MONO}" font-size="13" fill="{t["tinta"]}">{esc(texto)}</text>
<path d="M{ancho - 26} 18l5 4-5 4" fill="none" stroke="{t["suave"]}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""


def main() -> None:
    perfil = datos()
    guardar("sobre-mi", {tema: sobre_mi(t, perfil) for tema, t in TEMAS.items()})
    guardar("stack", {tema: stack(t, perfil) for tema, t in TEMAS.items()})
    contacto = perfil["contacto"]
    textos = {
        "web": contacto["web"].removeprefix("https://"),
        "linkedin": "linkedin/" + contacto["linkedin"].rstrip("/").rsplit("/", 1)[-1],
        "email": contacto["email"],
    }
    for clave, texto in textos.items():
        guardar(f"boton-{clave}", {tema: boton(t, clave, texto) for tema, t in TEMAS.items()})
    print("sobre-mi, stack y botones generados")


if __name__ == "__main__":
    main()
