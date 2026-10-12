#!/usr/bin/env python3
"""La tarjeta de actividad, con datos vivos de GitHub:

- el calendario del último año en isométrico: cada día es una columna cuya
  altura sale de lo que hice ese día, y las columnas crecen al cargar;
- unas cifras (total, días con actividad, rachas, mejor día);
- el reparto de lenguajes de mis repositorios públicos.

Necesita un token en GITHUB_TOKEN (en el workflow lo pone Actions; en local
vale `GITHUB_TOKEN=$(gh auth token)`).

Uso: python scripts/actividad.py
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import urllib.request
from collections import Counter

from comun import ANCHO, TEMAS, Lienzo, datos, f1, guardar, medir, tarjeta

API = "https://api.github.com"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# Lenguajes que linguist confunde: Hack es un dialecto de PHP y en mis
# repositorios son ficheros PHP de toda la vida.
EQUIVALENCIAS = {"Hack": "PHP"}
COLORES_LENGUAJE = {
    "dark": ["#7c9dff", "#a78bfa", "#5fc4b8", "#e3b341", "#f0883e", "#8b949e"],
    "light": ["#3b5bdb", "#7048e8", "#0f9488", "#b7791f", "#c2410c", "#6e7781"],
}

# Geometría de la perspectiva (dimétrica): las semanas avanzan hacia la
# derecha con poca pendiente y los días bajan en diagonal. Más ancha y más baja
# que la isométrica, cabe mejor en una tarjeta apaisada.
CELDA = 9.6                                    # lado de la celda en el suelo
EJE_U = (math.cos(math.radians(22)), math.sin(math.radians(22)))    # semanas
EJE_V = (-math.cos(math.radians(45)), math.sin(math.radians(45)))   # días
HUECO = 0.1           # fracción de celda que queda libre entre columnas
ALTURA_MAX = 62.0
ALTURA_VACIA = 1.6


def peticion(url: str, cuerpo: dict | None = None):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("Falta GITHUB_TOKEN. En local: GITHUB_TOKEN=$(gh auth token) python scripts/actividad.py")
    req = urllib.request.Request(
        url,
        data=json.dumps(cuerpo).encode() if cuerpo else None,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "perfil-jhonttt"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def graphql(consulta: str, **variables) -> dict:
    respuesta = peticion(f"{API}/graphql", {"query": consulta, "variables": variables})
    if "errors" in respuesta:
        raise SystemExit(f"GraphQL: {respuesta['errors']}")
    return respuesta["data"]


# --- datos -----------------------------------------------------------------

def calendario(usuario: str) -> list[tuple[dt.date, int]]:
    d = graphql(
        """query($u: String!) { user(login: $u) { contributionsCollection { contributionCalendar {
             weeks { contributionDays { date contributionCount } } } } } }""",
        u=usuario,
    )
    semanas = d["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(dt.date.fromisoformat(x["date"]), x["contributionCount"]) for s in semanas for x in s["contributionDays"]]


def lenguajes(usuario: str) -> tuple[Counter, int]:
    d = graphql(
        """query($u: String!) { user(login: $u) {
             repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
               nodes { name languages(first: 12) { edges { size node { name } } } } } } }""",
        u=usuario,
    )
    repos = [r for r in d["user"]["repositories"]["nodes"] if r["name"].lower() != usuario.lower()]
    total: Counter = Counter()
    for repo in repos:
        for borde in repo["languages"]["edges"]:
            nombre = borde["node"]["name"]
            total[EQUIVALENCIAS.get(nombre, nombre)] += borde["size"]
    return total, len(repos)


# --- cálculos ----------------------------------------------------------------

def rachas(dias: list[tuple[dt.date, int]]) -> tuple[int, int]:
    larga = actual = 0
    for _, n in dias:
        actual = actual + 1 if n else 0
        larga = max(larga, actual)
    # Hoy sin nada todavía no rompe la racha: el día no ha terminado.
    hasta = dias[:-1] if dias and dias[-1][1] == 0 else dias
    viva = 0
    for _, n in reversed(hasta):
        if not n:
            break
        viva += 1
    return viva, larga


def niveles(dias: list[tuple[dt.date, int]]) -> dict[dt.date, int]:
    """Nivel 0-4 de cada día por cuartiles de los días con actividad, como GitHub."""
    con_algo = sorted(n for _, n in dias if n)
    if not con_algo:
        return {d: 0 for d, _ in dias}
    cortes = [con_algo[int(len(con_algo) * q)] for q in (0.25, 0.5, 0.75)]
    return {d: 0 if n == 0 else 1 + sum(n > c for c in cortes) for d, n in dias}


def sombra(color: str, factor: float) -> str:
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c * factor))) for c in (r, g, b)))


def fecha_corta(d: dt.date) -> str:
    return f"{d.day} {MESES[d.month - 1]}"


# --- la tarjeta --------------------------------------------------------------

def construir(tema: str, dias: list[tuple[dt.date, int]], total_leng: Counter, n_repos: int) -> str:
    t = TEMAS[tema]
    escala = t["escala"].split(",")
    nivel = niveles(dias)
    maximo = max((n for _, n in dias), default=0) or 1

    alto = 512
    desde, hasta = dias[0][0], dias[-1][0]
    total = sum(n for _, n in dias)
    lz = Lienzo(ANCHO, alto, tema, "Actividad en GitHub",
                f"{total} contribuciones entre {fecha_corta(desde)} de {desde.year} y {fecha_corta(hasta)} de {hasta.year}.")
    tarjeta(lz, "04", "Actividad", f"{fecha_corta(desde)} {desde.year} — {fecha_corta(hasta)} {hasta.year}")

    # Origen: la esquina trasera (semana 0, lunes) del suelo.
    ox, oy = 98.0, 76.0 + ALTURA_MAX

    def punto(u: float, v: float, h: float) -> tuple[float, float]:
        return (ox + (u * EJE_U[0] + v * EJE_V[0]) * CELDA,
                oy + (u * EJE_U[1] + v * EJE_V[1]) * CELDA - h)

    def camino(puntos: list[tuple[float, float]]) -> str:
        return "M" + "L".join(f"{f1(x)} {f1(y)}" for x, y in puntos) + "Z"

    inicio = dias[0][0] - dt.timedelta(days=dias[0][0].weekday())  # columnas de lunes a domingo
    columnas = []
    for fecha, n in dias:
        w = (fecha - inicio).days // 7
        d = fecha.weekday()
        h = ALTURA_VACIA if n == 0 else 5 + (ALTURA_MAX - 5) * (n / maximo) ** 0.62
        profundidad = w * EJE_U[1] + d * EJE_V[1]
        columnas.append((profundidad, w, d, h, nivel[fecha], n, fecha))
    columnas.sort()  # de atrás hacia delante: el algoritmo del pintor

    caras = []
    for _, w, d, h, lv, n, fecha in columnas:
        u0, u1 = w + HUECO, w + 1 - HUECO
        v0, v1 = d + HUECO, d + 1 - HUECO
        arriba = lambda hh: [punto(u0, v0, hh), punto(u1, v0, hh), punto(u1, v1, hh), punto(u0, v1, hh)]
        izq = lambda hh: [punto(u0, v1, 0), punto(u1, v1, 0), punto(u1, v1, hh), punto(u0, v1, hh)]
        der = lambda hh: [punto(u1, v0, 0), punto(u1, v1, 0), punto(u1, v1, hh), punto(u1, v0, hh)]
        color = escala[lv]
        tonos = (color, sombra(color, 0.80 if tema == "dark" else 0.86), sombra(color, 0.64 if tema == "dark" else 0.74))
        titulo = f"<title>{fecha.isoformat()}: {n}</title>"
        if n == 0:
            caras.append(
                f'<g>{titulo}<path d="{camino(der(h))}" fill="{tonos[2]}"/><path d="{camino(izq(h))}" fill="{tonos[1]}"/>'
                f'<path d="{camino(arriba(h))}" fill="{tonos[0]}"/></g>'
            )
            continue
        # Crecen al cargar, en diagonal desde la semana más antigua. El retraso va
        # dentro de keyTimes (y no en begin) para que estén a cero desde el
        # principio y no se vean llenas un instante antes de empezar.
        retraso = 0.25 + w * 0.016
        dur = retraso + 0.9
        kt = f"0;{retraso / dur:.3f};1"
        anim = lambda forma: (
            f'<animate attributeName="d" dur="{dur:.2f}s" fill="freeze" calcMode="spline" keyTimes="{kt}" '
            f'keySplines="0 0 1 1;0.2 0.8 0.2 1" values="{camino(forma(0.6))};{camino(forma(0.6))};{camino(forma(h))}"/>'
        )
        caras.append(
            f'<g>{titulo}'
            f'<path d="{camino(der(h))}" fill="{tonos[2]}">{anim(der)}</path>'
            f'<path d="{camino(izq(h))}" fill="{tonos[1]}">{anim(izq)}</path>'
            f'<path d="{camino(arriba(h))}" fill="{tonos[0]}">{anim(arriba)}</path></g>'
        )
    lz.raw("".join(caras))

    # Meses tumbados en el suelo, delante del domingo, siguiendo el eje de las semanas.
    mes_previo = None
    for fecha, _ in dias:
        if fecha.weekday() == 0 and fecha.day <= 7 and fecha.month != mes_previo:
            mes_previo = fecha.month
            w = (fecha - inicio).days // 7
            x, y = punto(w + 0.1, 8.0, 0)
            matriz = f"{EJE_U[0]:.4f} {EJE_U[1]:.4f} {EJE_V[0]:.4f} {EJE_V[1]:.4f} {f1(x)} {f1(y)}"
            lz.raw(lz.texto(0, 0, MESES[fecha.month - 1], "mono-pequeno", "suave", extra=f' transform="matrix({matriz})"'))

    # Cifras, arriba a la derecha: donde el isométrico deja hueco.
    viva, larga = rachas(dias)
    activos = sum(1 for _, n in dias if n)
    mejor_fecha, mejor_n = max(dias, key=lambda x: x[1])
    por_dia = Counter()
    for fecha, n in dias:
        por_dia[fecha.weekday()] += n
    favorito = DIAS[por_dia.most_common(1)[0][0]] if total else "—"
    dias_txt = lambda n: "día" if n == 1 else "días"
    cifras = [
        (f"{total:,}".replace(",", "."), "", "contribuciones"),
        (str(activos), "", "días activos"),
        (str(larga), dias_txt(larga), "racha más larga"),
        (str(viva), dias_txt(viva), "racha actual"),
        (fecha_corta(mejor_fecha), "", f"mejor día · {mejor_n}"),
        (favorito, "", "día más activo"),
    ]
    cx0, cy0 = 612, 84
    for i, (valor, unidad, rotulo) in enumerate(cifras):
        x = cx0 + (i % 2) * 118
        y = cy0 + (i // 2) * 66
        lz.raw(lz.texto(x, y + 24, valor, "cifra-pequena", "tinta"))
        if unidad:
            lz.raw(lz.texto(x + medir(valor, "cifra-pequena") + 5, y + 24, unidad, "pequeno", "suave"))
        lz.raw(lz.texto(x, y + 42, rotulo, "mono-pequeno", "suave"))

    # Leyenda, abajo a la izquierda.
    ly = 330
    lz.raw(lz.texto(40, ly + 9, "menos", "mono-pequeno", "suave"))
    x = 40 + medir("menos", "mono-pequeno") + 8
    for color in escala:
        lz.raw(f'<rect x="{f1(x)}" y="{ly}" width="10" height="10" rx="2" fill="{color}"/>')
        x += 13
    lz.raw(lz.texto(x + 5, ly + 9, "más", "mono-pequeno", "suave"))

    # Lenguajes de los repositorios públicos.
    y0 = 418
    lz.raw(f'<line x1="28" y1="{y0 - 22.5}" x2="{ANCHO - 28}" y2="{y0 - 22.5}" stroke="{t["linea"]}"/>')
    lz.raw(lz.texto(28, y0, "Lenguajes", "seccion", "suave", mayus=True))
    lz.raw(lz.texto(ANCHO - 28, y0, f"{n_repos} repositorios públicos", "meta", "suave", anchor="end"))
    suma = sum(total_leng.values()) or 1
    principales = total_leng.most_common(5)
    resto = suma - sum(v for _, v in principales)
    tramos = principales + ([("Otros", resto)] if resto > 0 else [])
    colores = COLORES_LENGUAJE[tema]
    barra_y, barra_w = y0 + 20, ANCHO - 56
    lz.defs_raw(f'<clipPath id="barra"><rect x="28" y="{barra_y}" width="{barra_w}" height="8" rx="4"/></clipPath>')
    x = 28.0
    segmentos = []
    for i, (nombre, v) in enumerate(tramos):
        ancho = barra_w * v / suma
        segmentos.append(f'<rect x="{f1(x)}" y="{barra_y}" width="{f1(ancho + 0.6)}" height="8" fill="{colores[i % len(colores)]}"/>')
        x += ancho
    lz.raw(f'<g clip-path="url(#barra)">{"".join(segmentos)}</g>')
    x = 28.0
    ly = barra_y + 36
    for i, (nombre, v) in enumerate(tramos):
        porcentaje = f"{100 * v / suma:.1f}%".replace(".", ",")
        lz.raw(f'<circle cx="{f1(x + 4)}" cy="{ly - 4}" r="4" fill="{colores[i % len(colores)]}"/>')
        lz.raw(lz.texto(x + 14, ly, nombre, "pequeno-fuerte", "tinta"))
        x += 14 + medir(nombre, "pequeno-fuerte") + 6
        lz.raw(lz.texto(x, ly, porcentaje, "mono-pequeno", "suave"))
        x += medir(porcentaje, "mono-pequeno") + 24
    return lz.render()


def main() -> None:
    perfil = datos()
    usuario = perfil["usuario"]
    dias = calendario(usuario)
    total, n_repos = lenguajes(usuario)
    guardar("actividad", {tema: construir(tema, dias, total, n_repos) for tema in TEMAS})
    print(f"actividad: {sum(n for _, n in dias)} contribuciones · lenguajes de {n_repos} repositorios")


if __name__ == "__main__":
    main()
