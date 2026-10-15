#!/usr/bin/env python3
"""Las tarjetas de presentación, a partir de datos/perfil.json:

- 01 Sobre mí: quién soy, en dos párrafos, y unos datos al lado.
- 02 Trayectoria: cada etapa con su barra en un eje de tiempo común, para
  ver de un vistazo cómo encajan los estudios y la empresa.
- 03 Con qué trabajo: el stack por grupos; lo que usé en la empresa, marcado.
- La barra de contacto: tres segmentos que se colocan uno junto a otro bajo
  la cabecera y se leen como una sola pieza.

Cada pieza sale en dos anchos: el de escritorio y el de móvil (ANCHO_MOVIL en
comun.py), que lo pone todo en una sola columna.

Uso: python scripts/ficha.py
"""

from __future__ import annotations

import datetime as dt

from comun import Lienzo, datos, envolver, es_movil, f1, guardar_versiones, icono, medir, tarjeta

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
    lz.raw(f'<line x1="{X}" y1="{f1(y)}" x2="{lz.ancho - X}" y2="{f1(y)}" stroke="{lz.t["linea"]}" stroke-dasharray="2 4"/>')


# --- 01 Sobre mí -------------------------------------------------------------

def sobre_mi(tema: str, perfil: dict, ancho: float) -> str:
    bloque = perfil["sobre_mi"]
    movil = es_movil(ancho)
    # En escritorio, los datos van en una columna a la derecha; en móvil, debajo.
    col_texto = ancho - 2 * X if movil else 474
    x_datos = X if movil else 548
    ancho_datos = ancho - X - x_datos
    paso = 24 if movil else 25

    # Primero se mide todo, para saber la altura de la tarjeta.
    parrafos = [envolver(p, "cuerpo", col_texto) for p in bloque["texto"]]
    alto_texto = sum(len(p) * paso for p in parrafos) + (len(parrafos) - 1) * 12
    datos_env = [(k, envolver(v, "pequeno-fuerte", ancho_datos)) for k, v in bloque["datos"]]
    alto_datos = sum(22 + len(v) * 18 + 16 for _, v in datos_env) - 16
    if movil:
        alto = 56 + 34 + alto_texto + 44 + alto_datos + 30
    else:
        alto = 56 + 34 + max(alto_texto, alto_datos) + 34

    lz = Lienzo(ancho, alto, tema, "Sobre mí", " ".join(bloque["texto"]))
    tarjeta(lz, "01", "Sobre mí")
    y = 56 + 34 + 12
    for i, lineas in enumerate(parrafos):
        for linea in lineas:
            lz.raw(lz.texto(X, y, linea, "cuerpo", "tinta" if i == 0 else "suave"))
            y += paso
        y += 12

    if movil:
        y_linea = 56 + 34 + alto_texto + 18.5
        lz.raw(f'<line x1="{X}" y1="{f1(y_linea)}" x2="{ancho - X}" y2="{f1(y_linea)}" stroke="{lz.t["linea"]}"/>')
        y = y_linea + 30
    else:
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


def _eje(lz: Lienzo, eje_x0: float, eje_x1: float, y_anios: float, y0: float, y1: float, y_hoy: float):
    """Dibuja el eje de tiempo (una línea por año y la marca de hoy) y devuelve
    la función que pasa de una fecha a su x."""
    t = lz.t
    hoy = dt.date.today().replace(day=1)
    t_ini = dt.date(2024, 7, 1)
    t_fin = dt.date(hoy.year + 1, 7, 1)
    meses_totales = (t_fin.year - t_ini.year) * 12 + t_fin.month - t_ini.month

    def x_de(fecha: dt.date) -> float:
        meses = (fecha.year - t_ini.year) * 12 + fecha.month - t_ini.month + (fecha.day - 1) / 30
        return eje_x0 + (eje_x1 - eje_x0) * meses / meses_totales

    for anio in range(t_ini.year + 1, t_fin.year + 1):
        x = x_de(dt.date(anio, 1, 1))
        lz.raw(f'<line x1="{f1(x)}" y1="{y0}" x2="{f1(x)}" y2="{f1(y1)}" stroke="{t["rejilla"]}" stroke-width="1"/>')
        lz.raw(lz.texto(x, y_anios, str(anio), "mono-pequeno", "suave", anchor="middle"))
    xh = x_de(dt.date.today())
    lz.raw(f'<line x1="{f1(xh)}" y1="{y0 + 18}" x2="{f1(xh)}" y2="{f1(y1)}" stroke="{t["acento"]}" stroke-width="1" stroke-dasharray="2 3" opacity="0.7"/>')
    lz.raw(lz.texto(xh, y_hoy, "hoy", "mono-pequeno", "acento", anchor="middle"))
    return x_de, hoy


