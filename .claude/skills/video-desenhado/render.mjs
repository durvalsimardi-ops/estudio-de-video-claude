// Vídeo desenhado (aula 27): lê as cenas, acerta o tempo pela fala e grava o MP4 com o Chrome em segundo plano.
// Uso (na raiz do estúdio):
//   node .claude/skills/video-desenhado/render.mjs trabalho/<peça>                    → vídeo completo
//   node .claude/skills/video-desenhado/render.mjs trabalho/<peça> --quadros 1,3.5,7  → só alguns quadros (JPG) para conferir
// Na pasta da peça: cenas.json (obrigatório), palavras.json (do transcrever.py) e narracao.* (wav, mp3, m4a, aiff).
// Sem palavras.json o tempo é estimado e o vídeo sai sem som.
// Saída: <peça>/render/video.mp4 (1080x1920, 30 qps, voz em -14 LUFS). Precisa de Node 22+, ffmpeg e Google Chrome (ou Chromium).
// Sem nenhuma dependência npm: fala com o Chrome pelo protocolo de depuração (DevTools), por WebSocket.
import { spawn, execFileSync } from "child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync, mkdtempSync } from "fs";
import os from "os";
import path from "path";
import { fileURLToPath, pathToFileURL } from "url";

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const RAIZ = path.resolve(AQUI, "../../..");
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const PASTA = args[0] && !args[0].startsWith("--") ? path.resolve(args[0]) : null;
if (!PASTA) { console.log("Uso: node .claude/skills/video-desenhado/render.mjs trabalho/<peça> [--quadros 1,2.5] [--workers 3]"); process.exit(1); }
const FPS = 30, W = 1080, H = 1920, WORKERS = +opt("--workers", 3), SO_QUADROS = opt("--quadros", null);

// ===== 1. CENAS E DESENHOS =====
const roteiroIn = JSON.parse(readFileSync(path.join(PASTA, "cenas.json"), "utf8"));
const limpa = s => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
function desenho(nome) {
  // procura primeiro um desenho próprio da peça, depois os ícones Lucide do estúdio
  const lugares = [path.join(PASTA, "desenhos", nome + ".svg"), path.join(RAIZ, "assets/icones/lucide", nome + ".svg")];
  const arq = lugares.find(existsSync);
  if (!arq) {
    const tem = readdirSync(path.join(RAIZ, "assets/icones/lucide")).filter(f => f.endsWith(".svg")).map(f => f.slice(0, -4));
    throw new Error(`Desenho "${nome}" não existe. Disponíveis: ${tem.join(", ")} (ou ponha ${nome}.svg em ${path.join(PASTA, "desenhos")})`);
  }
  const svg = readFileSync(arq, "utf8").replace(/<!--[\s\S]*?-->/g, "");
  return svg.replace(/^[\s\S]*?<svg[^>]*>/, "").replace(/<\/svg>[\s\S]*$/, "").trim();
}

// ===== 2. TEMPO DE CADA PALAVRA =====
const arqPalavras = path.join(PASTA, "palavras.json");
const fala = existsSync(arqPalavras) ? JSON.parse(readFileSync(arqPalavras, "utf8")) : null;
const todas = [];   // palavras das frases, na ordem, com a cena de cada uma
roteiroIn.cenas.forEach((c, ci) => c.frase.split(/\s+/).filter(Boolean).forEach(w => todas.push({ w, ci })));
if (fala) {
  // casa cada palavra da frase com a palavra falada (procura até 6 à frente; tolera diferença de grafia)
  let j = 0;
  todas.forEach(p => {
    const a = limpa(p.w);
    for (let k = j; k < Math.min(fala.length, j + 6); k++) {
      const b = limpa(fala[k].w);
      if (a && b && (a === b || (a.length >= 3 && b.length >= 3 && (a.startsWith(b) || b.startsWith(a))))) { p.s = fala[k].s; p.e = fala[k].e; p.casou = true; j = k + 1; break; }
    }
  });
  // palavra que não casou: tempo entre a anterior e a próxima
  todas.forEach((p, i) => {
    if (p.s != null) return;
    const ant = todas.slice(0, i).reverse().find(x => x.s != null), prox = todas.slice(i + 1).find(x => x.s != null);
    const a = ant ? ant.e : 0, b = prox ? prox.s : a + .6;
    p.s = a + (b - a) * .1; p.e = a + (b - a) * .9;
  });
  const casadas = todas.filter(p => p.casou).length;
  console.log(`tempo pela fala: ${casadas} de ${todas.length} palavras das frases achadas na narração`);
  if (casadas < todas.length * .7) console.log("ATENÇÃO: muitas palavras não bateram. A frase do cenas.json está igual ao que foi falado?");
} else {
  // sem narração: ritmo de leitura calmo
  let t = .6, ci = 0;
  todas.forEach(p => { if (p.ci !== ci) { t += .7; ci = p.ci; } p.s = t; p.e = t + .3 + p.w.length * .025; t = p.e + .06; });
  console.log("sem palavras.json: tempo estimado e vídeo sem som");
}

