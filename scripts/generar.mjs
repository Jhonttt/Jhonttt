// Genera los SVG del perfil (banner y botones de contacto) en versión clara y
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
  const lema = "> git commit -m \"aprendiendo algo nuevo\"";
  // Ancho aproximado del monoespaciado a 15 px, para la animación de tecleo.
  const anchoLema = Math.ceil(lema.length * 8.6);

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="titulo">
  <title id="titulo">Juan Atahona — Estudiante de 2º de DAM</title>
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
  <text x="56" y="164" font-family="${SANS}" font-size="22" fill="${t.suave}">Estudiante de <tspan fill="${t.acento}" font-weight="600">2º de DAM</tspan> · España</text>

  <g clip-path="url(#tecleo)">
    <text x="56" y="214" font-family="${MONO}" font-size="15" fill="${t.texto}">${esc(lema)}</text>
  </g>
  <g class="cursor"><rect class="parpadeo" x="59" y="200" width="8" height="18" fill="${t.acento}"/></g>

  <rect x="0.5" y="0.5" width="${W - 1}" height="${H - 1}" rx="14" fill="none" stroke="${t.borde}"/>
</svg>
`;
}

// Botones de contacto: el icono es un trazo de 16x16 para que no dependa de
// ninguna fuente de iconos.
const botones = [
  {
    archivo: "portfolio",
    texto: "juanatahona.dev",
    icono: '<circle cx="8" cy="8" r="6.5"/><path d="M1.5 8h13M8 1.5c2 2 2.8 4.2 2.8 6.5S10 12.5 8 14.5M8 1.5C6 3.5 5.2 5.7 5.2 8S6 12.5 8 14.5"/>',
  },
  {
    archivo: "linkedin",
    texto: "LinkedIn",
    icono: '<rect x="1.5" y="1.5" width="13" height="13" rx="2.5"/><path d="M5 7v4.5M5 4.6v.1M8 11.5V7m0 2.2c0-1.4.9-2.2 2-2.2s1.8.8 1.8 2.2v2.3"/>',
  },
  {
    archivo: "email",
    texto: "juan.atahona4@gmail.com",
    icono: '<rect x="1.5" y="3" width="13" height="10" rx="2"/><path d="m2 4 6 5 6-5"/>',
  },
];

function boton(b, t) {
  const H = 36;
  const W = Math.round(b.texto.length * 7.9 + 62);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="t">
  <title id="t">${esc(b.texto)}</title>
  <rect x="0.5" y="0.5" width="${W - 1}" height="${H - 1}" rx="18" fill="${t.fondo}" stroke="${t.borde}"/>
  <g transform="translate(16 10)" fill="none" stroke="${t.acento}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">${b.icono}</g>
  <text x="42" y="23" font-family="${SANS}" font-size="14" fill="${t.texto}">${esc(b.texto)}</text>
</svg>
`;
}

for (const [nombre, t] of Object.entries(temas)) {
  writeFileSync(join(salida, `banner-${nombre}.svg`), banner(t));
  for (const b of botones) writeFileSync(join(salida, `${b.archivo}-${nombre}.svg`), boton(b, t));
}
console.log("SVG generados en", salida);