def _barra(lz: Lienzo, i: int, etapa: dict, x_de, hoy: dt.date, yb: float) -> None:
    """La barra de una etapa en el eje; la actual, con degradado y pulso."""
    t = lz.t
    x0 = x_de(_mes(etapa["desde"], hoy))
    if not etapa.get("hasta"):
        x1 = x_de(dt.date.today())
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


def _filas_etiquetas(etiquetas: list[str], ancho_max: float) -> list[list[str]]:
    """Reparte las etiquetas en las líneas que hagan falta."""
    filas: list[list[str]] = [[]]
    x = 0.0
    for etiqueta in etiquetas:
        w = medir(etiqueta, "mono-pequeno") + 16
        if filas[-1] and x + w > ancho_max:
            filas.append([])
            x = 0.0
        filas[-1].append(etiqueta)
        x += w + 6
    return filas


def _etiquetas(lz: Lienzo, x0: float, yy: float, filas: list[list[str]]) -> None:
    t = lz.t
    for fila in filas:
        x = x0
        for etiqueta in fila:
            w = medir(etiqueta, "mono-pequeno") + 16
            lz.raw(f'<rect x="{f1(x)}" y="{f1(yy - 6)}" width="{f1(w)}" height="22" rx="6" fill="{t["panel"]}" stroke="{t["linea"]}"/>')
            lz.raw(lz.texto(x + 8, yy + 9, etiqueta, "mono-pequeno", "suave"))
            x += w + 6
        yy += 28


def trayectoria(tema: str, perfil: dict, ancho: float) -> str:
    if es_movil(ancho):
        return _trayectoria_movil(tema, perfil, ancho)
    etapas = perfil["trayectoria"]
    eje_x0, eje_x1 = 604, ancho - X - 4
    col_texto = 196
    ancho_texto = eje_x0 - col_texto - 34

    # Medición previa de cada fila.
    filas = []
    for etapa in etapas:
        lineas = envolver(etapa["texto"], "pequeno", ancho_texto)
        etiquetas = _filas_etiquetas(etapa.get("etiquetas", []), ancho_texto)
        alto = 18 + 20 + 10 + len(lineas) * 19 + (34 + 28 * (len(etiquetas) - 1) if etapa.get("etiquetas") else 0)
        filas.append((etapa, lineas, etiquetas, alto))
    y_filas = 56 + 50
    alto = y_filas + sum(a + 38 for *_, a in filas) - 38 + 44

    lz = Lienzo(ancho, alto, tema, "Trayectoria",
                "; ".join(f"{e['titulo']}, {e['lugar']} ({_rango(e)})" for e in etapas))
    tarjeta(lz, "02", "Trayectoria")
    x_de, hoy = _eje(lz, eje_x0, eje_x1, 86, 78, alto - 40, alto - 24)

    y = y_filas
    for i, (etapa, lineas, etiquetas, alto_fila) in enumerate(filas):
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
            _etiquetas(lz, col_texto, yy + 2, etiquetas)

        _barra(lz, i, etapa, x_de, hoy, y + 10)

        y += alto_fila + 38
        if i < len(filas) - 1:
            separador(lz, y - 20)
    return lz.render()


