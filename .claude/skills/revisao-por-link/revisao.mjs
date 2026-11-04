#!/usr/bin/env node
// Revisão de vídeo por link: o cliente assiste, pausa e comenta no segundo exato.
// Uso (na raiz do estúdio):
//   node .claude/skills/revisao-por-link/revisao.mjs configurar <nome-do-projeto>   cria o site e o banco na SUA conta Cloudflare (uma vez)
//   node .claude/skills/revisao-por-link/revisao.mjs subir <video.mp4> --titulo "Café Aurora · Reels 1"   peça nova (v1)
//   node .claude/skills/revisao-por-link/revisao.mjs subir <video.mp4> --peca <codigo> [--nota "o que mudou"]   versão nova
//   node .claude/skills/revisao-por-link/revisao.mjs publicar          manda o site para o Cloudflare (só com o OK do aluno)
//   node .claude/skills/revisao-por-link/revisao.mjs listar            peças, versões, links e comentários novos
//   node .claude/skills/revisao-por-link/revisao.mjs puxar [<codigo>] [--todos]   comentários → lista de correções com quadros
//   node .claude/skills/revisao-por-link/revisao.mjs local             testa no seu computador (http://localhost:8788), sem publicar
// Opções: --pasta <dir> (padrão trabalho/revisao) · --base <url> (outro endereço, ex. o local)
// O token de leitura fica em ~/.config/estudio-de-video/revisao.json (fora do git). Outro lugar: variável REVISAO_CONFIG.
import { execFileSync, spawn, spawnSync } from "node:child_process";
import { copyFileSync, cpSync, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { randomBytes } from "node:crypto";
import { fileURLToPath } from "node:url";

const AQUI = dirname(fileURLToPath(import.meta.url));
const RAIZ = resolve(AQUI, "../../..");
const LIMITE_MB = +process.env.REVISAO_LIMITE_MB || 24; // o Cloudflare Pages aceita até 25 MB por arquivo
const PORTA_LOCAL = 8788;

const [cmd, ...resto] = process.argv.slice(2);
const opt = (k) => { const i = resto.indexOf("--" + k); return i >= 0 ? resto[i + 1] : undefined; };
const tem = (k) => resto.includes("--" + k);
const SIM_NAO = new Set(["--todos"]); // opções sem valor
const pos = resto.filter((a, i) => !a.startsWith("--") && (!(resto[i - 1] || "").startsWith("--") || SIM_NAO.has(resto[i - 1])));

const PASTA = resolve(opt("pasta") || join(RAIZ, "trabalho/revisao"));
const PUBLICO = join(PASTA, "publico");
const REGISTRO = join(PASTA, "pecas.json");
const CONFIG = process.env.REVISAO_CONFIG || join(homedir(), ".config/estudio-de-video/revisao.json");

const lerJson = (f, padrao) => (existsSync(f) ? JSON.parse(readFileSync(f, "utf8")) : padrao);
const gravarJson = (f, d) => { mkdirSync(dirname(f), { recursive: true }); writeFileSync(f, JSON.stringify(d, null, 2)); };
const codigoNovo = () => Array.from(randomBytes(18), (x) => "abcdefghijkmnpqrstuvwxyz23456789"[x % 32]).join("");
const fmt = (t) => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`.replace(".", ",");
const slug = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40);
const curto = (f) => (f.startsWith(RAIZ + "/") ? relative(RAIZ, f) : f);
const npx = process.platform === "win32" ? "npx.cmd" : "npx";

function config() {
  const c = lerJson(CONFIG, null);
  if (c?.token) return c;
  const novo = { token: randomBytes(24).toString("hex"), projeto: null, url: null };
  gravarJson(CONFIG, novo);
  return novo;
}
const base = (c) => opt("base") || c.url;

function wrangler(args, extra = {}) {
  const r = spawnSync(npx, ["--yes", "wrangler", ...args], { cwd: PASTA, encoding: "utf8", ...extra });
  if (r.status !== 0) throw new Error(`wrangler ${args[0]} ${args[1] || ""}: ${(r.stderr || r.stdout || "").trim().split("\n").slice(-3).join(" ")}`);
  return (r.stdout || "") + (r.stderr || "");
}

// Monta a pasta do site: código das funções, página inicial e wrangler.toml.
function prepararPasta(c) {
  mkdirSync(PUBLICO, { recursive: true });
  cpSync(join(AQUI, "site/functions"), join(PASTA, "functions"), { recursive: true });
  for (const f of ["index.html", "404.html", "robots.txt", "_headers"]) copyFileSync(join(AQUI, "site/publico", f), join(PUBLICO, f));
  const nome = c.projeto || "revisao-local";
  writeFileSync(join(PASTA, "wrangler.toml"), [
    `# Gerado por revisao.mjs. Não vai para o git (fica em trabalho/).`,
    `name = "${nome}"`,
    `pages_build_output_dir = "./publico"`,
    `compatibility_date = "2025-09-01"`,
    ``,
    `[[d1_databases]]`,
    `binding = "DB"`,
    `database_name = "${c.banco || nome + "-comentarios"}"`,
    `database_id = "${c.banco_id || "00000000-0000-0000-0000-000000000000"}"`,
    ``,
  ].join("\n"));
  // a página de cada peça é sempre a versão mais nova do modelo
  for (const p of lerJson(REGISTRO, [])) {
    const d = join(PUBLICO, "p", p.codigo);
    if (existsSync(d)) copyFileSync(join(AQUI, "site/pagina.html"), join(d, "index.html"));
  }
}

