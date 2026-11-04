#!/usr/bin/env node
// Meia tela: a pessoa numa janela embaixo e, em cima, um painel por ideia com lista e check no tempo da fala.
//
// Uso:
//   node .claude/skills/meia-tela/meia_tela.mjs <video> <pasta-do-recorte> <paineis.json> <saida.mp4> [--cor "#2E6BFF"] [--fundo "#EEF1F6"]
//
// - pasta-do-recorte: onde está o rostos.json (bash ferramentas/recorte.sh <video> <pasta> --so-rostos basta).
// - paineis.json: {"paineis": [{"etiqueta": "Passo 1", "titulo": "...", "inicio": 1.0, "fim": 8.0,
//                               "itens": [{"texto": "...", "em": 2.1}]}]}  (tempos do vídeo original)
// Precisa: Node 22+, ffmpeg e Google Chrome instalado (não precisa instalar pacote do npm).
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { abrirChrome, cssFontes } from "../../../ferramentas/chrome.mjs";

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const RAIZ = path.resolve(AQUI, "..", "..", "..");
const args = process.argv.slice(2);
const opcao = (nome, padrao) => {
  const i = args.indexOf(nome);
  if (i < 0) return padrao;
  const v = args[i + 1];
  args.splice(i, 2);
  return v;
};
const COR = opcao("--cor", "#2E6BFF");
const FUNDO = opcao("--fundo", "#EEF1F6");
if (args.length < 4) {
  console.log("Uso: node .claude/skills/meia-tela/meia_tela.mjs <video> <pasta-do-recorte> <paineis.json> <saida.mp4> [--cor #2E6BFF] [--fundo #EEF1F6]");
  process.exit(1);
}
const [VIDEO, PASTA, PAINEIS, SAIDA] = args;

// tela final e lugar da janela da pessoa
const LW = 1080, LH = 1920;
const JANELA = { x: 40, y: 900, w: 1000, h: 940 };

const arqRostos = fs.statSync(PASTA).isDirectory() ? path.join(PASTA, "rostos.json") : PASTA;
const rec = JSON.parse(fs.readFileSync(arqRostos, "utf8"));
const FPS = 30;
const INICIO = rec.inicio, DUR = rec.fim - rec.inicio;

// ---------- enquadramento: rosto inteiro (com cabelo e ombros) dentro da janela o tempo todo ----------
function enquadrar() {
  const q = rec.quadros.filter((x) => x.rosto);
  if (!q.length) throw new Error("Nenhum rosto encontrado no rostos.json. Confira o vídeo.");
  const med = (v) => v.slice().sort((a, b) => a - b)[Math.floor(v.length / 2)];
  const esq = Math.min(...q.map((x) => x.rosto.x));
  const dir = Math.max(...q.map((x) => x.rosto.x + x.rosto.w));
  const topo = Math.min(...q.map((x) => x.topo_cabeca ?? x.rosto.y - 0.45 * x.rosto.h));
  const queixo = Math.max(...q.map((x) => x.rosto.y + x.rosto.h));
  const hRosto = med(q.map((x) => x.rosto.h));
  const proporcao = JANELA.w / JANELA.h;
  let ch = Math.max(queixo - topo + 1.5 * hRosto, 2.6 * hRosto);   // cabeça + ombros
  let cw = ch * proporcao;
  if ((dir - esq) * 1.25 > cw) { cw = (dir - esq) * 1.25; ch = cw / proporcao; }  // rosto que anda de lado
  if (cw > rec.largura) { cw = rec.largura; ch = cw / proporcao; }
  if (ch > rec.altura) { ch = rec.altura; cw = ch * proporcao; }
  cw = Math.floor(cw / 2) * 2; ch = Math.floor(ch / 2) * 2;
  let cx = (esq + dir) / 2 - cw / 2, cy = topo - 0.1 * ch;
  cx = Math.round(Math.min(Math.max(cx, 0), rec.largura - cw));
  cy = Math.round(Math.min(Math.max(cy, 0), rec.altura - ch));
  const inteiro = topo >= cy && queixo <= cy + ch && esq >= cx && dir <= cx + cw;
  return { cw, ch, cx, cy, inteiro };
}
const corte = enquadrar();
console.log(`janela: recorte ${corte.cw}x${corte.ch} em (${corte.cx},${corte.cy}) · rosto inteiro: ${corte.inteiro ? "sim" : "NÃO (pessoa se mexe demais ou está perto demais)"}`);

