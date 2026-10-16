#!/usr/bin/env python3
"""La tarjeta de actividad, con datos vivos de GitHub:

- el calendario del último año en isométrico: cada día es una columna cuya
  altura sale de lo que hice ese día, y las columnas crecen al cargar. La
  parte de abajo es lo público, en la escala de azules; encima, rayado en
  violeta, lo que hice en repositorios privados;
- unas cifras (total, públicas y privadas, rachas, mejor día);
- el reparto de lenguajes de mis repositorios públicos.

De dónde sale cada cosa:

- Lo público, del calendario de contribuciones tal y como lo ve cualquiera
  (GITHUB_TOKEN, que en el workflow pone Actions).
- Lo privado, de los commits que firmo en mis repositorios privados, en todas
  sus ramas, contados uno a uno (PERFIL_TOKEN, un token personal con permiso de
  lectura sobre ellos). El calendario no sirve para esto: GitHub no cuenta lo
  que no llega a la rama principal y la API no reparte por días lo privado.
  De esos repositorios solo se publica CUÁNTO y CUÁNDO; ni nombres ni mensajes.
  Sin PERFIL_TOKEN, la tarjeta sale como antes, solo con lo público.
- Lo privado a lo que ya no tengo acceso (las prácticas), de
  datos/privadas-extra.json, que se rellena a mano una vez.

En local:
    GITHUB_TOKEN=$(gh auth token) PERFIL_TOKEN=$(gh auth token) python scripts/actividad.py
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import urllib.request
from collections import Counter

from comun import DATOS, TEMAS, Lienzo, datos, es_movil, f1, guardar_versiones, medir, tarjeta

API = "https://api.github.com"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
X = 28

# Lenguajes que linguist confunde: Hack es un dialecto de PHP y en mis
# repositorios son ficheros PHP de toda la vida.
EQUIVALENCIAS = {"Hack": "PHP"}
# Cada lenguaje lleva su color de siempre, el de linguist, que da la propia API.
# "Otros", y algún lenguaje que no tenga color, va en gris.
GRIS = {"dark": "#8b949e", "light": "#6e7781"}

# Geometría de la perspectiva (dimétrica): las semanas avanzan hacia la
# derecha con poca pendiente y los días bajan en diagonal. Más ancha y más baja
# que la isométrica, cabe mejor en una tarjeta apaisada.
EJE_U = (math.cos(math.radians(22)), math.sin(math.radians(22)))    # semanas
EJE_V = (-math.cos(math.radians(45)), math.sin(math.radians(45)))   # días
HUECO = 0.1           # fracción de celda que queda libre entre columnas
ALTURA_VACIA = 1.6


def peticion(url: str, cuerpo: dict | None = None, token: str | None = None):
    token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("Falta GITHUB_TOKEN. En local: GITHUB_TOKEN=$(gh auth token) python scripts/actividad.py")
    req = urllib.request.Request(
        url,
        data=json.dumps(cuerpo).encode() if cuerpo else None,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "perfil-jhonttt"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def graphql(consulta: str, token: str | None = None, **variables) -> dict:
    respuesta = peticion(f"{API}/graphql", {"query": consulta, "variables": variables}, token)
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


def privadas(desde: dt.date) -> Counter | None:
    """Commits míos por día en repositorios privados (todas las ramas, sin repetir).

    Devuelve None si no hay PERFIL_TOKEN: entonces la tarjeta no habla de lo privado.
    """
    token = os.environ.get("PERFIL_TOKEN")
    if not token:
        print("actividad: sin PERFIL_TOKEN, solo la actividad pública")
        return None
    d = graphql(
        """{ viewer { id repositories(first: 100, privacy: PRIVATE, isFork: false,
               ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) {
             nodes { name owner { login } refs(refPrefix: "refs/heads/", first: 100) { nodes { name } } } } } }""",
        token,
    )
    autor = d["viewer"]["id"]
    consulta = """query($o: String!, $n: String!, $rama: String!, $desde: GitTimestamp!, $autor: ID!, $tras: String) {
      repository(owner: $o, name: $n) { ref(qualifiedName: $rama) { target { ... on Commit {
        history(first: 100, after: $tras, since: $desde, author: {id: $autor}) {
          pageInfo { hasNextPage endCursor } nodes { oid authoredDate } } } } } } }"""
    por_dia: Counter = Counter()
    for repo in d["viewer"]["repositories"]["nodes"]:
        vistos: set[str] = set()
        for rama in repo["refs"]["nodes"]:
            tras = None
            while True:
                r = graphql(consulta, token, o=repo["owner"]["login"], n=repo["name"], rama=f"refs/heads/{rama['name']}",
                            desde=f"{desde.isoformat()}T00:00:00Z", autor=autor, tras=tras)
                ref = (r["repository"] or {}).get("ref")
                if not ref:
                    break
                historia = ref["target"]["history"]
                for c in historia["nodes"]:
                    if c["oid"] not in vistos:
                        vistos.add(c["oid"])
                        # La fecha tal y como la apuntó git, con la zona del autor:
                        # es el día en que lo hice, no el de UTC.
                        por_dia[dt.date.fromisoformat(c["authoredDate"][:10])] += 1
                if not historia["pageInfo"]["hasNextPage"]:
                    break
                tras = historia["pageInfo"]["endCursor"]
    por_dia.update(privadas_extra())
    return por_dia


def privadas_extra() -> Counter:
    """Lo de repositorios privados que el token ya no ve, porque perdí el acceso:
    datos/privadas-extra.json, con los commits por día."""
    fichero = DATOS.parent / "privadas-extra.json"
    if not fichero.exists():
        return Counter()
    dias = json.loads(fichero.read_text(encoding="utf-8"))["dias"]
    return Counter({dt.date.fromisoformat(d): n for d, n in dias.items()})


def lenguajes(usuario: str) -> tuple[Counter, int, dict[str, str]]:
    d = graphql(
        """query($u: String!) { user(login: $u) {
             repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
               nodes { name languages(first: 12) { edges { size node { name color } } } } } } }""",
        u=usuario,
    )
    repos = [r for r in d["user"]["repositories"]["nodes"] if r["name"].lower() != usuario.lower()]
    total: Counter = Counter()
    colores: dict[str, str] = {}
    for repo in repos:
        for borde in repo["languages"]["edges"]:
            nombre = borde["node"]["name"]
            if borde["node"]["color"]:
                colores.setdefault(nombre, borde["node"]["color"])
            total[EQUIVALENCIAS.get(nombre, nombre)] += borde["size"]
    return total, len(repos), colores


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


def mezcla(a: str, b: str, t: float) -> str:
    """Color entre a (t=0) y b (t=1)."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#{:02x}{:02x}{:02x}".format(*(round(x + (y - x) * t) for x, y in zip(ca, cb)))


