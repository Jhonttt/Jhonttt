#!/usr/bin/env python3
"""Las tarjetas de presentación, a partir de datos/perfil.json:

- 01 Sobre mí: quién soy, en dos párrafos, y unos datos al lado.
- 02 Trayectoria: cada etapa con su barra en un eje de tiempo común, para
  ver de un vistazo cómo encajan los estudios y la empresa.
- 03 Con qué trabajo: el stack por grupos; lo que usé en la empresa, marcado.
- La barra de contacto: tres segmentos que se colocan uno junto a otro bajo
  la cabecera y se leen como una sola pieza.

Uso: python scripts/ficha.py
"""

from __future__ import annotations

import datetime as dt

from comun import ANCHO, TEMAS, Lienzo, datos, envolver, f1, guardar, icono, medir, tarjeta

X = 28  # margen lateral de todas las tarjetas
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Iconos propios, de trazo, para lo que no tiene icono en simple-icons (24x24).
ICONOS_PROPIOS = {
    "sql": '<ellipse cx="12" cy="5.5" rx="7.5" ry="3"/><path d="M4.5 5.5v13c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-13M4.5 12c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3"/>',
    "husky": '<path d="M9 2.5v12a3.5 3.5 0 0 0 7 0V12"/><path d="m13 14.5 3-3 3 3"/>',
    "githubprojects": '<rect x="3" y="3.5" width="18" height="17" rx="2.5"/><path d="M9 3.5v17M15 3.5v17"/>',
}
# Iconos de trazo de 16x16 para la barra de contacto.
ICONOS_CONTACTO = {
    "web": '<circle cx="8" cy="8" r="6.5"/><path d="M1.5 8h13M8 1.5c1.9 1.9 2.8 4.1 2.8 6.5S9.9 12.6 8 14.5M8 1.5C6.1 3.4 5.2 5.6 5.2 8s.9 4.6 2.8 6.5"/>',
    "linkedin": '<rect x="1.5" y="1.5" width="13" height="13" rx="2.5"/><path d="M5 7v4.5M5 4.6v.1M8 11.5V7m0 2.2c0-1.4.9-2.2 2-2.2s1.8.8 1.8 2.2v2.3"/>',
    "email": '<rect x="1.5" y="3" width="13" height="10" rx="2"/><path d="m2 4 6 5 6-5"/>',
}


def separador(lz: Lienzo, y: float) -> None:
    lz.raw(f'<line x1="{X}" y1="{f1(y)}" x2="{ANCHO - X}" y2="{f1(y)}" stroke="{lz.t["linea"]}" stroke-dasharray="2 4"/>')


# --- 01 Sobre mí -------------------------------------------------------------

def sobre_mi(tema: str, perfil: dict) -> str:
    bloque = perfil["sobre_mi"]
    col_texto = 474
    x_datos = 548
    ancho_datos = ANCHO - X - x_datos

    # Primero se mide todo, para saber la altura de la tarjeta.
    parrafos = [envolver(p, "cuerpo", col_texto) for p in bloque["texto"]]
    alto_texto = sum(len(p) * 25 for p in parrafos) + (len(parrafos) - 1) * 12
    datos_env = [(k, envolver(v, "pequeno-fuerte", ancho_datos)) for k, v in bloque["datos"]]
    alto_datos = sum(22 + len(v) * 18 + 16 for _, v in datos_env) - 16
    alto = 56 + 34 + max(alto_texto, alto_datos) + 34

    lz = Lienzo(ANCHO, alto, tema, "Sobre mí", " ".join(bloque["texto"]))
    tarjeta(lz, "01", "Sobre mí")
    y = 56 + 34 + 12
    for i, lineas in enumerate(parrafos):
        for linea in lineas:
            lz.raw(lz.texto(X, y, linea, "cuerpo", "tinta" if i == 0 else "suave"))
            y += 25
        y += 12

    lz.raw(f'<line x1="{x_datos - 26}.5" y1="{56 + 30}" x2="{x_datos - 26}.5" y2="{alto - 30}" stroke="{lz.t["linea"]}"/>')
    y = 56 + 34 + 8
    for clave, lineas in datos_env:
        lz.raw(lz.texto(x_datos, y, clave, "mono-pequeno", "suave", mayus=True))
        y += 20
        for linea in lineas:
            lz.raw(lz.texto(x_datos, y, linea, "pequeno-fuerte", "tinta"))
            y += 18
        y += 16
    return lz.render()