def _trayectoria_movil(tema: str, perfil: dict, ancho: float) -> str:
    """En móvil, el eje de tiempo va arriba, con una barra por etapa, y las
    etapas debajo, a todo el ancho. Cada etapa lleva su número en las dos partes."""
    etapas = perfil["trayectoria"]
    col = ancho - 2 * X
    x_num = X + 22            # las barras empiezan tras el número de la etapa
    y_eje = 56 + 28
    alto_eje = 26 + len(etapas) * 22 + 34

    filas = []
    for etapa in etapas:
        lineas = envolver(etapa["texto"], "pequeno", col)
        etiquetas = _filas_etiquetas(etapa.get("etiquetas", []), col)
        alto = 18 + 22 + 20 + 12 + len(lineas) * 19 + (34 + 28 * (len(etiquetas) - 1) if etapa.get("etiquetas") else 0)
        filas.append((etapa, lineas, etiquetas, alto))
    y_filas = y_eje + alto_eje + 26
    alto = y_filas + sum(a + 38 for *_, a in filas) - 38 + 28

    lz = Lienzo(ancho, alto, tema, "Trayectoria",
                "; ".join(f"{e['titulo']}, {e['lugar']} ({_rango(e)})" for e in etapas))
    tarjeta(lz, "02", "Trayectoria")
    y_fin_eje = y_eje + alto_eje - 22
    x_de, hoy = _eje(lz, x_num + 4, ancho - X - 4, y_eje + 8, y_eje, y_fin_eje, y_fin_eje + 16)
    for i, etapa in enumerate(etapas):
        yb = y_eje + 26 + i * 22
        lz.raw(lz.texto(X, yb + 7, f"{i + 1:02d}", "mono-pequeno", "acento" if not etapa.get("hasta") else "suave"))
        _barra(lz, i, etapa, x_de, hoy, yb)
    separador(lz, y_filas - 26)

    y = y_filas
    for i, (etapa, lineas, etiquetas, alto_fila) in enumerate(filas):
        actual = not etapa.get("hasta")
        lz.raw(lz.texto(X, y + 10, f"{i + 1:02d} · {etapa['tipo'].upper()}", "mono-pequeno", "acento" if actual else "suave"))
        lz.raw(lz.texto(ancho - X, y + 10, _rango(etapa), "etiqueta", "tinta" if actual else "suave", anchor="end"))
        lz.raw(lz.texto(X, y + 38, etapa["titulo"], "dato", "tinta"))
        lz.raw(lz.texto(X, y + 58, etapa["lugar"], "pequeno", "suave"))
        yy = y + 84
        for linea in lineas:
            lz.raw(lz.texto(X, yy, linea, "pequeno", "tinta"))
            yy += 19
        if etapa.get("etiquetas"):
            _etiquetas(lz, X, yy + 2, etiquetas)
        y += alto_fila + 38
        if i < len(filas) - 1:
            separador(lz, y - 20)
    return lz.render()


# --- 03 Con qué trabajo ------------------------------------------------------

def _ancho_chip(item: dict) -> float:
    return 10 + 15 + 8 + medir(item["nombre"], "pequeno-fuerte") + 12


def _chip(lz: Lienzo, x: float, y: float, item: dict) -> float:
    """Dibuja un chip y devuelve su ancho."""
    t = lz.t
    destacado = item.get("empresa", False)
    nombre = item["nombre"]
    w = _ancho_chip(item)
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


def stack(tema: str, perfil: dict, ancho: float) -> str:
    grupos = perfil["stack"]
    movil = es_movil(ancho)
    # En móvil, el nombre del grupo va encima de sus chips y no a la izquierda.
    x_chips, x_max = (X if movil else 168), ancho - X
    rotulo = 26 if movil else 0

    # Reparto de chips en líneas, para conocer la altura antes de dibujar.
    reparto = []
    for grupo in grupos:
        lineas, actual, ocupado = [], [], 0.0
        for item in grupo["items"]:
            w = _ancho_chip(item)
            if actual and x_chips + ocupado + w > x_max:
                lineas.append(actual)
                actual, ocupado = [], 0.0
            actual.append(item)
            ocupado += w + 8
        lineas.append(actual)
        reparto.append((grupo["grupo"], lineas))
    alto = 56 + 26 + sum(rotulo + len(l) * 40 + 30 for _, l in reparto) - 30 + 30
    if movil:
        alto += 26  # la leyenda, que en móvil no cabe en la cabecera

    lz = Lienzo(ancho, alto, tema, "Con qué trabajo",
                ", ".join(i["nombre"] for g in grupos for i in g["items"]) + ".")
    t = lz.t
    tarjeta(lz, "03", "Con qué trabajo")
    # Leyenda: qué significa el borde de color. En la cabecera o, en móvil, al pie.
    leyenda = perfil.get("leyenda_empresa", "usado en la empresa")
    w_ley = medir(leyenda, "meta")
    y_ley = alto - 30 if movil else 38
    x_ley = X + 20 if movil else ancho - X
    x_caja = X if movil else ancho - X - w_ley - 20
    lz.raw(f'<rect x="{f1(x_caja)}" y="{y_ley - 8}" width="12" height="10" rx="3" fill="{t["panel"]}" stroke="{t["acento"]}" stroke-opacity="0.6"/>')
    lz.raw(lz.texto(x_ley, y_ley, leyenda, "meta", "suave", anchor="start" if movil else "end"))

    y = 56 + 26
    for k, (nombre, lineas) in enumerate(reparto):
        if movil:
            lz.raw(lz.texto(X, y + 10, nombre, "mono-pequeno", "suave", mayus=True))
            y += rotulo
        else:
            lz.raw(lz.texto(X, y + 19.5, nombre, "mono-pequeno", "suave", mayus=True))
        for linea in lineas:
            x = x_chips
            for item in linea:
                x += _chip(lz, x, y, item) + 8
            y += 40
        y += 30
        if k < len(reparto) - 1 or movil:
            separador(lz, y - 30 + 10)
    return lz.render()