function duracao(v) {
  return +execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v], { encoding: "utf8" }).trim();
}

// Prévia leve para a web: H.264, até 1280 px no lado maior, começa a tocar antes de baixar tudo.
function previa(entrada, saida) {
  const dur = duracao(entrada);
  const escala = (lado) => `scale='if(gt(iw,ih),min(${lado},iw),-2)':'if(gt(iw,ih),-2,min(${lado},ih))'`;
  const tentativas = [
    ["-crf", "26", "-vf", escala(1280)],
    null, // calculada pelo tamanho
    null,
  ];
  for (let i = 0; i < tentativas.length; i++) {
    let v = tentativas[i];
    if (!v) {
      const kbps = Math.floor(((LIMITE_MB * 8 * 1e6 * 0.92) / dur - 128e3) / 1000 / (i === 2 ? 1.4 : 1));
      if (kbps < 150) throw new Error("vídeo longo demais para 25 MB: mande um trecho ou divida em partes");
      v = ["-b:v", `${kbps}k`, "-maxrate", `${Math.round(kbps * 1.2)}k`, "-bufsize", `${kbps * 2}k`, "-vf", escala(i === 2 ? 960 : 1280)];
    }
    execFileSync("ffmpeg", ["-v", "error", "-y", "-i", entrada, "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p", ...v,
      "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-movflags", "+faststart", saida], { stdio: "inherit" });
    const mb = statSync(saida).size / 1e6;
    if (mb <= LIMITE_MB) return { mb, dur };
    console.log(`prévia com ${mb.toFixed(1)} MB, reduzindo…`);
  }
  throw new Error("não consegui deixar a prévia abaixo de 25 MB");
}