# --- 02 Trayectoria ----------------------------------------------------------

def _mes(texto: str | None, hoy: dt.date) -> dt.date:
    if not texto:
        return hoy
    a, m = texto.split("-")
    return dt.date(int(a), int(m), 1)


def _rango(etapa: dict) -> str:
    d = _mes(etapa["desde"], dt.date.today())
    if etapa.get("solo_anio"):
        ini = str(d.year)
    else:
        ini = f"{MESES[d.month - 1]} {d.year}"
    if not etapa.get("hasta"):
        return f"{ini} — hoy"
    h = _mes(etapa["hasta"], dt.date.today())
    if h.year == d.year and not etapa.get("solo_anio"):
        return f"{MESES[d.month - 1]} — {MESES[h.month - 1]} {h.year}"
    return f"{ini} — {MESES[h.month - 1]} {h.year}"


def trayectoria(tema: str, perfil: dict) -> str:
    etapas = perfil["trayectoria"]
    hoy = dt.date.today().replace(day=1)
    t_ini = dt.date(2024, 7, 1)
    t_fin = dt.date(hoy.year + 1, 7, 1)
    eje_x0, eje_x1 = 604, ANCHO - X - 4
    meses_totales = (t_fin.year - t_ini.year) * 12 + t_fin.month - t_ini.month

    def x_de(fecha: dt.date) -> float:
        meses = (fecha.year - t_ini.year) * 12 + fecha.month - t_ini.month + (fecha.day - 1) / 30
        return eje_x0 + (eje_x1 - eje_x0) * meses / meses_totales

    col_texto = 196
    ancho_texto = eje_x0 - col_texto - 34

    # Medición previa de cada fila.
    filas = []
    for etapa in etapas:
        lineas = envolver(etapa["texto"], "pequeno", ancho_texto)
        alto = 18 + 20 + 10 + len(lineas) * 19 + (34 if etapa.get("etiquetas") else 0)
        filas.append((etapa, lineas, alto))
    y_filas = 56 + 50
    alto = y_filas + sum(a + 38 for _, _, a in filas) - 38 + 44

    lz = Lienzo(ANCHO, alto, tema, "Trayectoria",
                "; ".join(f"{e['titulo']}, {e['lugar']} ({_rango(e)})" for e in etapas))
    t = lz.t
    tarjeta(lz, "02", "Trayectoria")

    # El eje: una línea por año y la marca de hoy.
    for anio in range(t_ini.year + 1, t_fin.year + 1):
        x = x_de(dt.date(anio, 1, 1))
        lz.raw(f'<line x1="{f1(x)}" y1="78" x2="{f1(x)}" y2="{alto - 40}" stroke="{t["rejilla"]}" stroke-width="1"/>')
        lz.raw(lz.texto(x, 86, str(anio), "mono-pequeno", "suave", anchor="middle"))
    xh = x_de(dt.date.today())
    lz.raw(f'<line x1="{f1(xh)}" y1="96" x2="{f1(xh)}" y2="{alto - 40}" stroke="{t["acento"]}" stroke-width="1" stroke-dasharray="2 3" opacity="0.7"/>')
    lz.raw(lz.texto(xh, alto - 24, "hoy", "mono-pequeno", "acento", anchor="middle"))

    y = y_filas
    for i, (etapa, lineas, alto_fila) in enumerate(filas):
        actual = not etapa.get("hasta")
        lz.raw(lz.texto(X, y + 16, _rango(etapa), "etiqueta", "tinta" if actual else "suave"))
        lz.raw(lz.texto(X, y + 36, etapa["tipo"], "mono-pequeno", "acento" if actual else "suave", mayus=True))

        lz.raw(lz.texto(col_texto, y + 16, etapa["titulo"], "dato", "tinta"))
        lz.raw(lz.texto(col_texto, y + 37, etapa["lugar"], "pequeno", "suave"))
        yy = y + 64
        for linea in lineas:
            lz.raw(lz.texto(col_texto, yy, linea, "pequeno", "tinta"))
            yy += 19
        if etapa.get("etiquetas"):
            x = col_texto
            yy += 2
            for etiqueta in etapa["etiquetas"]:
                w = medir(etiqueta, "mono-pequeno") + 16
                lz.raw(f'<rect x="{f1(x)}" y="{f1(yy - 6)}" width="{f1(w)}" height="22" rx="6" fill="{t["panel"]}" stroke="{t["linea"]}"/>')
                lz.raw(lz.texto(x + 8, yy + 9, etiqueta, "mono-pequeno", "suave"))
                x += w + 6

        # Su barra en el eje.
        x0 = x_de(_mes(etapa["desde"], hoy))
        yb = y + 10
        if actual:
            x1 = xh
            lz.defs_raw(
                f'<linearGradient id="viva{i}" x1="0" x2="1"><stop offset="0" stop-color="{t["acento2"]}"/>'
                f'<stop offset="1" stop-color="{t["acento"]}"/></linearGradient>'
            )
            fin = etapa.get("fin_previsto")
            if fin:
                xf = x_de(_mes(fin, hoy))
                lz.raw(f'<line x1="{f1(x1)}" y1="{yb + 3}" x2="{f1(xf)}" y2="{yb + 3}" stroke="{t["acento"]}" stroke-width="2" stroke-dasharray="2 4" opacity="0.55"/>')
            lz.raw(f'<rect x="{f1(x0)}" y="{yb}" width="{f1(max(x1 - x0, 6))}" height="6" rx="3" fill="url(#viva{i})"/>')
            lz.raw(
                f'<circle cx="{f1(x1)}" cy="{yb + 3}" r="3" fill="none" stroke="{t["acento"]}" stroke-width="1.2">'
                f'<animate attributeName="r" values="3;10" dur="2.4s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values="0.8;0" dur="2.4s" repeatCount="indefinite"/></circle>'
                f'<circle cx="{f1(x1)}" cy="{yb + 3}" r="3.5" fill="{t["acento"]}"/>'
            )
        else:
            x1 = x_de(_mes(etapa["hasta"], hoy).replace(day=28))
            color = t["tinta"] if etapa["tipo"] != "estudios" else t["suave"]
            lz.raw(f'<rect x="{f1(x0)}" y="{yb}" width="{f1(max(x1 - x0, 6))}" height="6" rx="3" fill="{color}" opacity="0.85"/>')

        y += alto_fila + 38
        if i < len(filas) - 1:
            separador(lz, y - 20)
    return lz.render()


