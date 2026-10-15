#!/usr/bin/env python3
"""Escribe el README: cada pieza es un <picture> que elige entre cuatro SVG.

- Por ancho de pantalla: hasta MOVIL_MAX px, la versión de móvil (una columna,
  pensada para verse a su tamaño); por encima, la de escritorio.
- Por tema: el oscuro si el sistema lo pide; el claro si no.

Los SVG no viven en main sino en la rama `salida`, que el workflow reescribe
con un único commit cada vez que los genera. Así main no acumula un commit
diario solo para actualizar dibujos.

Uso: python scripts/readme.py
"""

from __future__ import annotations

from html import escape

from comun import RAIZ, datos

MOVIL_MAX = 767   # el ancho a partir del cual GitHub pone el perfil en una columna
SALIDA = "https://raw.githubusercontent.com/{usuario}/{usuario}/salida/{nombre}.svg"


def picture(usuario: str, nombre: str, alt: str, ancho: str = "100%") -> str:
    url = lambda variante: SALIDA.format(usuario=usuario, nombre=f"{nombre}{variante}")
    return (
        "<picture>"
        f'<source media="(max-width: {MOVIL_MAX}px) and (prefers-color-scheme: dark)" srcset="{url("-movil-dark")}">'
        f'<source media="(max-width: {MOVIL_MAX}px)" srcset="{url("-movil-light")}">'
        f'<source media="(prefers-color-scheme: dark)" srcset="{url("-dark")}">'
        f'<img src="{url("-light")}" width="{ancho}" alt="{escape(alt, quote=True)}">'
        "</picture>"
    )


def main() -> None:
    p = datos()
    u = p["usuario"]
    c = p["contacto"]
    web = c["web"].removeprefix("https://").rstrip("/")
    linkedin = "in/" + c["linkedin"].rstrip("/").rsplit("/", 1)[-1]
    etapas = "; ".join(f"{e['titulo']}, {e['lugar']}" for e in p["trayectoria"])
    stack = ", ".join(i["nombre"] for g in p["stack"] for i in g["items"])

    lineas = [
        "<!--",
        "  Lo genera scripts/readme.py: no lo edites a mano.",
        "  Todo lo que se ve son SVG generados con Python desde datos/perfil.json",
        "  (scripts/), publicados en la rama `salida`. Cada <picture> elige la versión",
        "  de móvil o la de escritorio según el ancho de la pantalla, y la clara o la",
        "  oscura según el tema. Va todo en un único bloque HTML, sin líneas en blanco,",
        "  y los tres enlaces de contacto pegados, para que formen una sola barra.",
        "-->",
        '<div align="center">',
        picture(u, "banner", f"{p['nombre']}. {p['titular']}. {p['ubicacion']['texto']}."),
        f'<a href="{c["web"]}">{picture(u, "contacto-web", f"Portfolio: {web}", "33.3%")}</a>'
        f'<a href="{c["linkedin"]}">{picture(u, "contacto-linkedin", f"LinkedIn: {linkedin}", "33.3%")}</a>'
        f'<a href="mailto:{c["email"]}">{picture(u, "contacto-email", f"Email: {c["email"]}", "33.3%")}</a>',
        picture(u, "sobre-mi", "Sobre mí. " + " ".join(p["sobre_mi"]["texto"])),
        picture(u, "trayectoria", f"Trayectoria: {etapas}."),
        picture(u, "stack", f"Con qué trabajo: {stack}."),
        picture(u, "actividad", "Actividad en GitHub durante el último año, en 3D: lo público y, encima, "
                                "lo hecho en repositorios privados; con las rachas y el reparto de lenguajes "
                                "de mis repositorios públicos."),
        '<br><sub>Generado con Python desde <a href="datos/perfil.json"><code>datos/perfil.json</code></a>'
        " · la actividad se actualiza sola cada día</sub>",
        "</div>",
    ]
    (RAIZ / "README.md").write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="\n")
    print("README escrito")


if __name__ == "__main__":
    main()
