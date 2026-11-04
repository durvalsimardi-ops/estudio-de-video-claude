// Abre o Google Chrome sem janela e conversa com ele pelo protocolo de depuração.
// Não precisa instalar nada além do Chrome (ou Edge/Chromium) e do Node 22+.
// Usado pelas skills que desenham quadros em HTML (meia-tela) e pelo svg-para-png.
import { spawn, execSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export function acharChrome() {
  if (process.env.CHROME && fs.existsSync(process.env.CHROME)) return process.env.CHROME;
  const candidatos = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    path.join(os.homedir(), "AppData", "Local", "Google", "Chrome", "Application", "chrome.exe"),
  ];
  for (const c of candidatos) if (fs.existsSync(c)) return c;
  for (const nome of ["google-chrome", "chromium", "chromium-browser"]) {
    try { return execSync(`command -v ${nome}`, { stdio: ["ignore", "pipe", "ignore"] }).toString().trim(); } catch {}
  }
  throw new Error("Não achei o Google Chrome. Instale o Chrome ou informe o caminho em CHROME=/caminho/do/chrome");
}

// Abre uma aba do tamanho pedido, com fundo transparente. Devolve { enviar, abrir, foto, fechar }.
export async function abrirChrome({ largura, altura }) {
  if (typeof WebSocket === "undefined") throw new Error("Precisa do Node 22 ou mais novo (node --version).");
  const perfil = fs.mkdtempSync(path.join(os.tmpdir(), "estudio-chrome-"));
  const proc = spawn(acharChrome(), [
    "--headless=new", "--remote-debugging-port=0", `--user-data-dir=${perfil}`,
    "--no-first-run", "--no-default-browser-check", "--hide-scrollbars", "--mute-audio",
    "--allow-file-access-from-files", "--force-device-scale-factor=1",
    `--window-size=${largura},${altura}`, "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });

  // o Chrome escreve o endereço de depuração na saída de erro
  const endereco = await new Promise((ok, falha) => {
    let texto = "";
    const tempo = setTimeout(() => falha(new Error("O Chrome não respondeu em 20 s.")), 20000);
    proc.stderr.on("data", (d) => {
      texto += d;
      const m = texto.match(/ws:\/\/[^\s]+/);
      if (m) { clearTimeout(tempo); ok(m[0]); }
    });
    proc.on("exit", () => falha(new Error("O Chrome fechou ao abrir:\n" + texto.slice(-500))));
  });
  const porta = new URL(endereco).port;
  const abas = await (await fetch(`http://127.0.0.1:${porta}/json/list`)).json();
  const aba = abas.find((a) => a.type === "page");
  const ws = new WebSocket(aba.webSocketDebuggerUrl);
  await new Promise((ok, falha) => { ws.onopen = ok; ws.onerror = falha; });

  let id = 0;
  const esperando = new Map();
  const eventos = [];
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.id && esperando.has(d.id)) {
      const { ok, falha } = esperando.get(d.id);
      esperando.delete(d.id);
      d.error ? falha(new Error(d.error.message)) : ok(d.result);
    } else if (d.method) eventos.push(d);
  };
  const enviar = (method, params = {}) => new Promise((ok, falha) => {
    const n = ++id;
    esperando.set(n, { ok, falha });
    ws.send(JSON.stringify({ id: n, method, params }));
  });

  await enviar("Page.enable");
  await enviar("Emulation.setDeviceMetricsOverride", { width: largura, height: altura, deviceScaleFactor: 1, mobile: false });
  await enviar("Emulation.setDefaultBackgroundColorOverride", { color: { r: 0, g: 0, b: 0, a: 0 } });

  return {
    enviar,
    // abre um arquivo HTML local e espera as fontes carregarem
    async abrir(arquivo) {
      await enviar("Page.navigate", { url: "file://" + path.resolve(arquivo).split(path.sep).join("/").replace(/^([A-Za-z]):/, "/$1:") });
      for (let i = 0; i < 200; i++) {
        const r = await enviar("Runtime.evaluate", { expression: "document.readyState", returnByValue: true });
        if (r.result.value === "complete") break;
        await new Promise((ok) => setTimeout(ok, 50));
      }
      await enviar("Runtime.evaluate", { expression: "document.fonts.ready.then(() => true)", awaitPromise: true });
    },
    // roda uma expressão na página e devolve o valor
    async avaliar(expressao) {
      const r = await enviar("Runtime.evaluate", { expression: expressao, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error("Erro na página: " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
      return r.result.value;
    },
    // foto da aba em PNG (com transparência)
    async foto() {
      const r = await enviar("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false });
      return Buffer.from(r.data, "base64");
    },
    fechar() {
      try { ws.close(); } catch {}
      proc.kill();
      setTimeout(() => fs.rmSync(perfil, { recursive: true, force: true }), 500);
    },
  };
}

// Fontes de assets/fontes embutidas no HTML (assim a página não depende de nada instalado).
export function cssFontes(raiz, lista) {
  return lista.map(({ familia, arquivo, peso = 400, estilo = "normal" }) => {
    const dados = fs.readFileSync(path.join(raiz, "assets", "fontes", arquivo)).toString("base64");
    const tipo = arquivo.endsWith(".woff2") ? "woff2" : "truetype";
    return `@font-face{font-family:'${familia}';src:url(data:font/${tipo};base64,${dados}) format('${tipo}');font-weight:${peso};font-style:${estilo};}`;
  }).join("\n");
}
