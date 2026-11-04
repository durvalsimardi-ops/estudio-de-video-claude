// Comentários da página de revisão (Cloudflare Pages Functions + banco D1 "DB").
//
// Para quem tem o link da peça (o código aleatório no endereço é a proteção):
//   GET    /api/comentarios?peca=<codigo>&versao=<n>      lista os comentários daquela versão
//   POST   /api/comentarios  {peca, versao, t, nome, texto} grava um comentário e devolve uma chave para apagar
//   DELETE /api/comentarios?id=<id>&chave=<chave>          apaga o próprio comentário
// Só para o Claude do aluno (cabeçalho Authorization: Bearer <TOKEN_REVISAO>):
//   GET    /api/admin/comentarios[?peca=<codigo>][&status=novo]
//   POST   /api/admin/status  {ids: [1, 2], status: "recebido" | "feito" | "novo"}

const LIMITE_POR_PECA = 400;   // comentários por peça, somando as versões
const INTERVALO_MS = 3000;     // a mesma pessoa não grava dois comentários em menos de 3 s

const json = (dados, status = 200) =>
  new Response(JSON.stringify(dados), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });

const aleatorio = (n = 20) => {
  const letras = "abcdefghijkmnpqrstuvwxyz23456789";
  return Array.from(crypto.getRandomValues(new Uint8Array(n)), (x) => letras[x % letras.length]).join("");
};

async function resumo(texto) {
  const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(texto));
  return Array.from(new Uint8Array(b).slice(0, 8), (x) => x.toString(16).padStart(2, "0")).join("");
}

// A tabela é criada na primeira chamada: não precisa rodar nada no banco antes.
let pronto = false;
async function preparar(db) {
  if (pronto) return;
  await db.batch([
    db.prepare(`CREATE TABLE IF NOT EXISTS comentarios (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      peca TEXT NOT NULL,
      versao INTEGER NOT NULL,
      t REAL NOT NULL,
      nome TEXT NOT NULL,
      texto TEXT NOT NULL,
      chave TEXT NOT NULL,
      origem TEXT,
      status TEXT NOT NULL DEFAULT 'novo',
      criado_em TEXT NOT NULL)`),
    db.prepare("CREATE INDEX IF NOT EXISTS comentarios_peca ON comentarios (peca, versao)"),
  ]);
  pronto = true;
}

// A peça existe se o arquivo peca.json dela foi publicado junto com o site.
async function lerPeca(env, url, codigo) {
  if (!/^[a-z0-9]{12,40}$/.test(codigo || "")) return null;
  const r = await env.ASSETS.fetch(new Request(new URL(`/p/${codigo}/peca.json`, url)));
  if (!r.ok) return null;
  try { return await r.json(); } catch { return null; }
}

async function publico(req, env, url) {
  const db = env.DB;
  if (req.method === "GET") {
    const peca = url.searchParams.get("peca");
    if (!(await lerPeca(env, url, peca))) return json({ erro: "peça não encontrada" }, 404);
    const versao = +url.searchParams.get("versao") || 1;
    const { results } = await db
      .prepare("SELECT id, versao, t, nome, texto, criado_em FROM comentarios WHERE peca = ? AND versao = ? ORDER BY t, id")
      .bind(peca, versao).all();
    return json(results);
  }

  if (req.method === "POST") {
    const c = await req.json().catch(() => null);
    if (!c) return json({ erro: "envio inválido" }, 400);
    if (c.site) return json({ ok: true }); // campo escondido: só robô preenche
    const p = await lerPeca(env, url, c.peca);
    if (!p) return json({ erro: "peça não encontrada" }, 404);
    const versao = p.versoes.find((v) => v.n === +c.versao);
    if (!versao) return json({ erro: "versão não encontrada" }, 400);
    const t = Math.round(+c.t * 10) / 10;
    const nome = String(c.nome || "").trim().slice(0, 40);
    const texto = String(c.texto || "").trim().slice(0, 1000);
    if (!nome || !texto) return json({ erro: "escreva o seu nome e o comentário" }, 400);
    if (!(t >= 0 && t <= (versao.duracao || 0) + 1)) return json({ erro: "tempo fora do vídeo" }, 400);

    const origem = await resumo((req.headers.get("cf-connecting-ip") || "local") + c.peca);
    const conta = await db.prepare("SELECT COUNT(*) AS n FROM comentarios WHERE peca = ?").bind(c.peca).first();
    if (conta.n >= LIMITE_POR_PECA) return json({ erro: "esta peça já recebeu comentários demais" }, 429);
    const ultimo = await db
      .prepare("SELECT criado_em FROM comentarios WHERE peca = ? AND origem = ? ORDER BY id DESC LIMIT 1")
      .bind(c.peca, origem).first();
    if (ultimo && Date.now() - Date.parse(ultimo.criado_em) < INTERVALO_MS) return json({ erro: "aguarde um instante" }, 429);

    const chave = aleatorio();
    const r = await db
      .prepare("INSERT INTO comentarios (peca, versao, t, nome, texto, chave, origem, criado_em) VALUES (?,?,?,?,?,?,?,?)")
      .bind(c.peca, versao.n, t, nome, texto, chave, origem, new Date().toISOString()).run();
    return json({ ok: true, id: r.meta.last_row_id, chave });
  }

  if (req.method === "DELETE") {
    const r = await db.prepare("DELETE FROM comentarios WHERE id = ? AND chave = ? AND status = 'novo'")
      .bind(+url.searchParams.get("id"), url.searchParams.get("chave") || "").run();
    return json({ ok: r.meta.changes > 0 });
  }
  return json({ erro: "método" }, 405);
}

async function admin(req, env, url, partes) {
  const token = env.TOKEN_REVISAO || "";
  if (token.length < 24 || req.headers.get("authorization") !== `Bearer ${token}`) return json({ erro: "sem acesso" }, 401);
  const db = env.DB;
  if (partes[0] === "comentarios" && req.method === "GET") {
    const filtros = [], valores = [];
    for (const k of ["peca", "status"]) {
      const v = url.searchParams.get(k);
      if (v) { filtros.push(`${k} = ?`); valores.push(v); }
    }
    const onde = filtros.length ? "WHERE " + filtros.join(" AND ") : "";
    const { results } = await db
      .prepare(`SELECT id, peca, versao, t, nome, texto, status, criado_em FROM comentarios ${onde} ORDER BY peca, versao, t, id`)
      .bind(...valores).all();
    return json(results);
  }
  if (partes[0] === "status" && req.method === "POST") {
    const c = await req.json().catch(() => ({}));
    if (!["novo", "recebido", "feito"].includes(c.status) || !Array.isArray(c.ids)) return json({ erro: "envio inválido" }, 400);
    const ids = c.ids.map(Number).filter(Number.isInteger);
    if (ids.length) await db.batch(ids.map((id) => db.prepare("UPDATE comentarios SET status = ? WHERE id = ?").bind(c.status, id)));
    return json({ ok: true, alterados: ids.length });
  }
  return json({ erro: "rota" }, 404);
}

export async function onRequest({ request, env, params }) {
  const url = new URL(request.url);
  const partes = params.rota || [];
  try {
    if (!env.DB) return json({ erro: "banco D1 não ligado (binding DB)" }, 500);
    await preparar(env.DB);
    if (partes[0] === "comentarios") return await publico(request, env, url);
    if (partes[0] === "admin") return await admin(request, env, url, partes.slice(1));
    return json({ erro: "rota" }, 404);
  } catch (e) {
    return json({ erro: String(e?.message || e) }, 500);
  }
}
