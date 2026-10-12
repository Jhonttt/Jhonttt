#!/usr/bin/env python3
"""Tarjetas con datos vivos de GitHub: el calendario del último año y los
lenguajes de mis repositorios.

Solo biblioteca estándar. Necesita un token en GITHUB_TOKEN (en el workflow
lo pone Actions; en local vale `GITHUB_TOKEN=$(gh auth token)`).

Uso: python scripts/actividad.py
"""

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.request
from collections import Counter

from comun import MONO, SANS, TEMAS, datos, esc, guardar, marco

ANCHO = 1200
API = "https://api.github.com"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
# Paleta propia para los lenguajes, no la de linguist: seis tonos que conviven
# con el acento en los dos temas.
COLORES_LENGUAJE = ["#6ea8fe", "#3fb6a8", "#b392f0", "#e3b341", "#f0883e", "#8b949e", "#545d68"]


def peticion(url: str, cuerpo: dict | None = None) -> dict | list:
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
    datos_ = graphql(
        """query($u: String!) { user(login: $u) { contributionsCollection { contributionCalendar {
             weeks { contributionDays { date contributionCount } } } } } }""",
        u=usuario,
    )
    semanas = datos_["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(dt.date.fromisoformat(d["date"]), d["contributionCount"]) for s in semanas for d in s["contributionDays"]]


def lenguajes(usuario: str, privados: bool) -> tuple[Counter, int]:
    privacidad = "" if privados else ", privacy: PUBLIC"
    datos_ = graphql(
        f"""query($u: String!) {{ user(login: $u) {{
             repositories(first: 100, ownerAffiliations: OWNER, isFork: false{privacidad}) {{
               nodes {{ name languages(first: 12) {{ edges {{ size node {{ name }} }} }} }} }} }} }}""",
        u=usuario,
    )
    total: Counter = Counter()
    # El repositorio del perfil no cuenta.
    repos = [r for r in datos_["user"]["repositories"]["nodes"] if r["name"].lower() != usuario.lower()]
    for repo in repos:
        for borde in repo["languages"]["edges"]:
            total[borde["node"]["name"]] += borde["size"]
    return total, len(repos)


# --- cálculos ----------------------------------------------------------------

def rachas(dias: list[tuple[dt.date, int]]) -> tuple[int, int]:
    larga = actual = 0
    for _, n in dias:
        actual = actual + 1 if n else 0
        larga = max(larga, actual)
    # La racha actual no se rompe por el día de hoy si aún no ha habido nada.
    hoy = list(dias)
    if hoy and hoy[-1][1] == 0:
        hoy = hoy[:-1]
    viva = 0
    for _, n in reversed(hoy):
        if not n:
            break
        viva += 1
    return viva, larga


def niveles(dias: list[tuple[dt.date, int]]) -> dict[dt.date, int]:
    """Nivel 0-4 de cada día por cuartiles de los días con actividad, como GitHub."""
    con_algo = sorted(n for _, n in dias if n)
    if not con_algo:
        return {d: 0 for d, _ in dias}
    corte = [con_algo[int(len(con_algo) * q)] for q in (0.25, 0.5, 0.75)]
    return {d: 0 if n == 0 else 1 + sum(n > c for c in corte) for d, n in dias}


# --- tarjetas ----------------------------------------------------------------

def tarjeta_calendario(t: dict[str, str], dias: list[tuple[dt.date, int]]) -> str:
    escala = t["escala"].split(",")
    nivel = niveles(dias)
    celda, hueco = 13, 3
    x0, y0 = 84, 134
    partes = []
    # Columnas de lunes a domingo (GitHub empieza en domingo; aquí, en lunes).
    inicio = dias[0][0] - dt.timedelta(days=dias[0][0].weekday())
    mes_previo = None
    for fecha, n in dias:
        col = (fecha - inicio).days // 7
        fila = fecha.weekday()
        x = x0 + col * (celda + hueco)
        y = y0 + fila * (celda + hueco)
        partes.append(f'<rect x="{x}" y="{y}" width="{celda}" height="{celda}" rx="3" fill="{escala[nivel[fecha]]}"><title>{fecha.isoformat()}: {n}</title></rect>')
        if fila == 0 and fecha.month != mes_previo and fecha.day <= 7:
            partes.append(f'<text x="{x}" y="{y0 - 14}" font-family="{MONO}" font-size="15" fill="{t["suave"]}">{MESES[fecha.month - 1]}</text>')
            mes_previo = fecha.month
    for fila, letra in ((0, "lun"), (2, "mié"), (4, "vie")):
        partes.append(f'<text x="36" y="{y0 + fila * (celda + hueco) + 12}" font-family="{MONO}" font-size="14" fill="{t["suave"]}">{letra}</text>')

    # Leyenda de la escala.
    ly = y0 + 7 * (celda + hueco) + 26
    partes.append(f'<text x="{x0}" y="{ly + 12}" font-family="{MONO}" font-size="14" fill="{t["suave"]}">menos</text>')
    for i, color in enumerate(escala):
        partes.append(f'<rect x="{x0 + 58 + i * 18}" y="{ly}" width="13" height="13" rx="3" fill="{color}"/>')
    partes.append(f'<text x="{x0 + 58 + 5 * 18 + 6}" y="{ly + 12}" font-family="{MONO}" font-size="14" fill="{t["suave"]}">más</text>')

    total = sum(n for _, n in dias)
    viva, larga = rachas(dias)
    por_dia = Counter()
    for fecha, n in dias:
        por_dia[fecha.weekday()] += n
    favorito = DIAS[por_dia.most_common(1)[0][0]] if total else "—"
    cifras = [(f"{total:,}".replace(",", "."), "contribuciones"), (f"{viva} d", "racha actual"), (f"{larga} d", "racha más larga"), (favorito, "día que más")]
    # Cifras en columna a la derecha del calendario: valor grande y rótulo al lado.
    for i, (valor, rotulo) in enumerate(cifras):
        y = 128 + i * 46
        partes.append(
            f'<text x="968" y="{y}" font-family="{SANS}" font-size="24" font-weight="600" fill="{t["tinta"]}">{esc(valor)}</text>'
            f'<text x="968" y="{y + 18}" font-family="{MONO}" font-size="13" fill="{t["suave"]}">{esc(rotulo)}</text>'
        )
    partes.append(f'<line x1="944" y1="104" x2="944" y2="{ly + 14}" stroke="{t["linea"]}"/>')

    alto = max(ly + 50, 128 + 3 * 46 + 48)
    desde, hasta = dias[0][0], dias[-1][0]
    meta = f"{desde.day} {MESES[desde.month - 1]} {desde.year} — {hasta.day} {MESES[hasta.month - 1]} {hasta.year}"
    return marco(t, ANCHO, alto, "03", "El último año", meta, "".join(partes),
                 desc=f"Calendario de contribuciones: {total} en el último año, racha más larga de {larga} días.")


def tarjeta_lenguajes(t: dict[str, str], total: Counter, n_repos: int) -> str:
    suma = sum(total.values()) or 1
    principales = total.most_common(6)
    resto = suma - sum(v for _, v in principales)
    tramos = [(nombre, v) for nombre, v in principales] + ([("Otros", resto)] if resto > 0 else [])

    x0, ancho_barra, y = 36, ANCHO - 72, 118
    partes = [f'<clipPath id="barra"><rect x="{x0}" y="{y}" width="{ancho_barra}" height="14" rx="7"/></clipPath><g clip-path="url(#barra)">']
    x = x0
    for i, (nombre, v) in enumerate(tramos):
        w = ancho_barra * v / suma
        partes.append(f'<rect x="{x:.1f}" y="{y}" width="{w + 0.5:.1f}" height="14" fill="{COLORES_LENGUAJE[i % len(COLORES_LENGUAJE)]}"/>')
        x += w
    partes.append("</g>")

    columnas = 4
    ancho_col = ancho_barra / columnas
    for i, (nombre, v) in enumerate(tramos):
        cx = x0 + (i % columnas) * ancho_col
        cy = y + 64 + (i // columnas) * 44
        partes.append(
            f'<circle cx="{cx + 7}" cy="{cy - 7}" r="7" fill="{COLORES_LENGUAJE[i % len(COLORES_LENGUAJE)]}"/>'
            f'<text x="{cx + 24}" y="{cy}" font-family="{SANS}" font-size="20" fill="{t["tinta"]}">{esc(nombre)}'
            f'<tspan dx="10" font-family="{MONO}" font-size="16" fill="{t["suave"]}">{100 * v / suma:.1f}%</tspan></text>'
        )
    filas = (len(tramos) + columnas - 1) // columnas
    alto = y + 64 + filas * 44
    return marco(t, ANCHO, alto, "04", "En qué escribo", f"{n_repos} repositorios", "".join(partes),
                 desc="Reparto de lenguajes en mis repositorios, por bytes de código.")


def main() -> None:
    perfil = datos()
    usuario = perfil["usuario"]
    dias = calendario(usuario)
    total, n_repos = lenguajes(usuario, perfil.get("lenguajes_privados", False))
    guardar("actividad", {tema: tarjeta_calendario(t, dias) for tema, t in TEMAS.items()})
    guardar("lenguajes", {tema: tarjeta_lenguajes(t, total, n_repos) for tema, t in TEMAS.items()})
    print(f"actividad: {sum(n for _, n in dias)} contribuciones · lenguajes: {len(total)} en {n_repos} repositorios")


if __name__ == "__main__":
    main()
