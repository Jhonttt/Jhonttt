#!/usr/bin/env python3
"""Escribe el README: cada pieza es un <picture> que elige entre cuatro SVG.

- Por ancho de pantalla: hasta MOVIL_MAX px, la versión de móvil (una columna,
  pensada para verse a su tamaño); por encima, la de escritorio.
- Por tema: el oscuro si el sistema lo pide; el claro si no.

Arriba va el interruptor ES | EN: un <details> que, al pulsarlo, despliega
el perfil entero en inglés ahí mismo, sin salir del perfil. GitHub no deja
JavaScript ni CSS en el README, así que no hay forma de ESCONDER el español al
abrirlo: el inglés aparece encima y el español sigue debajo.

Los SVG no viven en main sino en la rama `salida`, que el workflow reescribe
con un único commit cada vez que los genera. Así main no acumula un commit
diario solo para actualizar dibujos.

Uso: python scripts/readme.py
"""

from __future__ import annotations

from html import escape

from comun import RAIZ, datos, sufijo

MOVIL_MAX = 767   # el ancho a partir del cual GitHub pone el perfil en una columna
SALIDA = "https://raw.githubusercontent.com/{usuario}/{usuario}/salida/{nombre}.svg"

AVISO = [
    "  Lo genera scripts/readme.py: no lo edites a mano.",
    "  Todo lo que se ve son SVG generados con Python desde datos/perfil.json",
    "  (scripts/), publicados en la rama `salida`. Cada <picture> elige la versión",
    "  de móvil o la de escritorio según el ancho de la pantalla, y la clara o la",
    "  oscura según el tema. Va todo en un único bloque HTML, sin líneas en blanco,",
    "  y los tres enlaces de contacto pegados, para que formen una sola barra.",
    "  El <details> de arriba despliega el perfil en inglés (datos/perfil.en.json).",
]

TEXTOS = {
    "es": {
        "sobre_mi": "Sobre mí. ",
        "trayectoria": "Trayectoria: {}.",
        "stack": "Con qué trabajo: {}.",
        "actividad": "Actividad en GitHub durante el último año, en 3D: lo público y, encima, "
                     "lo hecho en repositorios privados; con las rachas y el reparto de lenguajes "
                     "de mis repositorios públicos.",
        "pie": "Generado con Python desde {enlace} · la actividad se actualiza sola cada hora",
        "datos": "datos/perfil.json",
    },
    "en": {
        "sobre_mi": "About me. ",
        "trayectoria": "Timeline: {}.",
        "stack": "What I work with: {}.",
        "actividad": "GitHub activity over the last year, in 3D: public work and, on top, "
                     "work in private repositories; with streaks and the language breakdown "
                     "of my public repositories.",
        "pie": "English version, generated from {enlace} · the Spanish one follows below",
        "datos": "datos/perfil.en.json",
    },
}


def picture(usuario: str, nombre: str, alt: str, ancho: str = "100%", idioma: str = "es") -> str:
    url = lambda variante: SALIDA.format(usuario=usuario, nombre=f"{nombre}{variante}")
    s = sufijo(idioma)
    return (
        "<picture>"
        f'<source media="(max-width: {MOVIL_MAX}px) and (prefers-color-scheme: dark)" srcset="{url(f"-movil{s}-dark")}">'
        f'<source media="(max-width: {MOVIL_MAX}px)" srcset="{url(f"-movil{s}-light")}">'
        f'<source media="(prefers-color-scheme: dark)" srcset="{url(f"{s}-dark")}">'
        f'<img src="{url(f"{s}-light")}" width="{ancho}" alt="{escape(alt, quote=True)}">'
        "</picture>"
    )


def boton(usuario: str) -> str:
    """El interruptor ES | EN, botón del desplegable. Es pequeño y no tiene
    versión de móvil, solo clara y oscura; sin width, para que se vea a su tamaño."""
    url = lambda tema: SALIDA.format(usuario=usuario, nombre=f"idioma-{tema}")
    return (
        "<picture>"
        f'<source media="(prefers-color-scheme: dark)" srcset="{url("dark")}">'
        f'<img src="{url("light")}" alt="Idioma: español. Read in English">'
        "</picture>"
    )


def piezas(idioma: str) -> list[str]:
    """El perfil entero en un idioma, del banner al pie."""
    p = datos(idioma)
    tx = TEXTOS[idioma]
    u = p["usuario"]
    pic = lambda nombre, alt, ancho="100%": picture(u, nombre, alt, ancho, idioma)
    c = p["contacto"]
    web = c["web"].removeprefix("https://").rstrip("/")
    linkedin = "in/" + c["linkedin"].rstrip("/").rsplit("/", 1)[-1]
    etapas = "; ".join(f"{e['titulo']}, {e['lugar']}" for e in p["trayectoria"])
    stack = ", ".join(i["nombre"] for g in p["stack"] for i in g["items"])
    return [
        pic("banner", f"{p['nombre']}. {p['titular']}. {p['ubicacion']['texto']}."),
        f'<a href="{c["web"]}">{picture(u, "contacto-web", f"Portfolio: {web}", "33.3%")}</a>'
        f'<a href="{c["linkedin"]}">{picture(u, "contacto-linkedin", f"LinkedIn: {linkedin}", "33.3%")}</a>'
        f'<a href="mailto:{c["email"]}">{picture(u, "contacto-email", f"Email: {c["email"]}", "33.3%")}</a>',
        pic("sobre-mi", tx["sobre_mi"] + " ".join(p["sobre_mi"]["texto"])),
        pic("trayectoria", tx["trayectoria"].format(etapas)),
        pic("stack", tx["stack"].format(stack)),
        pic("actividad", tx["actividad"]),
        "<br><sub>" + tx["pie"].format(enlace=f'<a href="{tx["datos"]}"><code>{tx["datos"]}</code></a>') + "</sub>",
    ]


def main() -> None:
    usuario = datos()["usuario"]
    lineas = [
        "<!--",
        *AVISO,
        "-->",
        '<div align="center">',
        "<details>",
        f"<summary>{boton(usuario)}</summary>",
        *piezas("en"),
        "<br><br>",
        "</details>",
        *piezas("es"),
        "</div>",
    ]
    (RAIZ / "README.md").write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="\n")
    print("README escrito")


if __name__ == "__main__":
    main()
