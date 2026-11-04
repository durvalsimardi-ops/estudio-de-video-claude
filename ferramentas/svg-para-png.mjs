#!/usr/bin/env node
// Transforma um desenho SVG em PNG com fundo transparente, usando o Chrome (sem instalar nada).
// Serve para fazer adesivos próprios: peça ao Claude um SVG simples e converta.
//
// Uso: node ferramentas/svg-para-png.mjs <desenho.svg> <saida.png> [--largura 800]
// Textos dentro do SVG podem usar font-family "Barlow Condensed" (já embutida aqui).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { abrirChrome, cssFontes } from "./chrome.mjs";

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const i = args.indexOf("--largura");
const LARGURA = i >= 0 ? Number(args.splice(i, 2)[1]) : 800;
if (args.length < 2) { console.log("Uso: node ferramentas/svg-para-png.mjs <desenho.svg> <saida.png> [--largura 800]"); process.exit(1); }
const [SVG, PNG] = args;

const svg = fs.readFileSync(SVG, "utf8");
const vb = svg.match(/viewBox="([\d.\s-]+)"/);
const [, , vw, vh] = vb ? vb[1].trim().split(/\s+/).map(Number) : [0, 0, 1, 1];
const ALTURA = Math.round((LARGURA * vh) / vw);
const fontes = cssFontes(RAIZ, [
  { familia: "Barlow Condensed", arquivo: "barlow-condensed/BarlowCondensed-Black.ttf", peso: 900 },
  { familia: "Barlow Condensed", arquivo: "barlow-condensed/BarlowCondensed-Bold.ttf", peso: 700 },
]);
const html = `<!doctype html><html><head><meta charset="utf-8"><style>${fontes}
html,body{margin:0;background:transparent}svg{display:block;width:${LARGURA}px;height:${ALTURA}px}</style></head>
<body>${svg.replace(/<\?xml[^>]*>/, "")}</body></html>`;
const temp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "estudio-svg-")), "desenho.html");
fs.writeFileSync(temp, html);

const chrome = await abrirChrome({ largura: LARGURA, altura: ALTURA });
try {
  await chrome.abrir(temp);
  const r = await chrome.enviar("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width: LARGURA, height: ALTURA, scale: 1 } });
  fs.mkdirSync(path.dirname(path.resolve(PNG)), { recursive: true });
  fs.writeFileSync(PNG, Buffer.from(r.data, "base64"));
  console.log(`ok · ${LARGURA}x${ALTURA} · ${PNG}`);
} finally {
  chrome.fechar();
  fs.rmSync(path.dirname(temp), { recursive: true, force: true });
}