async function api(c, caminho, corpo) {
  const b = base(c);
  if (!b) throw new Error("sem endereço: rode configurar (ou use --base http://localhost:8788 no teste local)");
  const r = await fetch(b.replace(/\/$/, "") + "/api/admin/" + caminho, {
    method: corpo ? "POST" : "GET",
    headers: { authorization: `Bearer ${c.token}`, "content-type": "application/json" },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`${caminho}: ${d.erro || r.status}`);
  return d;
}

// ---------------------------------------------------------------- comandos
async function configurar() {
  const projeto = slug(pos[0] || "");
  if (!projeto) throw new Error("diga o nome do projeto, ex.: configurar revisao-ana");
  const c = config();
  mkdirSync(PASTA, { recursive: true });
  console.log("conferindo o login na Cloudflare…");
  wrangler(["whoami"]);
  console.log(`criando o site ${projeto}…`);
  const saida = wrangler(["pages", "project", "create", projeto, "--production-branch", "main"]);
  const url = (saida.match(/https:\/\/[a-z0-9.-]+\.pages\.dev/) || [`https://${projeto}.pages.dev`])[0];
  console.log("criando o banco de comentários (D1)…");
  const banco = `${projeto}-comentarios`;
  const d1 = wrangler(["d1", "create", banco]);
  const id = (d1.match(/"?database_id"?\s*[=:]\s*"([0-9a-f-]{36})"/) || [])[1];
  if (!id) throw new Error("não achei o id do banco na resposta do wrangler:\n" + d1);
  Object.assign(c, { projeto, url, banco, banco_id: id });
  gravarJson(CONFIG, c);
  prepararPasta(c);
  console.log("guardando o token de leitura no site…");
  wrangler(["pages", "secret", "put", "TOKEN_REVISAO", "--project-name", projeto], { input: c.token + "\n" });
  console.log(`ok · site ${url} · banco ${banco}\nConfiguração em ${CONFIG} (fora do git).`);
}

async function subir() {
  const arq = resolve(pos[0] || "");
  if (!existsSync(arq)) throw new Error("vídeo não encontrado: " + (pos[0] || "(nenhum)"));
  const c = config();
  const registro = lerJson(REGISTRO, []);
  let p;
  if (opt("peca")) {
    p = registro.find((x) => x.codigo === opt("peca"));
    if (!p) throw new Error("peça não encontrada: " + opt("peca") + " (veja com listar)");
  } else {
    if (!opt("titulo")) throw new Error('peça nova precisa de --titulo "nome da peça"');
    p = { codigo: codigoNovo(), titulo: opt("titulo"), versoes: [], criado_em: new Date().toISOString() };
    registro.push(p);
  }
  prepararPasta(c);
  const n = (p.versoes.at(-1)?.n || 0) + 1;
  const dir = join(PUBLICO, "p", p.codigo);
  mkdirSync(dir, { recursive: true });
  console.log(`preparando a prévia v${n}…`);
  const { mb, dur } = previa(arq, join(dir, `v${n}.mp4`));
  p.versoes.push({ n, arquivo: `v${n}.mp4`, duracao: Math.round(dur * 10) / 10, nota: opt("nota") || "", criado_em: new Date().toISOString(), origem: curto(arq) });
  copyFileSync(join(AQUI, "site/pagina.html"), join(dir, "index.html"));
  // o que vai para o site: só título e versões (sem caminhos do seu computador)
  gravarJson(join(dir, "peca.json"), { titulo: p.titulo, versoes: p.versoes.map(({ n, arquivo, duracao, nota }) => ({ n, arquivo, duracao, nota })) });
  gravarJson(REGISTRO, registro);
  const b = base(c) || "https://<seu-projeto>.pages.dev";
  console.log(`ok · ${p.titulo} v${n} · ${mb.toFixed(1)} MB · ${dur.toFixed(1)} s`);
  console.log(`link: ${b.replace(/\/$/, "")}/p/${p.codigo}/`);
  console.log("Ainda não está na internet. Para publicar: revisao.mjs publicar (com o OK do aluno).");
}

async function publicar() {
  const c = config();
  if (!c.projeto) throw new Error("rode primeiro: revisao.mjs configurar <nome-do-projeto>");
  prepararPasta(c);
  console.log("publicando…");
  const s = wrangler(["pages", "deploy", "publico", "--project-name", c.projeto, "--branch", "main", "--commit-dirty=true"], { stdio: ["ignore", "pipe", "pipe"] });
  console.log(s.split("\n").filter((l) => /Success|Deployment complete|pages\.dev/.test(l)).join("\n"));
  for (const p of lerJson(REGISTRO, [])) console.log(`${p.titulo} · v${p.versoes.at(-1).n} · ${c.url}/p/${p.codigo}/`);
}

async function listar() {
  const c = config();
  let novos = [];
  try { novos = await api(c, "comentarios?status=novo"); } catch (e) { console.log(`(sem contar comentários: ${e.message})`); }
  const registro = lerJson(REGISTRO, []);
  if (!registro.length) return console.log("nenhuma peça ainda.");
  for (const p of registro) {
    const q = novos.filter((x) => x.peca === p.codigo).length;
    console.log(`${p.codigo}  ${p.titulo} · v${p.versoes.at(-1).n}${q ? ` · ${q} comentário(s) novo(s)` : ""}\n    ${(base(c) || "https://<seu-projeto>.pages.dev").replace(/\/$/, "")}/p/${p.codigo}/`);
  }
}

async function puxar() {
  const c = config();
  const registro = lerJson(REGISTRO, []);
  const filtro = new URLSearchParams();
  if (pos[0]) filtro.set("peca", pos[0]);
  if (!tem("todos")) filtro.set("status", "novo");
  const lista = await api(c, "comentarios?" + filtro);
  if (!lista.length) return console.log("nenhum comentário novo.");
  const grupos = {};
  for (const x of lista) (grupos[`${x.peca}|${x.versao}`] ||= []).push(x);
  const agora = new Date();
  const dois = (n) => String(n).padStart(2, "0");
  const carimbo = `${agora.getFullYear()}-${dois(agora.getMonth() + 1)}-${dois(agora.getDate())}-${dois(agora.getHours())}-${dois(agora.getMinutes())}`;
  for (const [chave, itens] of Object.entries(grupos)) {
    const [codigo, versao] = chave.split("|");
    const p = registro.find((x) => x.codigo === codigo) || { titulo: codigo, versoes: [] };
    const video = join(PUBLICO, "p", codigo, `v${versao}.mp4`);
    const dir = join(PASTA, "correcoes", `${slug(p.titulo)}-${codigo.slice(0, 6)}`, `v${versao}-${carimbo}`);
    mkdirSync(join(dir, "quadros"), { recursive: true });
    const linhas = [
      `# ${p.titulo} · correções da v${versao}`, "",
      `Puxado em ${agora.toLocaleString("pt-BR")} · ${itens.length} comentário(s) · link: ${(base(c) || "").replace(/\/$/, "")}/p/${codigo}/`, "",
      "Para cada item: olhar o quadro, escrever a correção em uma linha e confirmar com o aluno antes de editar.", "",
    ];
    itens.forEach((x, i) => {
      const nome = `${String(i + 1).padStart(2, "0")}-${fmt(x.t).replace(/[:,]/g, "-")}.jpg`;
      const quadro = join(dir, "quadros", nome);
      if (existsSync(video)) {
        execFileSync("ffmpeg", ["-v", "error", "-y", "-ss", String(x.t), "-i", video, "-frames:v", "1", "-vf", "scale='min(720,iw)':-2", "-q:v", "3", quadro]);
      }
      linhas.push(`## ${i + 1}. ${fmt(x.t)} · ${x.nome}`, "", `> ${x.texto.replace(/\n/g, "\n> ")}`, "",
        existsSync(quadro) ? `Quadro: \`${curto(quadro)}\`` : "Quadro: (vídeo desta versão não está nesta pasta)", "",
        "Correção: (preencher)", "");
    });
    writeFileSync(join(dir, "correcoes.md"), linhas.join("\n"));
    await api(c, "status", { ids: itens.map((x) => x.id), status: "recebido" });
    console.log(`${p.titulo} v${versao} · ${itens.length} comentário(s)\n  ${curto(join(dir, "correcoes.md"))}`);
  }
}

async function local() {
  const c = config();
  prepararPasta(c);
  writeFileSync(join(PASTA, ".dev.vars"), `TOKEN_REVISAO=${c.token}\n`);
  console.log(`teste local em http://localhost:${PORTA_LOCAL} (Ctrl+C para parar). Nada vai para a internet.`);
  for (const p of lerJson(REGISTRO, [])) console.log(`  ${p.titulo}: http://localhost:${PORTA_LOCAL}/p/${p.codigo}/`);
  const filho = spawn(npx, ["--yes", "wrangler", "pages", "dev", "publico", "--port", String(PORTA_LOCAL)], { cwd: PASTA, stdio: "inherit" });
  filho.on("exit", (code) => process.exit(code ?? 0));
}

const comandos = { configurar, subir, publicar, listar, puxar, local };
if (!comandos[cmd]) {
  console.log(readFileSync(fileURLToPath(import.meta.url), "utf8").split("\n").slice(1, 13).map((l) => l.replace(/^\/\/ ?/, "")).join("\n"));
  process.exit(1);
}
comandos[cmd]().catch((e) => { console.error("erro:", e.message); process.exit(1); });