// ===== 3. ROTEIRO PARA A PÁGINA =====
const TR = .4;
const cenas = roteiroIn.cenas.map((c, ci) => {
  const ws = todas.filter(p => p.ci === ci);
  const dest = new Set((c.destaques || []).map(limpa));
  return { c, ws, dest };
}).map((x, ci, arr) => {
  const prevFim = ci > 0 ? Math.max(...arr[ci - 1].ws.map(p => p.e)) : 0;
  const ini = ci === 0 ? 0 : Math.max(prevFim + .05, x.ws[0].s - TR - .05);
  const palavras = x.ws.map(p => ({ w: p.w, s: +p.s.toFixed(3), dura: Math.max(.22, Math.min(.7, p.e - p.s)), destaque: x.dest.has(limpa(p.w)) }));
  const desenhos = (x.c.desenhos || []).map((d, k) => {
    const o = typeof d === "string" ? { icone: d } : d;
    const gatilho = o.na_palavra && palavras.find(p => limpa(p.w) === limpa(o.na_palavra));
    return { svg: desenho(o.icone), cor: o.cor, ini: gatilho ? gatilho.s : ini + (ci === 0 ? .15 : TR) + k * .55, dura: o.dura || 1.3 };
  });
  return { ini, palavras, desenhos };
});
const ultimo = todas.length ? Math.max(...todas.map(p => p.e)) : 2;
const DUR = +(Math.max(ultimo, ...cenas.flatMap(c => c.desenhos.map(d => d.ini + d.dura))) + 1.5).toFixed(2);
const cores = { fundo: "#F7F3EC", tinta: "#2B211B", destaque: "#2E6BFF", ponto: "rgba(43,33,27,.10)", ...(roteiroIn.cores || {}) };
const roteiro = {
  cenas, cores, letra: roteiroIn.letra || 120, espessura: roteiroIn.espessura || 1.35,
  fonte: readFileSync(path.join(RAIZ, "assets/fontes/caveat/Caveat-700.woff2")).toString("base64"),
};

// ===== 4. CHROME EM SEGUNDO PLANO =====
function acharChrome() {
  if (process.env.CHROME) return process.env.CHROME;
  const casa = os.homedir();
  const fixos = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  ];
  for (const f of fixos) if (existsSync(f)) return f;
  for (const n of ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]) {
    try { return execFileSync("which", [n]).toString().trim(); } catch {}
  }
  // o Chrome que o HyperFrames baixa também serve
  const hf = path.join(casa, ".cache/hyperframes/chrome/chrome-headless-shell");
  if (existsSync(hf)) for (const v of readdirSync(hf)) for (const d of readdirSync(path.join(hf, v))) {
    const b = path.join(hf, v, d, "chrome-headless-shell"); if (existsSync(b)) return b;
  }
  throw new Error("Não achei o Chrome. Instale o Google Chrome ou defina CHROME=<caminho do executável>.");
}