# --- 03 Con qué trabajo ------------------------------------------------------

def _chip(lz: Lienzo, x: float, y: float, item: dict) -> float:
    """Dibuja un chip y devuelve su ancho."""
    t = lz.t
    destacado = item.get("empresa", False)
    nombre = item["nombre"]
    w = 10 + 15 + 8 + medir(nombre, "pequeno-fuerte") + 12
    borde = t["acento"] if destacado else t["linea"]
    lz.raw(f'<rect x="{f1(x)}" y="{f1(y)}" width="{f1(w)}" height="30" rx="8" fill="{t["panel"]}" '
           f'stroke="{borde}" stroke-opacity="{0.6 if destacado else 1}"/>')
    color = t["acento"] if destacado else t["tinta"]
    slug = item["icono"]
    if slug in ICONOS_PROPIOS:
        lz.raw(f'<g transform="translate({f1(x + 10)} {f1(y + 7.5)}) scale({15 / 24:.4f})" fill="none" stroke="{color}" '
               f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">{ICONOS_PROPIOS[slug]}</g>')
    else:
        _, d = icono(slug)
        lz.raw(f'<g transform="translate({f1(x + 10)} {f1(y + 7.5)}) scale({15 / 24:.4f})"><path d="{d}" fill="{color}"/></g>')
    lz.raw(lz.texto(x + 33, y + 19.5, nombre, "pequeno-fuerte", "tinta"))
    return w


def stack(tema: str, perfil: dict) -> str:
    grupos = perfil["stack"]
    x_chips, x_max = 168, ANCHO - X

    # Reparto de chips en líneas, para conocer la altura antes de dibujar.
    reparto = []
    for grupo in grupos:
        lineas, actual, ancho = [], [], 0.0
        for item in grupo["items"]:
            w = 10 + 15 + 8 + medir(item["nombre"], "pequeno-fuerte") + 12
            if actual and x_chips + ancho + w > x_max:
                lineas.append(actual)
                actual, ancho = [], 0.0
            actual.append(item)
            ancho += w + 8
        lineas.append(actual)
        reparto.append((grupo["grupo"], lineas))
    alto = 56 + 26 + sum(len(l) * 40 + 30 for _, l in reparto) - 30 + 30

    total = sum(len(g["items"]) for g in grupos)
    lz = Lienzo(ANCHO, alto, tema, "Con qué trabajo",
                ", ".join(i["nombre"] for g in grupos for i in g["items"]) + ".")
    t = lz.t
    tarjeta(lz, "03", "Con qué trabajo")
    # Leyenda en la cabecera: qué significa el borde de color.
    leyenda = perfil.get("leyenda_empresa", "usado en la empresa")
    w_ley = medir(leyenda, "meta")
    lz.raw(f'<rect x="{f1(ANCHO - X - w_ley - 20)}" y="30" width="12" height="10" rx="3" fill="{t["panel"]}" stroke="{t["acento"]}" stroke-opacity="0.6"/>')
    lz.raw(lz.texto(ANCHO - X, 38, leyenda, "meta", "suave", anchor="end"))

    y = 56 + 26
    for k, (nombre, lineas) in enumerate(reparto):
        lz.raw(lz.texto(X, y + 19.5, nombre, "mono-pequeno", "suave", mayus=True))
        for linea in lineas:
            x = x_chips
            for item in linea:
                x += _chip(lz, x, y, item) + 8
            y += 40
        y += 30
        if k < len(reparto) - 1:
            separador(lz, y - 30 + 10)
    return lz.render()


# --- contacto ----------------------------------------------------------------

def _rect_esquinas(x, y, w, h, tl, tr, br, bl) -> str:
    return (f"M{x + tl} {y}H{x + w - tr}" + (f"A{tr} {tr} 0 0 1 {x + w} {y + tr}" if tr else "") +
            f"V{y + h - br}" + (f"A{br} {br} 0 0 1 {x + w - br} {y + h}" if br else "") +
            f"H{x + bl}" + (f"A{bl} {bl} 0 0 1 {x} {y + h - bl}" if bl else "") +
            f"V{y + tl}" + (f"A{tl} {tl} 0 0 1 {x + tl} {y}" if tl else "") + "Z")


def contacto(tema: str, clave: str, rotulo: str, valor: str, posicion: int) -> str:
    """Uno de los tres segmentos (posición 0, 1 o 2) de la barra de contacto."""
    w = round(ANCHO / 3, 2)
    h = 58
    lz = Lienzo(w, h, tema, f"{rotulo}: {valor}")
    t = lz.t
    r = 12
    esquinas = {0: (r, 0, 0, r), 1: (0, 0, 0, 0), 2: (0, r, r, 0)}[posicion]
    # El borde de fuera se dibuja entero; entre segmentos, solo la línea izquierda
    # del segundo y del tercero, para que no se dupliquen.
    lz.raw(f'<path d="{_rect_esquinas(0.5, 0.5, w - 1 + (1 if posicion < 2 else 0), h - 1, *esquinas)}" '
           f'fill="{t["fondo"]}" stroke="{t["linea"]}"/>')
    if posicion < 2:
        lz.raw(f'<rect x="{w - 0.6}" y="1" width="1" height="{h - 2}" fill="{t["fondo"]}"/>')
    lz.raw(f'<g transform="translate(22 {h / 2 - 8})" fill="none" stroke="{t["acento"]}" stroke-width="1.4" '
           f'stroke-linecap="round" stroke-linejoin="round">{ICONOS_CONTACTO[clave]}</g>')
    lz.raw(lz.texto(52, 25, rotulo, "mono-pequeno", "suave", mayus=True))
    lz.raw(lz.texto(52, 42, valor, "pequeno-fuerte", "tinta"))
    lz.raw(f'<path d="M{w - 30} {h / 2 + 4}l7-7M{w - 29} {h / 2 - 3}h6v6" fill="none" stroke="{t["suave"]}" '
           f'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>')
    return lz.render()


def main() -> None:
    perfil = datos()
    guardar("sobre-mi", {tema: sobre_mi(tema, perfil) for tema in TEMAS})
    guardar("trayectoria", {tema: trayectoria(tema, perfil) for tema in TEMAS})
    guardar("stack", {tema: stack(tema, perfil) for tema in TEMAS})
    c = perfil["contacto"]
    segmentos = [
        ("web", "Portfolio", c["web"].removeprefix("https://").rstrip("/")),
        ("linkedin", "LinkedIn", "in/" + c["linkedin"].rstrip("/").rsplit("/", 1)[-1]),
        ("email", "Email", c["email"]),
    ]
    for i, (clave, rotulo, valor) in enumerate(segmentos):
        guardar(f"contacto-{clave}", {tema: contacto(tema, clave, rotulo, valor, i) for tema in TEMAS})
    print("sobre-mi, trayectoria, stack y contacto generados")


if __name__ == "__main__":
    main()