// ---------- página com os dados ----------
const bruto = JSON.parse(fs.readFileSync(PAINEIS, "utf8"));
const paineis = (bruto.paineis || bruto).map((p) => ({
  etiqueta: p.etiqueta || "", titulo: p.titulo, inicio: p.inicio - INICIO, fim: p.fim - INICIO,
  itens: (p.itens || []).map((it) => ({ texto: it.texto, em: it.em - INICIO })),
}));
const trabalho = path.dirname(path.resolve(arqRostos));  // a página fica junto do recorte, em trabalho/
fs.mkdirSync(trabalho, { recursive: true });
const fontes = cssFontes(RAIZ, [
  { familia: "Titulo", arquivo: "barlow-condensed/BarlowCondensed-Bold.ttf", peso: 700 },
  { familia: "Corpo", arquivo: "barlow/Barlow-Medium.ttf", peso: 500 },
  { familia: "Corpo", arquivo: "barlow/Barlow-SemiBold.ttf", peso: 600 },
]);
const html = fs.readFileSync(path.join(AQUI, "pagina.html"), "utf8")
  .replace("/*FONTES*/", fontes)
  .replace("/*DADOS*/null", JSON.stringify({ janela: JANELA, cor: COR, fundo: FUNDO, paineis }));
const pagina = path.join(trabalho, "meia-tela.html");
fs.writeFileSync(pagina, html);

// ---------- ffmpeg: fundo + pessoa na janela + quadros da página por cima ----------
const filtro = [
  `[0:v]fps=${FPS},crop=${corte.cw}:${corte.ch}:${corte.cx}:${corte.cy},scale=${JANELA.w}:${JANELA.h},setsar=1[p]`,
  `color=c=${FUNDO}:s=${LW}x${LH}:r=${FPS}:d=${DUR.toFixed(3)}[bg]`,
  `[bg][p]overlay=${JANELA.x}:${JANELA.y}:shortest=1[b]`,
  `[b][1:v]overlay=0:0:format=auto,format=yuv420p[v]`,
].join(";");
fs.mkdirSync(path.dirname(path.resolve(SAIDA)), { recursive: true });
const ff = spawn("ffmpeg", ["-v", "error", "-y", "-ss", INICIO.toFixed(3), "-t", DUR.toFixed(3), "-i", VIDEO,
  "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "png", "-i", "-",
  "-filter_complex", filtro, "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
  "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", SAIDA], { stdio: ["pipe", "inherit", "inherit"] });
const escrever = (buf) => new Promise((ok) => (ff.stdin.write(buf) ? ok() : ff.stdin.once("drain", ok)));

const chrome = await abrirChrome({ largura: LW, altura: LH });
try {
  await chrome.abrir(pagina);
  const total = Math.round(DUR * FPS);
  let anterior = null, foto = null, novas = 0;
  for (let n = 0; n < total; n++) {
    const estado = await chrome.avaliar(`window.seek(${(n / FPS).toFixed(4)})`);
    if (estado !== anterior || !foto) { foto = await chrome.foto(); anterior = estado; novas++; }
    await escrever(foto);
    if (n % 150 === 0) process.stderr.write(`  ${n}/${total} quadros\n`);
  }
  console.log(`quadros: ${total} (${novas} desenhados, o resto repetido)`);
} finally {
  chrome.fechar();
  ff.stdin.end();
}
await new Promise((ok) => ff.on("close", ok));
if (ff.exitCode !== 0) { console.error("O ffmpeg falhou."); process.exit(1); }
console.log(`ok · ${SAIDA}`);
