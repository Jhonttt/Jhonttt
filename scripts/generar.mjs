// Genera los SVG del perfil (banner y tarjetas de proyecto) en versión clara y
// oscura a partir de un solo origen. Uso: node scripts/generar.mjs
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..");
const salida = join(raiz, "assets");
mkdirSync(salida, { recursive: true });

// El fondo oscuro es el de GitHub (#0d1117) para que el SVG se funda con la
// página; el claro, blanco puro por lo mismo.
const temas = {
  light: {
    fondo: "#ffffff",
    superficie: "#f6f8fa",
    borde: "#d0d7de",
    texto: "#1f2328",
    suave: "#59636e",
    tenue: "#d8dee4",
    acento: "#0f766e",
  },
  dark: {
    fondo: "#0d1117",
    superficie: "#151b23",
    borde: "#30363d",
    texto: "#f0f6fc",
    suave: "#9198a1",
    tenue: "#21262d",
    acento: "#2dd4bf",
  },
};

const SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif";
const MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace";

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function banner(t) {
  const W = 960;
  const H = 280;
  const cx = 790;
  const cy = 140;
  const lema = "> construyendo gachamon.ink";
  // Ancho aproximado del monoespaciado a 15 px, para la animación de tecleo.
  const anchoLema = Math.ceil(lema.length * 8.6);

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="titulo">
  <title id="titulo">Juan Atahona — Desarrollador fullstack</title>
  <defs>
    <pattern id="puntos" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="1" fill="${t.tenue}"/>
    </pattern>
    <linearGradient id="desvanecer" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0" stop-color="#fff" stop-opacity="0"/>
      <stop offset="0.55" stop-color="#fff" stop-opacity="0.15"/>
      <stop offset="1" stop-color="#fff" stop-opacity="1"/>
    </linearGradient>
    <mask id="mascara"><rect width="${W}" height="${H}" fill="url(#desvanecer)"/></mask>
    <clipPath id="marco"><rect x="0.5" y="0.5" width="${W - 1}" height="${H - 1}" rx="14"/></clipPath>
    <clipPath id="tecleo"><rect class="tecleo" x="56" y="196" width="${anchoLema}" height="26"/></clipPath>
  </defs>
  <style>
    .orbita { transform-origin: ${cx}px ${cy}px; animation: girar linear infinite; }
    .o1 { animation-duration: 28s; }
    .o2 { animation-duration: 44s; animation-direction: reverse; }
    .o3 { animation-duration: 64s; }
    /* El retraso negativo hace que arranque con la frase ya escrita. */
    .tecleo { animation: teclear 7s steps(${lema.length}, end) -3.5s infinite; }
    .cursor { animation: seguir 7s steps(${lema.length}, end) -3.5s infinite; }
    .parpadeo { animation: parpadeo 1s steps(1, end) infinite; }
    @keyframes girar { to { transform: rotate(360deg); } }
    @keyframes teclear { 0% { width: 0; } 45%, 85% { width: ${anchoLema}px; } 100% { width: 0; } }
    @keyframes seguir { 0% { transform: translateX(0); } 45%, 85% { transform: translateX(${anchoLema}px); } 100% { transform: translateX(0); } }
    @keyframes parpadeo { 50% { opacity: 0; } }
    @media (prefers-reduced-motion: reduce) {
      .orbita, .tecleo, .cursor, .parpadeo { animation: none; }
      .cursor { transform: translateX(${anchoLema}px); }
    }
  </style>

  <g clip-path="url(#marco)">
    <rect width="${W}" height="${H}" fill="${t.fondo}"/>
    <rect width="${W}" height="${H}" fill="url(#puntos)" mask="url(#mascara)"/>

    <g fill="none" stroke="${t.borde}" stroke-width="1">
      <circle cx="${cx}" cy="${cy}" r="52"/>
      <circle cx="${cx}" cy="${cy}" r="88"/>
      <circle cx="${cx}" cy="${cy}" r="124" stroke-dasharray="2 6"/>
    </g>
    <circle cx="${cx}" cy="${cy}" r="6" fill="${t.acento}"/>
    <circle cx="${cx}" cy="${cy}" r="16" fill="none" stroke="${t.acento}" stroke-opacity="0.35"/>
    <g class="orbita o1"><circle cx="${cx + 52}" cy="${cy}" r="4" fill="${t.texto}"/></g>
    <g class="orbita o2"><circle cx="${cx}" cy="${cy - 88}" r="5" fill="${t.acento}"/></g>
    <g class="orbita o3"><circle cx="${cx - 124}" cy="${cy}" r="3.5" fill="${t.suave}"/></g>
  </g>

  <text x="56" y="70" font-family="${MONO}" font-size="14" fill="${t.suave}">~/juan-atahona</text>
  <text x="54" y="128" font-family="${SANS}" font-size="52" font-weight="700" fill="${t.texto}" letter-spacing="-1.2">Juan Atahona</text>
  <text x="56" y="164" font-family="${SANS}" font-size="22" fill="${t.suave}">Desarrollador <tspan fill="${t.acento}" font-weight="600">fullstack</tspan> · España</text>

  <g clip-path="url(#tecleo)">
    <text x="56" y="214" font-family="${MONO}" font-size="15" fill="${t.texto}">${esc(lema)}</text>
  </g>
  <g class="cursor"><rect class="parpadeo" x="59" y="200" width="8" height="18" fill="${t.acento}"/></g>

  <rect x="0.5" y="0.5" width="${W - 1}" height="${H - 1}" rx="14" fill="none" stroke="${t.borde}"/>
</svg>
`;
}

// Las descripciones van ya partidas en líneas: SVG no sabe ajustar texto.
const proyectos = [
  {
    archivo: "gachamon",
    nombre: "Gachamón",
    enlace: "gachamon.ink",
    lineas: ["Arcade Pokémon para el navegador: modo aventura", "roguelike, duelos 1v1 en tiempo real y gachapón."],
    stack: ["Next 16", "React 19", "Postgres", "GSAP"],
  },
  {
    archivo: "serena",
    nombre: "Proyecto Serena",
    enlace: "serena-app",
    lineas: ["Portal para estudiantes con dificultades emocionales,", "con roles, JWT y datos sensibles cifrados."],
    stack: ["React", "Node.js", "Sequelize", "WordPress"],
  },
  {
    archivo: "project-hub",
    nombre: "Project Hub",
    enlace: "proyecto-intermodular",
    lineas: ["Web para que un centro educativo publique", "y gestione los trabajos de sus estudiantes."],
    stack: ["Angular", "Laravel", "Blade", "Bootstrap"],
  },
  {
    archivo: "incidencias",
    nombre: "Dashboard de incidencias",
    enlace: "di-dashboard",
    lineas: ["Escritorio para gestionar incidencias con", "indicadores reactivos, búsqueda y filtros."],
    stack: ["Java", "JavaFX", "FXML", "Maven"],
  },
];

function tarjeta(p, t) {
  const W = 468;
  const H = 176;
  const anchoChar = 7.3; // monoespaciado a 12 px
  let x = 24;
  const chips = p.stack
    .map((s) => {
      const w = Math.round(s.length * anchoChar + 20);
      const chip = `<g transform="translate(${x} 128)"><rect width="${w}" height="24" rx="12" fill="${t.superficie}" stroke="${t.borde}"/><text x="${w / 2}" y="16" text-anchor="middle" font-family="${MONO}" font-size="12" fill="${t.suave}">${esc(s)}</text></g>`;
      x += w + 8;
      return chip;
    })
    .join("\n    ");

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="t">
  <title id="t">${esc(p.nombre)}</title>
  <rect x="0.5" y="0.5" width="${W - 1}" height="${H - 1}" rx="12" fill="${t.fondo}" stroke="${t.borde}"/>
  <circle cx="30" cy="38" r="5" fill="${t.acento}"/>
  <text x="46" y="45" font-family="${SANS}" font-size="20" font-weight="600" fill="${t.texto}">${esc(p.nombre)}</text>
  <text x="${W - 24}" y="44" text-anchor="end" font-family="${MONO}" font-size="12" fill="${t.suave}">${esc(p.enlace)} ↗</text>
  <text font-family="${SANS}" font-size="14.5" fill="${t.suave}">
    ${p.lineas.map((l, i) => `<tspan x="24" y="${84 + i * 22}">${esc(l)}</tspan>`).join("\n    ")}
  </text>
  <g>
    ${chips}
  </g>
</svg>
`;
}

for (const [nombre, t] of Object.entries(temas)) {
  writeFileSync(join(salida, `banner-${nombre}.svg`), banner(t));
  for (const p of proyectos) writeFileSync(join(salida, `${p.archivo}-${nombre}.svg`), tarjeta(p, t));
}
console.log("SVG generados en", salida);