def fecha_corta(d: dt.date) -> str:
    return f"{d.day} {MESES[d.month - 1]}"


def numero(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# --- la tarjeta --------------------------------------------------------------

def _rayado(lz: Lienzo, tema: str) -> None:
    """Los rayados de lo privado, uno por cara de la columna (arriba, izquierda, derecha).

    Del mismo azul que lo público, para que se lea como la misma actividad, pero
    a rayas: rayas del azul de acento sobre un azul oscuro (o claro, en el tema
    claro), mientras que lo público es macizo.
    """
    t = lz.t
    claro = tema == "light"
    fondo = mezcla(t["acento"], t["fondo"], 0.78 if claro else 0.72)
    raya = t["acento"]
    factores = (1.0, 0.86, 0.74) if claro else (1.0, 0.8, 0.64)
    for k, f in enumerate(factores):
        lz.defs_raw(
            f'<pattern id="priv{k}" width="3.4" height="3.4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="3.4" height="3.4" fill="{sombra(fondo, f)}"/><rect width="1.4" height="3.4" fill="{sombra(raya, f)}"/></pattern>'
        )


def _muestra_privada(lz: Lienzo, x: float, y: float, lado: float = 10) -> None:
    lz.raw(f'<rect x="{f1(x)}" y="{f1(y)}" width="{lado}" height="{lado}" rx="2" fill="url(#priv0)" '
           f'stroke="{lz.t["acento"]}" stroke-opacity="0.5" stroke-width="0.8"/>')


def construir(tema: str, ancho: float, publicas: list[tuple[dt.date, int]], priv: Counter | None,
              total_leng: Counter, n_repos: int, colores_leng: dict[str, str]) -> str:
    t = TEMAS[tema]
    movil = es_movil(ancho)
    escala = t["escala"].split(",")
    con_privadas = priv is not None
    priv = priv or Counter()
    dias = [(d, n + priv.get(d, 0)) for d, n in publicas]   # el total de cada día
    nivel = niveles(publicas)
    maximo = max((n for _, n in dias), default=0) or 1

    # La composición. En escritorio, el calendario a la izquierda y las cifras
    # a su derecha; en móvil, las cifras arriba y el calendario, más pequeño, debajo.
    if movil:
        celda, altura_max = 7.0, 46.0
        y_cifras, paso_cifras, col_cifras = 76, 52, (ancho - 2 * X) / 2
        x_cifras = X
        oy = y_cifras + 4 * paso_cifras - 6 + altura_max
        ox = X + 7 * celda * -EJE_V[0] + 6
        ly = oy + 53 * celda * EJE_U[1] + 7 * celda * EJE_V[1] + 36
    else:
        celda, altura_max = 9.6, 62.0
        y_cifras, paso_cifras, col_cifras = 76 if con_privadas else 84, 58 if con_privadas else 66, 118
        x_cifras = 612
        ox, oy = 98.0, 76.0 + altura_max
        ly = 330

    # Los lenguajes, repartidos en líneas (en escritorio caben en una).
    suma = sum(total_leng.values()) or 1
    principales = total_leng.most_common(5)
    resto = suma - sum(v for _, v in principales)
    tramos = principales + ([("Otros", resto)] if resto > 0 else [])
    filas_leng: list[list[tuple[str, str, int]]] = [[]]
    xx = 0.0
    for i, (nombre, v) in enumerate(tramos):
        porcentaje = f"{100 * v / suma:.1f}%".replace(".", ",")
        w = 14 + medir(nombre, "pequeno-fuerte") + 6 + medir(porcentaje, "mono-pequeno")
        if filas_leng[-1] and xx + w > ancho - 2 * X:
            filas_leng.append([])
            xx = 0.0
        filas_leng[-1].append((nombre, porcentaje, i))
        xx += w + 24
    y0_leng = ly + 66 if movil else 418
    alto = y0_leng + 20 + 36 + 24 * (len(filas_leng) - 1) + 28 + (8 if movil else 0)

    desde, hasta = dias[0][0], dias[-1][0]
    total = sum(n for _, n in dias)
    total_priv = sum(priv.get(d, 0) for d, _ in publicas)
    desc = f"{total} contribuciones entre {fecha_corta(desde)} de {desde.year} y {fecha_corta(hasta)} de {hasta.year}"
    if con_privadas:
        desc += f", {total_priv} de ellas en repositorios privados"
    lz = Lienzo(ancho, alto, tema, "Actividad en GitHub", desc + ".")
    tarjeta(lz, "04", "Actividad", f"{fecha_corta(desde)} {desde.year} — {fecha_corta(hasta)} {hasta.year}")
    if con_privadas:
        _rayado(lz, tema)

    # Origen: la esquina trasera (semana 0, lunes) del suelo.
    def punto(u: float, v: float, h: float) -> tuple[float, float]:
        return (ox + (u * EJE_U[0] + v * EJE_V[0]) * celda,
                oy + (u * EJE_U[1] + v * EJE_V[1]) * celda - h)

    def camino(puntos: list[tuple[float, float]]) -> str:
        return "M" + "L".join(f"{f1(x)} {f1(y)}" for x, y in puntos) + "Z"

    inicio = dias[0][0] - dt.timedelta(days=dias[0][0].weekday())  # columnas de lunes a domingo
    columnas = []
    for (fecha, n_pub), (_, n) in zip(publicas, dias):
        w = (fecha - inicio).days // 7
        d = fecha.weekday()
        h = ALTURA_VACIA if n == 0 else 5 + (altura_max - 5) * (n / maximo) ** 0.62
        profundidad = w * EJE_U[1] + d * EJE_V[1]
        columnas.append((profundidad, w, d, h, nivel[fecha], n_pub, n - n_pub, fecha))
    columnas.sort()  # de atrás hacia delante: el algoritmo del pintor

    caras = []
    for _, w, d, h, lv, n_pub, n_priv, fecha in columnas:
        u0, u1 = w + HUECO, w + 1 - HUECO
        v0, v1 = d + HUECO, d + 1 - HUECO
        arriba = lambda b, hh: [punto(u0, v0, hh), punto(u1, v0, hh), punto(u1, v1, hh), punto(u0, v1, hh)]
        izq = lambda b, hh: [punto(u0, v1, b), punto(u1, v1, b), punto(u1, v1, hh), punto(u0, v1, hh)]
        der = lambda b, hh: [punto(u1, v0, b), punto(u1, v1, b), punto(u1, v1, hh), punto(u1, v0, hh)]
        color = escala[lv]
        tonos = (color, sombra(color, 0.80 if tema == "dark" else 0.86), sombra(color, 0.64 if tema == "dark" else 0.74))
        if con_privadas:
            titulo = f"<title>{fecha.isoformat()}: {n_pub} públicas · {n_priv} privadas</title>"
        else:
            titulo = f"<title>{fecha.isoformat()}: {n_pub}</title>"
        if n_pub + n_priv == 0:
            caras.append(
                f'<g>{titulo}<path d="{camino(der(0, h))}" fill="{tonos[2]}"/><path d="{camino(izq(0, h))}" fill="{tonos[1]}"/>'
                f'<path d="{camino(arriba(0, h))}" fill="{tonos[0]}"/></g>'
            )
            continue
        # Crecen al cargar, en diagonal desde la semana más antigua. El retraso va
        # dentro de keyTimes (y no en begin) para que estén a cero desde el
        # principio y no se vean llenas un instante antes de empezar.
        retraso = 0.25 + w * 0.016
        dur = retraso + 0.9
        kt = f"0;{retraso / dur:.3f};1"

        def cara(forma, b, hh, relleno):
            ini = camino(forma(0.6, 0.6))
            return (
                f'<path d="{camino(forma(b, hh))}" fill="{relleno}">'
                f'<animate attributeName="d" dur="{dur:.2f}s" fill="freeze" calcMode="spline" keyTimes="{kt}" '
                f'keySplines="0 0 1 1;0.2 0.8 0.2 1" values="{ini};{ini};{camino(forma(b, hh))}"/></path>'
            )

        # Lo público abajo y lo privado encima, en la misma columna.
        h_pub = h * n_pub / (n_pub + n_priv)
        partes = [titulo]
        if n_pub:
            partes += [cara(der, 0, h_pub, tonos[2]), cara(izq, 0, h_pub, tonos[1])]
            if not n_priv:
                partes.append(cara(arriba, 0, h_pub, tonos[0]))
        if n_priv:
            partes += [cara(der, h_pub, h, "url(#priv2)"), cara(izq, h_pub, h, "url(#priv1)"),
                       cara(arriba, h_pub, h, "url(#priv0)")]
        caras.append(f'<g>{"".join(partes)}</g>')
    lz.raw("".join(caras))

    # Meses tumbados en el suelo, delante del domingo, siguiendo el eje de las semanas.
    mes_previo = None
    escala_texto = 0.85 if movil else 1
    for fecha, _ in dias:
        if fecha.weekday() == 0 and fecha.day <= 7 and fecha.month != mes_previo:
            mes_previo = fecha.month
            w = (fecha - inicio).days // 7
            x, y = punto(w + 0.1, 8.0, 0)
            matriz = (f"{EJE_U[0] * escala_texto:.4f} {EJE_U[1] * escala_texto:.4f} "
                      f"{EJE_V[0] * escala_texto:.4f} {EJE_V[1] * escala_texto:.4f} {f1(x)} {f1(y)}")
            lz.raw(lz.texto(0, 0, MESES[fecha.month - 1], "mono-pequeno", "suave", extra=f' transform="matrix({matriz})"'))

    # Cifras: donde el isométrico deja hueco en escritorio, o arriba en móvil.
    viva, larga = rachas(dias)
    activos = sum(1 for _, n in dias if n)
    mejor_fecha, mejor_n = max(dias, key=lambda x: x[1])
    por_dia = Counter()
    for fecha, n in dias:
        por_dia[fecha.weekday()] += n
    favorito = DIAS[por_dia.most_common(1)[0][0]] if total else "—"
    dias_txt = lambda n: "día" if n == 1 else "días"
    cifras = [
        (numero(total), "", "contribuciones", None),
        (str(activos), "", "días activos", None),
    ]
    if con_privadas:
        cifras += [
            (numero(total - total_priv), "", "públicas", "publica"),
            (numero(total_priv), "", "privadas", "privada"),
        ]
    cifras += [
        (str(larga), dias_txt(larga), "racha más larga", None),
        (str(viva), dias_txt(viva), "racha actual", None),
        (fecha_corta(mejor_fecha), "", f"mejor día · {mejor_n}", None),
        (favorito, "", "día más activo", None),
    ]
    for i, (valor, unidad, rotulo, muestra) in enumerate(cifras):
        x = x_cifras + (i % 2) * col_cifras
        y = y_cifras + (i // 2) * paso_cifras
        lz.raw(lz.texto(x, y + 24, valor, "cifra-pequena", "tinta"))
        if unidad:
            lz.raw(lz.texto(x + medir(valor, "cifra-pequena") + 5, y + 24, unidad, "pequeno", "suave"))
        xr = x
        if muestra == "publica":
            lz.raw(f'<rect x="{f1(x)}" y="{y + 34}" width="9" height="9" rx="2" fill="{escala[-1]}"/>')
            xr += 14
        elif muestra == "privada":
            _muestra_privada(lz, x, y + 34, 9)
            xr += 14
        lz.raw(lz.texto(xr, y + 42, rotulo, "mono-pequeno", "suave"))

    # Leyenda, bajo el calendario.
    x = 40 if not movil else X
    lz.raw(lz.texto(x, ly + 9, "menos", "mono-pequeno", "suave"))
    x += medir("menos", "mono-pequeno") + 8
    for color in escala:
        lz.raw(f'<rect x="{f1(x)}" y="{ly}" width="10" height="10" rx="2" fill="{color}"/>')
        x += 13
    lz.raw(lz.texto(x + 5, ly + 9, "más", "mono-pequeno", "suave"))
    if con_privadas:
        x += 5 + medir("más", "mono-pequeno") + 22
        _muestra_privada(lz, x, ly)
        lz.raw(lz.texto(x + 16, ly + 9, "privadas", "mono-pequeno", "suave"))

    # Lenguajes de los repositorios públicos.
    y0 = y0_leng
    lz.raw(f'<line x1="{X}" y1="{y0 - 22.5}" x2="{ancho - X}" y2="{y0 - 22.5}" stroke="{t["linea"]}"/>')
    lz.raw(lz.texto(X, y0, "Lenguajes", "seccion", "suave", mayus=True))
    lz.raw(lz.texto(ancho - X, y0, f"{n_repos} repos públicos" if movil else f"{n_repos} repositorios públicos",
                    "meta", "suave", anchor="end"))
    colores = [colores_leng.get(nombre, GRIS[tema]) for nombre, _ in tramos]
    barra_y, barra_w = y0 + 20, ancho - 2 * X
    lz.defs_raw(f'<clipPath id="barra"><rect x="{X}" y="{barra_y}" width="{barra_w}" height="8" rx="4"/></clipPath>')
    x = float(X)
    segmentos = []
    for i, (nombre, v) in enumerate(tramos):
        ancho_tramo = barra_w * v / suma
        segmentos.append(f'<rect x="{f1(x)}" y="{barra_y}" width="{f1(ancho_tramo + 0.6)}" height="8" fill="{colores[i]}"/>')
        x += ancho_tramo
    lz.raw(f'<g clip-path="url(#barra)">{"".join(segmentos)}</g>')
    ly = barra_y + 36
    for fila in filas_leng:
        x = float(X)
        for nombre, porcentaje, i in fila:
            lz.raw(f'<circle cx="{f1(x + 4)}" cy="{ly - 4}" r="4" fill="{colores[i]}"/>')
            lz.raw(lz.texto(x + 14, ly, nombre, "pequeno-fuerte", "tinta"))
            x += 14 + medir(nombre, "pequeno-fuerte") + 6
            lz.raw(lz.texto(x, ly, porcentaje, "mono-pequeno", "suave"))
            x += medir(porcentaje, "mono-pequeno") + 24
        ly += 24
    return lz.render()


def main() -> None:
    perfil = datos()
    usuario = perfil["usuario"]
    dias = calendario(usuario)
    priv = privadas(dias[0][0])
    total, n_repos, colores = lenguajes(usuario)
    guardar_versiones("actividad", lambda tema, ancho: construir(tema, ancho, dias, priv, total, n_repos, colores))
    texto = f"actividad: {sum(n for _, n in dias)} contribuciones públicas"
    if priv is not None:
        texto += f" y {sum(priv.get(d, 0) for d, _ in dias)} commits privados"
    print(f"{texto} · lenguajes de {n_repos} repositorios")


if __name__ == "__main__":
    main()
