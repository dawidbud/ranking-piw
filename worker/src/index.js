// Liga Piw — API na Cloudflare Workers + D1 (SQLite).
// Wystawia tę samą strukturę danych co dawny jsonblob: { ratings, comments, newBeers },
// ale zapisy są atomowe (bez wyścigów) i walidowane. CORS otwarty (strona publiczna).

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", ...CORS } });

// identyczna normalizacja jak we froncie i w Pythonie — klucz piwa musi się zgadzać
const norm = (s) => String(s == null ? "" : s).toLowerCase().split(/\s+/).filter(Boolean).join(" ");
const beerId = (m, n, r) => norm(m) + "|" + norm(n) + "|" + norm(r);
const plDate = () => {
  const d = new Date(), p = (n) => String(n).padStart(2, "0");
  return p(d.getDate()) + "." + p(d.getMonth() + 1) + "." + d.getFullYear();
};

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    const path = new URL(req.url).pathname.replace(/\/+$/, "") || "/";
    try {
      if (req.method === "GET" && path === "/") return json({ ok: true, service: "liga-piw" });
      if (req.method === "GET" && path === "/api/store") return json(await buildStore(env));
      if (req.method === "POST" && path === "/api/rate") return await handleRate(req, env);
      if (req.method === "POST" && path === "/api/comment") return await handleComment(req, env);
      if (req.method === "POST" && path === "/api/beer") return await handleBeer(req, env);
      return json({ error: "not found" }, 404);
    } catch (e) {
      return json({ error: String((e && e.message) || e) }, 500);
    }
  },
};

async function buildStore(env) {
  const [r, c, b] = await Promise.all([
    env.DB.prepare("SELECT beer_id, author, value FROM ratings").all(),
    env.DB.prepare("SELECT beer_id, author, text, date FROM comments ORDER BY id").all(),
    env.DB.prepare("SELECT id, marka, nazwa, abv, rodzaj, added_by, date FROM new_beers ORDER BY created_at").all(),
  ]);
  const ratings = {};
  for (const row of r.results) (ratings[row.beer_id] ||= {})[row.author] = row.value;
  const comments = {};
  for (const row of c.results) (comments[row.beer_id] ||= []).push({ author: row.author, text: row.text, date: row.date });
  const newBeers = b.results.map((x) => ({
    id: x.id, marka: x.marka, nazwa: x.nazwa, abv: x.abv, rodzaj: x.rodzaj, addedBy: x.added_by, date: x.date,
  }));
  return { ratings, comments, newBeers };
}

async function handleRate(req, env) {
  const body = await req.json().catch(() => ({}));
  const bid = body.beerId;
  const author = String(body.author || "").trim().slice(0, 40);
  if (!bid || !author) return json({ error: "brak beerId/author" }, 400);
  if (body.value == null) {
    await env.DB.prepare("DELETE FROM ratings WHERE beer_id=? AND author=?").bind(bid, author).run();
    return json({ ok: true });
  }
  const v = Number(body.value);
  if (!(v >= 0.25 && v <= 5) || Math.round(v * 4) !== v * 4) return json({ error: "zła ocena" }, 400);
  await env.DB
    .prepare("INSERT INTO ratings (beer_id,author,value) VALUES (?,?,?) ON CONFLICT(beer_id,author) DO UPDATE SET value=excluded.value")
    .bind(bid, author, v).run();
  return json({ ok: true });
}

async function handleComment(req, env) {
  const body = await req.json().catch(() => ({}));
  const bid = body.beerId;
  const author = String(body.author || "").trim().slice(0, 40);
  const text = String(body.text || "").trim().slice(0, 500);
  if (!bid || !author || !text) return json({ error: "brak danych" }, 400);
  const date = String(body.date || "").trim().slice(0, 20) || plDate();
  await env.DB.prepare("INSERT INTO comments (beer_id,author,text,date) VALUES (?,?,?,?)").bind(bid, author, text, date).run();
  return json({ ok: true });
}

async function handleBeer(req, env) {
  const body = await req.json().catch(() => ({}));
  const marka = String(body.marka || "").trim().slice(0, 80);
  const nazwa = String(body.nazwa || "").trim().slice(0, 80);
  const rodzaj = (String(body.rodzaj || "").trim() || "Inne").slice(0, 40);
  if (!marka || !nazwa) return json({ error: "brak marki/nazwy" }, 400);
  let abv = body.abv == null ? null : Number(body.abv);
  if (abv != null && !(abv >= 0 && abv <= 30)) abv = null;
  const addedBy = String(body.addedBy || "").trim().slice(0, 40);
  const date = String(body.date || "").trim().slice(0, 20) || plDate();
  const id = beerId(marka, nazwa, rodzaj);
  await env.DB
    .prepare("INSERT INTO new_beers (id,marka,nazwa,abv,rodzaj,added_by,date) VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING")
    .bind(id, marka, nazwa, abv, rodzaj, addedBy, date).run();
  return json({ ok: true, id });
}