# --- contacto ----------------------------------------------------------------

def _rect_esquinas(x, y, w, h, tl, tr, br, bl) -> str:
    return (f"M{x + tl} {y}H{x + w - tr}" + (f"A{tr} {tr} 0 0 1 {x + w} {y + tr}" if tr else "") +
            f"V{y + h - br}" + (f"A{br} {br} 0 0 1 {x + w - br} {y + h}" if br else "") +
            f"H{x + bl}" + (f"A{bl} {bl} 0 0 1 {x} {y + h - bl}" if bl else "") +
            f"V{y + tl}" + (f"A{tl} {tl} 0 0 1 {x + tl} {y}" if tl else "") + "Z")


def contacto(tema: str, clave: str, rotulo: str, valor: str, posicion: int, ancho: float) -> str:
    """Uno de los tres segmentos (posición 0, 1 o 2) de la barra de contacto.

    En móvil no cabe el valor (el email solo ya ocupa más que un tercio), así
    que el segmento lleva el icono y el rótulo, centrados.
    """
    movil = es_movil(ancho)
    w = round(ancho / 3, 2)
    h = 64 if movil else 58
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
    if movil:
        lz.raw(f'<g transform="translate({f1(w / 2 - 8)} 13)" fill="none" stroke="{t["acento"]}" stroke-width="1.4" '
               f'stroke-linecap="round" stroke-linejoin="round">{ICONOS_CONTACTO[clave]}</g>')
        lz.raw(lz.texto(w / 2, 48, rotulo, "pequeno-fuerte", "tinta", anchor="middle"))
        return lz.render()
    lz.raw(f'<g transform="translate(22 {h / 2 - 8})" fill="none" stroke="{t["acento"]}" stroke-width="1.4" '
           f'stroke-linecap="round" stroke-linejoin="round">{ICONOS_CONTACTO[clave]}</g>')
    lz.raw(lz.texto(52, 25, rotulo, "mono-pequeno", "suave", mayus=True))
    lz.raw(lz.texto(52, 42, valor, "pequeno-fuerte", "tinta"))
    lz.raw(f'<path d="M{w - 30} {h / 2 + 4}l7-7M{w - 29} {h / 2 - 3}h6v6" fill="none" stroke="{t["suave"]}" '
           f'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>')
    return lz.render()


def main() -> None:
    perfil = datos()
    guardar_versiones("sobre-mi", lambda tema, ancho: sobre_mi(tema, perfil, ancho))
    guardar_versiones("trayectoria", lambda tema, ancho: trayectoria(tema, perfil, ancho))
    guardar_versiones("stack", lambda tema, ancho: stack(tema, perfil, ancho))
    c = perfil["contacto"]
    segmentos = [
        ("web", "Portfolio", c["web"].removeprefix("https://").rstrip("/")),
        ("linkedin", "LinkedIn", "in/" + c["linkedin"].rstrip("/").rsplit("/", 1)[-1]),
        ("email", "Email", c["email"]),
    ]
    for i, (clave, rotulo, valor) in enumerate(segmentos):
        guardar_versiones(f"contacto-{clave}",
                          lambda tema, ancho, clave=clave, rotulo=rotulo, valor=valor, i=i:
                          contacto(tema, clave, rotulo, valor, i, ancho))
    print("sobre-mi, trayectoria, stack y contacto generados")


if __name__ == "__main__":
    main()