const perfil = mkdtempSync(path.join(os.tmpdir(), "video-desenhado-"));
const chrome = spawn(acharChrome(), ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${perfil}`, "--no-first-run",
  "--no-default-browser-check", "--hide-scrollbars", "--force-color-profile=srgb", "--mute-audio", `--window-size=${W},${H}`, "about:blank"],
  { stdio: ["ignore", "ignore", "pipe"] });
const wsUrl = await new Promise((ok, erro) => {
  let txt = "";
  chrome.stderr.on("data", d => { txt += d; const m = txt.match(/ws:\/\/[^\s]+/); if (m) ok(m[0]); });
  chrome.on("exit", () => erro(new Error("O Chrome fechou ao abrir:\n" + txt)));
});
const ws = new WebSocket(wsUrl);
await new Promise(ok => ws.addEventListener("open", ok, { once: true }));
let nId = 0; const espera = new Map(), ouvintes = [];
ws.addEventListener("message", ev => {
  const m = JSON.parse(ev.data);
  if (m.id && espera.has(m.id)) { const { ok, erro } = espera.get(m.id); espera.delete(m.id); m.error ? erro(new Error(m.error.message)) : ok(m.result); }
  else ouvintes.forEach(f => f(m));
});
const cdp = (method, params = {}, sessionId) => new Promise((ok, erro) => { const id = ++nId; espera.set(id, { ok, erro }); ws.send(JSON.stringify({ id, method, params, sessionId })); });

async function abaPronta() {
  const { targetId } = await cdp("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp("Target.attachToTarget", { targetId, flatten: true });
  const s = (m, p) => cdp(m, p, sessionId);
  await s("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  await s("Page.enable");
  const carregou = new Promise(ok => ouvintes.push(m => { if (m.sessionId === sessionId && m.method === "Page.loadEventFired") ok(); }));
  await s("Page.navigate", { url: pathToFileURL(path.join(AQUI, "pagina.html")).href });
  await carregou;
  const r = await s("Runtime.evaluate", { expression: `window.iniciar(${JSON.stringify(roteiro)})`, awaitPromise: true });
  if (r.exceptionDetails) throw new Error("Erro na página: " + JSON.stringify(r.exceptionDetails).slice(0, 400));
  return async t => {
    await s("Runtime.evaluate", { expression: `window.seek(${t})`, awaitPromise: true });
    const { data } = await s("Page.captureScreenshot", { format: "jpeg", quality: 92 });
    return Buffer.from(data, "base64");
  };
}
const fechar = () => { try { chrome.kill(); } catch {} try { rmSync(perfil, { recursive: true, force: true }); } catch {} };

try {
  // ===== 5a. SÓ ALGUNS QUADROS =====
  if (SO_QUADROS) {
    const out = path.join(PASTA, "quadros"); mkdirSync(out, { recursive: true });
    const foto = await abaPronta();
    for (const t of SO_QUADROS.split(",").map(Number)) writeFileSync(path.join(out, `q-${t.toFixed(2)}.jpg`), await foto(t));
    console.log("quadros em", out);
  } else {
    // ===== 5b. VÍDEO INTEIRO: quadros vão direto para o ffmpeg, na ordem =====
    const REND = path.join(PASTA, "render"); mkdirSync(REND, { recursive: true });
    const narr = fala && readdirSync(PASTA).find(f => /^narracao\.(wav|mp3|m4a|aiff?|aac)$/i.test(f));
    const saida = path.join(REND, "video.mp4");
    const ff = ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-"];
    if (narr) ff.push("-i", path.join(PASTA, narr), "-af", `loudnorm=I=-14:TP=-1:LRA=11,apad`, "-c:a", "aac", "-b:a", "192k", "-ar", "48000");
    ff.push("-t", String(DUR), "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
      "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", saida);
    const enc = spawn("ffmpeg", ff, { stdio: ["pipe", "inherit", "inherit"] });
    const fim = new Promise((ok, erro) => enc.on("exit", c => c === 0 ? ok() : erro(new Error("ffmpeg saiu com erro " + c))));
    const NQ = Math.round(DUR * FPS), prontos = new Map(); let proximo = 0, feitos = 0;
    const escreve = async () => { while (prontos.has(proximo)) { const b = prontos.get(proximo); prontos.delete(proximo++); if (!enc.stdin.write(b)) await new Promise(ok => enc.stdin.once("drain", ok)); } };
    const ini = Date.now();
    await Promise.all([...Array(WORKERS).keys()].map(async w => {
      const foto = await abaPronta();
      for (let n = w; n < NQ; n += WORKERS) {
        // espera a fila andar para não guardar quadros demais na memória
        while (n - proximo > WORKERS * 8) await new Promise(ok => setTimeout(ok, 5));
        prontos.set(n, await foto(n / FPS)); await escreve();
        if (++feitos % 150 === 0) console.log(`${feitos}/${NQ} quadros · ${((Date.now() - ini) / 1000).toFixed(0)} s`);
      }
    }));
    await escreve(); enc.stdin.end(); await fim;
    console.log(`ok · ${DUR} s · ${NQ} quadros${narr ? " · com narração" : " · sem som"} · ${saida}`);
  }
} finally { fechar(); ws.close(); }
