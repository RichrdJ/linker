"use strict";

/* ================================================================ toestand */
let state = JSON.parse(document.getElementById("initial-state").textContent);
let currentId = null;     // actieve categorie (in de code: collection)
let statusMap = {};
let selectedId = null;    // link die Enter opent

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const board = $("#board");
const q = $("#q");
const hint = $("#search-hint");

const SVG = {
  edit: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16v4zM14 6l4 4"/></svg>',
  copy: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a2 2 0 0 1 2-2h8"/></svg>',
  grip: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="6" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="18" r="1"/></svg>',
  plus: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  az: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 18 7.5 6 11 18M5.2 14h4.6M14 6h6l-6 12h6"/></svg>',
  popular: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6h14M5 12h9M5 18h4"/></svg>',
};
const SWATCHES = ["#3b7ddd", "#3fb8af", "#5cc489", "#a38cf2", "#ec6f8e", "#e8734a", "#f0b44c"];

/* ================================================================ hulpjes */
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
function hash(s) {
  let h = 0;
  for (const ch of String(s)) h = (h * 31 + ch.codePointAt(0)) >>> 0;
  return h;
}
function isTextIcon(icon) {
  icon = (icon || "").trim();
  return !!icon && !/^(https?:\/\/|di:|sh:|upload:)/.test(icon) && !/^[a-z0-9][a-z0-9._-]*$/.test(icon);
}
function hostOf(url) {
  try { return new URL(url).host; } catch { return url; }
}
function letterColor(name) { return `hsl(${hash(name) % 360} 45% 42%)`; }
function inkFor(hex) {
  const n = parseInt(hex.slice(1), 16);
  const lum = (0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
  return lum > 0.6 ? "#1a1408" : "#ffffff";
}
function toast(msg, ms = 3200) {
  const t = $("#toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.hidden = true), ms);
}
async function api(method, url, body, raw = false) {
  const opts = { method, headers: {} };
  if (raw) { opts.body = body; opts.headers["Content-Type"] = "application/octet-stream"; }
  else if (body !== undefined) { opts.body = JSON.stringify(body); opts.headers["Content-Type"] = "application/json"; }
  const res = await fetch(url, opts);
  let data = null;
  try { data = await res.json(); } catch { /* leeg antwoord */ }
  if (!res.ok) {
    let msg = data?.detail;
    if (Array.isArray(msg)) msg = msg.map(d => d.msg).join(" ");
    const err = new Error(msg || `Er ging iets mis (${res.status}).`);
    err.status = res.status;
    if (res.status === 401 && data?.login) {   // sessie verlopen: terug naar de loginpagina
      location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search + location.hash);
    } else if (res.status === 401) { state.can_edit = false; applyAccess(); }
    throw err;
  }
  return data;
}
async function reload() {
  state = await api("GET", "/api/state");
  applySettings();
  render();
}

const cols = () => state.collections;
const current = () => cols().find(c => c.id === currentId);
function* eachLink() {
  for (const c of cols()) for (const s of c.sections) for (const l of s.links) yield { c, s, l };
}
const findLink = id => { for (const x of eachLink()) if (x.l.id === id) return x; return null; };
const findSection = id => { for (const c of cols()) for (const s of c.sections) if (s.id === id) return { c, s }; return null; };

/* ================================================================ weergave */
function iconHTML(link) {
  const icon = (link.icon || "").trim();
  if (isTextIcon(icon)) return `<span class="icon" aria-hidden="true">${esc(icon)}</span>`;
  const v = hash(icon + "|" + link.url).toString(36);
  const letter = esc((link.name || "?").trim().charAt(0).toUpperCase());
  // Eerst een lettertegel; die maakt plaats zodra het icoon geladen is
  return `<span class="icon letter" aria-hidden="true" style="background:${letterColor(link.name)}">${letter}<img
    src="/icon/${link.id}?v=${v}" alt="" hidden></span>`;
}

function cardHTML(link, terms) {
  const s = state.settings;
  const target = s.new_tab === "1" ? ' target="_blank" rel="noopener"' : "";
  const sub = link.description || hostOf(link.url).replace(/^www\./, "");
  const hl = t => (terms?.length ? highlight(t, terms) : esc(t));
  return `<div class="card" data-id="${link.id}">
    <a class="card-link" href="${esc(link.url)}"${target} draggable="false" data-visit="${link.id}"
      title="${esc(link.url)}${link.visits ? `\n${link.visits} keer geopend` : ""}">
      ${iconHTML(link)}
      <span class="card-text">
        <span class="card-name">${hl(link.name)}</span>
        <span class="card-sub">${hl(sub)}</span>
      </span>
    </a>
    <span class="dot" data-dot="${link.id}"></span>
    <span class="card-actions">
      <button type="button" class="mini edit-only" data-edit-link="${link.id}" title="Bewerken">${SVG.edit}</button>
      <button type="button" class="mini copy" data-copy="${link.id}" title="Adres kopiëren">${SVG.copy}</button>
    </span>
  </div>`;
}

function sectionHTML(sec, opts = {}) {
  const { terms, links = sec.links, path } = opts;
  const searching = !!terms?.length;
  return `<section class="section" data-sid="${sec.id}" aria-labelledby="s${sec.id}">
    <div class="section-head">
      <h2 class="section-name" id="s${sec.id}">${path ? `<span class="section-path">${esc(path)} / </span>` : ""}${esc(sec.name)}</h2>
      <span class="section-count">${links.length || ""}</span>
      ${searching ? "" : `<button type="button" class="mini add-inline edit-only" data-add-link="${sec.id}" title="Snelkoppeling toevoegen aan ${esc(sec.name)}" aria-label="Snelkoppeling toevoegen aan ${esc(sec.name)}">${SVG.plus}</button>
      <span class="section-tools">
        <button type="button" class="mini" data-sort="${sec.id}" title="Sorteren van A tot Z">${SVG.az}</button>
        <button type="button" class="mini" data-sort="${sec.id}" data-sort-by="visits" title="Sorteren op meest bezocht">${SVG.popular}</button>
        <button type="button" class="mini" data-edit-section="${sec.id}" title="Sectie bewerken">${SVG.edit}</button>
        <span class="mini grip section-grip" title="Slepen om de sectie te verplaatsen">${SVG.grip}</span>
      </span>`}
    </div>
    <div class="cards">
      ${links.map(l => cardHTML(l, terms)).join("")}
      ${searching || links.length ? "" : `<button type="button" class="add-card edit-only" data-add-link="${sec.id}" aria-label="Snelkoppeling toevoegen">+</button>`}
    </div>
  </section>`;
}

function render() {
  if (!cols().some(c => c.id === currentId)) {
    const fromHash = Number(location.hash.slice(1));
    const remembered = Number(localStorage.getItem("linker-collection"));
    currentId = [fromHash, remembered].find(id => cols().some(c => c.id === id)) ?? cols()[0]?.id ?? null;
  }
  renderSidebar();
  renderBoard();
}

function renderSidebar() {
  $("#collections").innerHTML = cols().map((c, i) => {
    const n = c.sections.reduce((sum, s) => sum + s.links.length, 0);
    const icon = state.settings.show_category_icons === "1" && c.icon ? esc(c.icon) : "";
    // In de ingeklapte zijbalk: het icoon, of anders de eerste letter
    const initial = esc([...c.name.trim()][0]?.toUpperCase() || "?");
    return `<li class="col-item" data-cid="${c.id}">
      <button type="button" class="col-btn" data-open="${c.id}" aria-current="${c.id === currentId}"
        title="${esc(c.name)}${i < 9 ? ` (Alt+${i + 1})` : ""}">
        ${icon ? `<span class="col-icon" aria-hidden="true">${icon}</span>` : `<span class="col-initial" aria-hidden="true">${initial}</span>`}
        <span class="col-name">${esc(c.name)}</span>
        <span class="col-down" data-col-down="${c.id}" hidden></span>
        <span class="col-count">${n || ""}</span>
      </button>
      <button type="button" class="mini col-edit edit-only" data-edit-collection="${c.id}"
        title="${esc(c.name)} bewerken" aria-label="${esc(c.name)} bewerken">${SVG.edit}</button>
    </li>`;
  }).join("");
  $$(".col-item", $("#collections")).forEach(li => (li.draggable = state.can_edit));
  applyStatus();
}

function renderBoard() {
  const raw = q.value.trim();
  const terms = raw.toLowerCase().split(/\s+/).filter(Boolean);
  document.body.classList.toggle("searching", terms.length > 0);
  board.classList.toggle("hide-sub", state.settings.show_subtitle !== "1");

  if (terms.length) return renderSearch(raw, terms);

  const col = current();
  $("#col-title").textContent = col ? col.name : "";
  $("#add-section").hidden = !col;
  if (!col) {
    board.innerHTML = `<div class="empty">
      <h2>Nog geen categorieën</h2>
      <p>Maak categorieën zoals Privé en Werk om je snelkoppelingen in te bewaren. Je kunt ook de bladwijzers uit je browser importeren via Instellingen.</p>
      <button type="button" class="btn primary" id="empty-start">Categorie maken</button>
    </div>`;
    $("#empty-start").onclick = () => withEdit(() => openName("collection"));
  } else if (!col.sections.length) {
    board.innerHTML = `<div class="empty"><h2>${esc(col.name)} is nog leeg</h2><p>Voeg een sectie toe om er snelkoppelingen in te zetten.</p>
      <button type="button" class="btn primary edit-only" data-add-section>+ Sectie</button></div>`;
  } else {
    board.innerHTML = col.sections.map(s => sectionHTML(s)).join("");
    if (!col.sections.some(s => s.links.length)) {
      board.insertAdjacentHTML("afterbegin", `<p class="first-tip edit-only">Plak een adres met <kbd>Ctrl</kbd>+<kbd>V</kbd>, sleep een link uit een ander tabblad hierheen, of klik op de <b>+</b> naast een sectie.</p>`);
    }
  }
  selectedId = null;
  hint.textContent = "";
  afterBoard();
}

function afterBoard() {
  $$(".icon img", board).forEach(img => {
    const show = () => {
      const span = img.parentElement;
      span.classList.remove("letter");
      span.style.background = "";
      span.replaceChildren(img);
      img.hidden = false;
    };
    if (img.complete && img.naturalWidth) show();
    else img.addEventListener("load", show, { once: true });
  });
  $$(".card", board).forEach(el => (el.draggable = state.can_edit && !document.body.classList.contains("searching")));
  applyStatus();
}

/* Accentkleur overal: CSS, logo (via CSS) en het icoon in het browsertabblad */
function faviconSVG(accent) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="${accent}"/><path d="M13.5 18.5l5-5M12 15l-2.5 2.5a3.5 3.5 0 0 0 5 5L17 20M15 12l2.5-2.5a3.5 3.5 0 0 1 5 5L20 17" fill="none" stroke="${inkFor(accent)}" stroke-width="2.6" stroke-linecap="round"/></svg>`;
}
function applyAccent(accent) {
  const root = document.documentElement;
  root.style.setProperty("--accent", accent);
  root.style.setProperty("--accent-ink", inkFor(accent));
  if (applyAccent.last === accent) return;
  applyAccent.last = accent;
  $("#favicon").href = "data:image/svg+xml," + encodeURIComponent(faviconSVG(accent));
  const c = accent.slice(1);
  $('link[rel="apple-touch-icon"]').href = `/icon-192.png?c=${c}`;
  $('link[rel="manifest"]').href = `/manifest.webmanifest?c=${c}`;
}

function applySettings() {
  const s = state.settings;
  const root = document.documentElement;
  root.dataset.theme = s.theme;
  root.dataset.size = s.card_size;
  applyAccent(s.accent);
  root.classList.toggle("has-bg", !!s.background);
  root.classList.toggle("bg-dim", s.background_dim === "1");
  root.style.setProperty("--bg-image", s.background ? `url("/background?v=${encodeURIComponent(s.background)}")` : "none");
  document.title = s.title;
  $("#title").textContent = s.title;
  $("#logo").title = s.title;
  $("#clock").hidden = s.show_clock !== "1";
  applyAccess();
  tick();
}
function applyAccess() {
  document.body.classList.toggle("can-edit", !!state.can_edit);
  $("#btn-lock").hidden = !state.locked;
  $("#lock-label").textContent = $("#btn-lock").title =
    state.login_required ? "Uitloggen" : state.can_edit ? "Vergrendelen" : "Ontgrendelen";}

function openCollection(id) {
  currentId = id;
  localStorage.setItem("linker-collection", String(id));
  history.replaceState(null, "", "#" + id);
  if (q.value) q.value = "";
  renderSidebar();
  renderBoard();
}

/* ================================================================ klok */
const timeFmt = new Intl.DateTimeFormat("nl-NL", { hour: "2-digit", minute: "2-digit" });
const dateFmt = new Intl.DateTimeFormat("nl-NL", { weekday: "long", day: "numeric", month: "long" });
function tick() {
  const now = new Date();
  $("#time").textContent = timeFmt.format(now);
  $("#time").dateTime = now.toISOString();
  $("#date").textContent = dateFmt.format(now);
}
setInterval(tick, 10_000);

/* ================================================================ zoeken */
function score(link, terms) {
  const name = link.name.toLowerCase();
  const desc = (link.description || "").toLowerCase();
  const host = hostOf(link.url).toLowerCase();
  let total = 0;
  for (const t of terms) {
    if (name.startsWith(t)) total += 100;
    else if (name.split(/[\s\-_.]+/).some(w => w.startsWith(t))) total += 70;
    else if (name.includes(t)) total += 50;
    else if (desc.includes(t)) total += 25;
    else if (host.includes(t)) total += 15;
    else return 0;
  }
  return total;
}
function highlight(text, terms) {
  let out = esc(text);
  for (const t of terms) {
    const re = new RegExp(`(${esc(t).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "ig");
    out = out.replace(/(<[^>]*>)|([^<]+)/g, (m, tag, txt) => tag || txt.replace(re, "<mark>$1</mark>"));
  }
  return out;
}
function looksLikeAddress(s) {
  return /^(https?:\/\/)?[\w-]+(\.[\w-]+)+(:\d+)?(\/\S*)?$/i.test(s) || /^[\w-]+:\d+(\/\S*)?$/.test(s);
}
const engineName = () => state.engines[state.settings.search_engine] || "het web";

function renderSearch(raw, terms) {
  let best = null, bestScore = 0, html = "";
  for (const c of cols()) {
    for (const s of c.sections) {
      const hits = s.links.filter(l => {
        const sc = score(l, terms);
        if (sc > bestScore) { best = l; bestScore = sc; }
        return sc > 0;
      });
      if (hits.length) html += sectionHTML(s, { terms, links: hits, path: c.name });
    }
  }
  board.innerHTML = html || `<div class="empty"><h2>Geen links gevonden</h2><p>Druk op Enter om op ${esc(engineName())} te zoeken.</p></div>`;
  selectedId = best ? best.id : null;
  afterBoard();
  markSelected();
  if (best) {
    hint.innerHTML = `<kbd>Enter</kbd> opent <b>${esc(best.name)}</b>, <kbd>↑</kbd><kbd>↓</kbd> kiest een andere, <kbd>Shift</kbd>+<kbd>Enter</kbd> zoekt op ${esc(engineName())}.`;
  } else if (looksLikeAddress(raw)) {
    hint.innerHTML = `<kbd>Enter</kbd> opent <b>${esc(raw)}</b>.`;
  } else {
    hint.innerHTML = `<kbd>Enter</kbd> zoekt op ${esc(engineName())}.`;
  }
}
function markSelected() {
  $$(".card.selected", board).forEach(a => a.classList.remove("selected"));
  const el = selectedId != null && board.querySelector(`.card[data-id="${selectedId}"]`);
  if (el) { el.classList.add("selected"); el.scrollIntoView({ block: "nearest" }); }
}
/* Bezoeken tellen: sendBeacon komt ook aan als de pagina meteen wegnavigeert */
function countVisit(id) {
  const link = findLink(id)?.l;
  if (!link) return;
  link.visits = (link.visits || 0) + 1;
  const url = `/api/links/${id}/visit`;
  if (!(navigator.sendBeacon && navigator.sendBeacon(url))) fetch(url, { method: "POST", keepalive: true }).catch(() => {});
}
// Klik, Ctrl/Cmd-klik en middelste muisknop (nieuw tabblad); rechtsklikken telt niet
["click", "auxclick"].forEach(type => document.addEventListener(type, e => {
  const a = e.target.closest?.("a[data-visit]");
  if (a && (e.type === "click" || e.button === 1)) countVisit(Number(a.dataset.visit));
}));

function go(url, newTab) {
  if (newTab) window.open(url, "_blank", "noopener");
  else location.href = url;
}

/* Zoekbalk is verborgen tot je begint te typen */
const topbar = $("#topbar");
function openSearch() {
  topbar.hidden = false;
  q.focus();
}
function closeSearch() {
  q.value = "";
  topbar.hidden = true;
  q.blur();
  renderBoard();
}
q.addEventListener("blur", () => setTimeout(() => {
  if (!q.value.trim() && document.activeElement !== q) closeSearch();
}, 150));
$("#btn-search").addEventListener("click", openSearch);

q.addEventListener("input", () => {
  if (!q.value.trim()) { renderBoard(); return; }
  renderBoard();
});
q.addEventListener("keydown", e => {
  const raw = q.value.trim();
  if (e.key === "Escape") { closeSearch(); return; }
  if ((e.key === "ArrowDown" || e.key === "ArrowUp") && raw) {
    const ids = $$(".card", board).map(el => Number(el.dataset.id));
    if (!ids.length) return;
    e.preventDefault();
    let i = ids.indexOf(selectedId);
    i = e.key === "ArrowDown" ? (i + 1) % ids.length : (i <= 0 ? ids.length - 1 : i - 1);
    selectedId = ids[i];
    markSelected();
    const link = findLink(selectedId)?.l;
    if (link) hint.innerHTML = `<kbd>Enter</kbd> opent <b>${esc(link.name)}</b>.`;
    return;
  }
  if (e.key !== "Enter" || !raw) return;
  e.preventDefault();
  const newTab = state.settings.new_tab === "1" || e.ctrlKey || e.metaKey;
  const link = findLink(selectedId)?.l;
  if (link && !e.shiftKey) { countVisit(link.id); return go(link.url, newTab); }
  if (!e.shiftKey && looksLikeAddress(raw)) return go(/^https?:\/\//i.test(raw) ? raw : "http://" + raw, newTab);
  go(state.search_url.replace("{q}", encodeURIComponent(raw)), newTab);
});

document.addEventListener("keydown", e => {
  if (document.querySelector("dialog[open]")) return;
  if (e.altKey && /^[1-9]$/.test(e.key)) {          // Alt+1…9: naar categorie
    const c = cols()[Number(e.key) - 1];
    if (c) { e.preventDefault(); openCollection(c.id); }
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const tag = document.activeElement?.tagName;
  if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
  if (e.key === "/") { e.preventDefault(); openSearch(); return; }
  if (e.key.length === 1 && /\S/.test(e.key)) openSearch();   // gewoon beginnen met typen
});

/* ================================================================ status */
async function pollStatus() {
  if (state.settings.check_interval === "0") { statusMap = {}; applyStatus(); return; }
  try { statusMap = await api("GET", "/api/status"); applyStatus(); } catch { /* volgende keer */ }
}
function applyStatus() {
  $$("[data-dot]", board).forEach(dot => {
    const st = statusMap[dot.dataset.dot];
    dot.className = "dot" + (st ? (st.up ? " up" : " down") : "");
    dot.title = !st ? "" : st.up ? `Bereikbaar, ${st.code}, ${st.ms} ms`
      : `Niet bereikbaar${st.code ? ", " + st.code : ""}${st.error ? ": " + st.error : ""}`;
  });
  for (const c of cols()) {
    const el = $(`[data-col-down="${c.id}"]`);
    if (!el) continue;
    const down = c.sections.flatMap(s => s.links).filter(l => statusMap[l.id] && !statusMap[l.id].up);
    el.hidden = !down.length;
    el.title = down.length ? `Niet bereikbaar: ${down.map(l => l.name).join(", ")}` : "";
  }
}
setInterval(pollStatus, 20_000);

/* ================================================================ klikken */
async function withEdit(fn) {
  if (!state.can_edit && !(await openUnlock())) return;
  return fn();
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {   // http in het thuisnetwerk: geen clipboard-API
    const ta = Object.assign(document.createElement("textarea"), { value: text });
    ta.style.cssText = "position:fixed;opacity:0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
}

document.addEventListener("click", async e => {
  const t = e.target;
  const open = t.closest("[data-open]");
  if (open) return openCollection(Number(open.dataset.open));
  const copy = t.closest("[data-copy]");
  if (copy) {
    const link = findLink(Number(copy.dataset.copy))?.l;
    if (link) { await copyText(link.url); toast("Adres gekopieerd"); }
    return;
  }
  const editLink = t.closest("[data-edit-link]");
  if (editLink) return openLink(Number(editLink.dataset.editLink));
  const addLink = t.closest("[data-add-link]");
  if (addLink) return openLink(null, Number(addLink.dataset.addLink));
  const editSec = t.closest("[data-edit-section]");
  if (editSec) return openName("section", Number(editSec.dataset.editSection));
  if (t.closest("[data-add-section]") || t.closest("#add-section")) return openName("section");
  const editCol = t.closest("[data-edit-collection]");
  if (editCol) return openName("collection", Number(editCol.dataset.editCollection));
  if (t.closest("#add-collection")) return withEdit(() => openName("collection"));
  const sort = t.closest("[data-sort]");
  if (sort) {
    const byVisits = sort.dataset.sortBy === "visits";
    if (byVisits && !findSection(Number(sort.dataset.sort))?.s.links.some(l => l.visits)) {
      toast("In deze sectie zijn nog geen bezoeken geteld. Linker telt vanaf nu elke klik.", 4500);
      return;
    }
    try {
      await api("POST", `/api/sections/${sort.dataset.sort}/sort${byVisits ? "?by=visits" : ""}`);
      await reload();
      toast(byVisits ? "Gesorteerd op meest bezocht" : "Gesorteerd van A tot Z");
    } catch (err) { toast(err.message); }
  }
});

$("#btn-lock").addEventListener("click", async () => {
  if (state.login_required) {   // hele pagina achter de login: uitloggen
    try { await api("POST", "/api/logout"); } catch { /* toch naar de loginpagina */ }
    location.href = "/login";
    return;
  }
  if (state.can_edit) {
    await api("POST", "/api/logout");
    await reload();
    toast("Bewerken is vergrendeld");
  } else if (await openUnlock()) {
    await reload();
  }
});

/* ================================================================ slepen */
let drag = null;   // { type: 'link'|'section'|'collection', el, id }

document.addEventListener("mousedown", e => {
  const grip = e.target.closest(".section-grip");
  if (grip && state.can_edit) grip.closest(".section").draggable = true;
});
document.addEventListener("dragstart", e => {
  if (!state.can_edit) return;
  const card = e.target.closest?.(".card");
  const sec = e.target.closest?.(".section");
  const col = e.target.closest?.(".col-item");
  if (card) drag = { type: "link", el: card, id: Number(card.dataset.id) };
  else if (sec?.draggable) drag = { type: "section", el: sec, id: Number(sec.dataset.sid) };
  else if (col) drag = { type: "collection", el: col, id: Number(col.dataset.cid) };
  else return;
  e.dataTransfer.effectAllowed = "move";
  e.dataTransfer.setData("text/plain", "");
  requestAnimationFrame(() => drag?.el.classList.add("dragging"));
});
function clearMarks() {
  $$(".drop-before, .drop-after, .drop-into").forEach(el => el.classList.remove("drop-before", "drop-after", "drop-into"));
}
function mark(el, e, horizontal) {
  const r = el.getBoundingClientRect();
  const before = horizontal ? e.clientX < r.left + r.width / 2 : e.clientY < r.top + r.height / 2;
  el.classList.add(before ? "drop-before" : "drop-after");
}
document.addEventListener("dragover", e => {
  if (!drag) return;
  const card = e.target.closest(".card"), sec = e.target.closest(".section"), col = e.target.closest(".col-item");
  let ok = false;
  clearMarks();
  if (drag.type === "link") {
    if (card && card !== drag.el) { mark(card, e, true); ok = true; }
    else if (sec && !card) { sec.classList.add("drop-into"); ok = true; }
    else if (col && Number(col.dataset.cid) !== currentId) { col.classList.add("drop-into"); ok = true; }
  } else if (drag.type === "section") {
    if (sec && sec !== drag.el) { mark(sec, e, false); ok = true; }
    else if (col && Number(col.dataset.cid) !== currentId) { col.classList.add("drop-into"); ok = true; }
  } else if (col && col !== drag.el) { mark(col, e, false); ok = true; }
  if (ok) e.preventDefault();
});
document.addEventListener("drop", async e => {
  if (!drag) return;
  e.preventDefault();
  const d = drag;
  const before = $(".drop-before"), after = $(".drop-after"), into = $(".drop-into");
  clearMarks();
  try {
    if (into?.classList.contains("col-item")) {
      const cid = Number(into.dataset.cid);
      if (d.type === "link") await api("POST", `/api/links/${d.id}/move/${cid}`);
      else {
        const s = findSection(d.id).s;
        await api("PUT", `/api/sections/${d.id}`, { name: s.name, collection_id: cid });
      }
      const name = cols().find(c => c.id === cid)?.name;
      toast(`Verplaatst naar ${name}`);
      return await reload();
    }
    if (before) before.before(d.el);
    else if (after) after.after(d.el);
    else if (into && d.type === "link") {
      const cards = $(".cards", into);
      cards.insertBefore(d.el, $(".add-card", cards) || null);
    } else return;
    await saveOrder(d.type);
  } catch (err) {
    toast(err.message);
    await reload();
  }
});
document.addEventListener("dragend", () => {
  drag?.el.classList.remove("dragging");
  $$(".section[draggable=true]").forEach(s => (s.draggable = false));
  drag = null;
  clearMarks();
});
async function saveOrder(type) {
  const body = {};
  if (type === "collection") body.collections = $$(".col-item").map(li => Number(li.dataset.cid));
  if (type === "section") body.sections = { [currentId]: $$(".section", board).map(s => Number(s.dataset.sid)) };
  if (type === "link") {
    body.links = {};
    $$(".section", board).forEach(s => (body.links[s.dataset.sid] = $$(".card", s).map(c => Number(c.dataset.id))));
  }
  await api("PUT", "/api/order", body);
  await reload();
}

/* ================================================================ dialogen */
$$("dialog").forEach(dlg => $$('[data-act="cancel"]', dlg).forEach(b => b.addEventListener("click", () => dlg.close())));
const setError = (form, msg) => ($(".form-error", form).textContent = msg || "");

/* ---------------------------------------------------------------- link */
const dlgLink = $("#dlg-link"), formLink = $("#form-link");
let linkEditId = null;

let nameTouched = false, afterSave = null;

async function openLink(id, sectionId, prefill = {}) {
  if (!state.can_edit && !(await openUnlock())) return;
  if (!cols().length) { toast("Maak eerst een categorie."); return; }
  linkEditId = id;
  const link = id ? findLink(id)?.l : null;
  $("#dlg-link-title").textContent = link ? "Snelkoppeling bewerken" : "Snelkoppeling toevoegen";
  formLink.section_id.innerHTML = cols().map(c => `<optgroup label="${esc(c.name)}">${
    c.sections.map(s => `<option value="${s.id}">${esc(c.name)} › ${esc(s.name)}</option>`).join("")}</optgroup>`).join("");
  formLink.url.value = link?.url || prefill.url || "";
  formLink.name.value = link?.name || prefill.name || "";
  formLink.name.placeholder = "";
  formLink.description.value = link?.description || "";
  formLink.icon.value = link?.icon || "";
  formLink.check_url.value = link?.check_url || "";
  const firstSection = (current() || cols()[0])?.sections[0]?.id;
  formLink.section_id.value = String(link?.section_id || sectionId || firstSection);
  if (!formLink.section_id.value) formLink.section_id.selectedIndex = 0;
  nameTouched = !!(link || prefill.name);
  formLink.check_enabled.checked = link ? link.check_enabled : false;
  $("details details", formLink).open = !!link?.check_url;
  $("#more-opts").open = !!(link && (link.description || link.icon || link.check_url));
  $('[data-act="delete"]', formLink).hidden = !link;
  $("#name-hint").hidden = !!link;
  setError(formLink);
  updatePreview();
  dlgLink.showModal();
  (formLink.url.value && !link ? formLink.name : link ? formLink.name : formLink.url).focus();
  if (!link && formLink.url.value && !formLink.name.value) fetchTitle();
}

let titleTimer = null, titleFor = "";
function fetchTitle() {
  clearTimeout(titleTimer);
  const url = formLink.url.value.trim();
  if (nameTouched || linkEditId || !url || url === titleFor || !/\w\.\w|:\d/.test(url)) return;
  titleTimer = setTimeout(async () => {
    titleFor = url;
    formLink.name.placeholder = "Titel ophalen…";
    try {
      const info = await api("GET", `/api/page-info?url=${encodeURIComponent(url)}`);
      if (!nameTouched && formLink.url.value.trim() === url) {
        formLink.name.value = info.title || "";
        formLink.name.placeholder = info.title ? "" : hostOf(info.url).replace(/^www\./, "");
        updatePreview();
      }
    } catch { formLink.name.placeholder = ""; }
  }, 500);
}
formLink.url.addEventListener("input", () => {
  titleFor = "";
  fetchTitle();
});
formLink.name.addEventListener("input", () => (nameTouched = formLink.name.value.trim() !== ""));

let previewTimer = null;
function updatePreview() {
  clearTimeout(previewTimer);
  const box = $("#icon-preview");
  const icon = formLink.icon.value.trim();
  const url = formLink.url.value.trim();
  const name = formLink.name.value.trim() || "?";
  const letter = () => {
    box.textContent = name.charAt(0).toUpperCase();
    box.style.background = letterColor(name);
    box.style.color = "#fff";
  };
  box.style.background = ""; box.style.color = "";
  if (isTextIcon(icon)) { box.textContent = icon; return; }
  if (!icon && !url) return letter();
  previewTimer = setTimeout(() => {
    const img = new Image();
    img.onload = () => { box.replaceChildren(img); box.style.background = ""; box.style.color = ""; };
    img.onerror = letter;
    img.src = `/api/icon-preview?icon=${encodeURIComponent(icon)}&url=${encodeURIComponent(url)}`;
  }, 450);
}
["icon", "url", "name"].forEach(n => formLink[n].addEventListener("input", updatePreview));

$("#icon-file").addEventListener("change", async e => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  try {
    const res = await api("POST", "/api/upload/icon", file, true);
    formLink.icon.value = res.icon;
    updatePreview();
  } catch (err) { setError(formLink, err.message); }
});

formLink.addEventListener("submit", async e => {
  e.preventDefault();
  const body = {
    section_id: Number(formLink.section_id.value),
    name: formLink.name.value.trim(),
    url: formLink.url.value.trim(),
    description: formLink.description.value.trim(),
    icon: formLink.icon.value.trim(),
    check_enabled: formLink.check_enabled.checked,
    check_url: formLink.check_url.value.trim(),
  };
  if (!body.url) return setError(formLink, "Vul het adres in.");
  try {
    const wasNew = !linkEditId;
    if (linkEditId) await api("PUT", `/api/links/${linkEditId}`, body);
    else await api("POST", "/api/links", body);
    dlgLink.close();
    if (afterSave) { const go = afterSave; afterSave = null; toast("Opgeslagen in Linker"); setTimeout(() => location.replace(go), 600); return; }
    await reload();
    const sec = findSection(body.section_id);
    if (wasNew && sec && sec.c.id !== currentId) openCollection(sec.c.id);
    if (wasNew) toast(`Opgeslagen in ${sec ? sec.c.name : "Linker"}`);
    setTimeout(pollStatus, 2500);
  } catch (err) { setError(formLink, err.message); }
});
$('[data-act="delete"]', formLink).addEventListener("click", async () => {
  const link = findLink(linkEditId)?.l;
  if (!link || !confirm(`Snelkoppeling ${link.name} verwijderen?`)) return;
  try { await api("DELETE", `/api/links/${linkEditId}`); dlgLink.close(); await reload(); }
  catch (err) { setError(formLink, err.message); }
});

/* ---------------------------------------------------------------- collectie of sectie */
const dlgName = $("#dlg-name"), formName = $("#form-name");
let nameCtx = null;   // { kind: 'collection'|'section', id }

async function openName(kind, id) {
  if (!state.can_edit && !(await openUnlock())) return;
  nameCtx = { kind, id: id || null };
  const isCol = kind === "collection";
  const item = id ? (isCol ? cols().find(c => c.id === id) : findSection(id)?.s) : null;
  $("#dlg-name-title").textContent = (item ? (isCol ? "Categorie" : "Sectie") + " bewerken" : (isCol ? "Categorie" : "Sectie") + " toevoegen");
  formName.name.value = item?.name || "";
  formName.name.placeholder = isCol ? "Hobby" : "Tools";
  formName.icon.value = isCol ? item?.icon || "" : "";
  $("#name-icon-row").hidden = !isCol || state.settings.show_category_icons !== "1";
  $("#name-collection-row").hidden = isCol || !item;
  formName.collection_id.innerHTML = cols().map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join("");
  formName.collection_id.value = String(item?.collection_id || currentId);
  $('[data-act="delete"]', formName).hidden = !item;
  setError(formName);
  dlgName.showModal();
  formName.name.focus();
}
formName.addEventListener("submit", async e => {
  e.preventDefault();
  const name = formName.name.value.trim();
  if (!name) return setError(formName, "Geef een naam op.");
  const { kind, id } = nameCtx;
  try {
    if (kind === "collection") {
      const body = { name, icon: formName.icon.value.trim() };
      if (id) await api("PUT", `/api/collections/${id}`, body);
      else currentId = (await api("POST", "/api/collections", body)).id;
    } else {
      const body = { name, collection_id: id ? Number(formName.collection_id.value) : currentId };
      if (id) await api("PUT", `/api/sections/${id}`, body);
      else await api("POST", "/api/sections", body);
    }
    dlgName.close();
    await reload();
    if (kind === "collection" && !id) openCollection(currentId);
  } catch (err) { setError(formName, err.message); }
});
$('[data-act="delete"]', formName).addEventListener("click", async () => {
  const { kind, id } = nameCtx;
  if (kind === "collection") {
    const c = cols().find(x => x.id === id);
    const n = c.sections.reduce((sum, s) => sum + s.links.length, 0);
    if (!confirm(`Categorie ${c.name} verwijderen?${n ? ` De ${n} snelkoppelingen erin worden ook verwijderd.` : ""}`)) return;
    try { await api("DELETE", `/api/collections/${id}`); dlgName.close(); currentId = null; await reload(); }
    catch (err) { setError(formName, err.message); }
  } else {
    const s = findSection(id).s;
    if (!confirm(`Sectie ${s.name} verwijderen?${s.links.length ? ` De ${s.links.length} snelkoppelingen erin worden ook verwijderd.` : ""}`)) return;
    try { await api("DELETE", `/api/sections/${id}`); dlgName.close(); await reload(); }
    catch (err) { setError(formName, err.message); }
  }
});

/* ---------------------------------------------------------------- ontgrendelen */
const dlgUnlock = $("#dlg-unlock"), formUnlock = $("#form-unlock");
function openUnlock() {
  return new Promise(resolve => {
    formUnlock.password.value = "";
    setError(formUnlock);
    let done = false;
    const finish = ok => { if (!done) { done = true; resolve(ok); } };
    dlgUnlock.addEventListener("close", () => finish(false), { once: true });
    formUnlock.onsubmit = async e => {
      e.preventDefault();
      try {
        await api("POST", "/api/login", { password: formUnlock.password.value });
        state.can_edit = true;
        applyAccess();
        renderSidebar();
        afterBoard();
        finish(true);
        dlgUnlock.close();
      } catch (err) { setError(formUnlock, err.message); }
    };
    dlgUnlock.showModal();
    formUnlock.password.focus();
  });
}

/* ---------------------------------------------------------------- instellingen */
const dlgSettings = $("#dlg-settings"), formSettings = $("#form-settings");
let settingsSnapshot = null;

$("#swatches").innerHTML = SWATCHES.map(c => `<button type="button" class="swatch" style="background:${c}" data-color="${c}" title="${c}"></button>`).join("");
$("#swatches").addEventListener("click", e => {
  const c = e.target.closest("[data-color]")?.dataset.color;
  if (!c) return;
  formSettings.accent.value = c;
  previewLook();
});
function previewLook() {
  const root = document.documentElement;
  root.dataset.theme = formSettings.theme.value;
  root.dataset.size = formSettings.card_size.value;
  applyAccent(formSettings.accent.value);
  root.classList.toggle("bg-dim", formSettings.background_dim.checked);
}
["accent"].forEach(n => formSettings[n].addEventListener("input", previewLook));
["theme", "card_size", "background_dim"].forEach(n => formSettings[n].addEventListener("change", previewLook));
formSettings.search_engine.addEventListener("change", () => {
  $("#custom-engine").hidden = formSettings.search_engine.value !== "custom";
});

function fillSettings() {
  const s = state.settings;
  formSettings.search_engine.innerHTML = Object.entries(state.engines).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("");
  formSettings.title.value = s.title;
  formSettings.card_size.value = s.card_size;
  formSettings.show_subtitle.checked = s.show_subtitle === "1";
  formSettings.show_category_icons.checked = s.show_category_icons === "1";
  formSettings.show_clock.checked = s.show_clock === "1";
  formSettings.new_tab.checked = s.new_tab === "1";
  formSettings.theme.value = s.theme;
  formSettings.accent.value = s.accent;
  formSettings.background_dim.checked = s.background_dim === "1";
  formSettings.search_engine.value = s.search_engine;
  formSettings.search_custom.value = s.search_custom;
  $("#custom-engine").hidden = s.search_engine !== "custom";
  $("#bg-remove").hidden = !s.background;
  $("#bg-dim-row").hidden = !s.background;
  const interval = formSettings.check_interval;
  if (![...interval.options].some(o => o.value === s.check_interval)) interval.add(new Option(`${s.check_interval} seconden`, s.check_interval));
  interval.value = s.check_interval;
  formSettings.new_password.value = "";
  formSettings.remove_password.checked = false;
  formSettings.require_login.checked = s.require_login === "1";
  $("#pw-state").textContent = state.login_required
    ? "Je startpagina is afgeschermd: zonder in te loggen ziet niemand je snelkoppelingen."
    : state.locked
    ? "Bewerken is beveiligd. Iedereen kan de startpagina gebruiken, maar alleen met het wachtwoord kun je links en instellingen wijzigen."
    : "Iedereen die de startpagina opent, kan nu ook links en instellingen wijzigen. Stel een wachtwoord in om dat af te schermen.";
  $("#pw-remove").hidden = !state.locked;
}

async function openSettings() {
  if (!state.can_edit && !(await openUnlock())) return;
  settingsSnapshot = { ...state.settings };
  fillSettings();
  setError(formSettings);
  dlgSettings.showModal();
}
$("#btn-settings").addEventListener("click", openSettings);
dlgSettings.addEventListener("close", () => {
  if (settingsSnapshot) applySettings();   // geannuleerd: voorbeeldweergave terugdraaien
  settingsSnapshot = null;
});

formSettings.addEventListener("submit", async e => {
  e.preventDefault();
  const body = {
    title: formSettings.title.value,
    card_size: formSettings.card_size.value,
    show_subtitle: formSettings.show_subtitle.checked,
    show_category_icons: formSettings.show_category_icons.checked,
    show_clock: formSettings.show_clock.checked,
    new_tab: formSettings.new_tab.checked,
    theme: formSettings.theme.value,
    accent: formSettings.accent.value,
    background_dim: formSettings.background_dim.checked,
    search_engine: formSettings.search_engine.value,
    search_custom: formSettings.search_custom.value,
    check_interval: Number(formSettings.check_interval.value),
  };
  if (formSettings.remove_password.checked) body.remove_password = true;
  else {
    if (formSettings.new_password.value) body.new_password = formSettings.new_password.value;
    body.require_login = formSettings.require_login.checked;
  }
  try {
    state = await api("PUT", "/api/settings", body);
    settingsSnapshot = null;
    dlgSettings.close();
    applySettings();
    render();
    pollStatus();
    toast("Instellingen opgeslagen");
  } catch (err) { setError(formSettings, err.message); }
});

$("#bg-file").addEventListener("change", async e => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  try {
    state = await api("POST", "/api/upload/background", file, true);
    settingsSnapshot = { ...state.settings };
    applySettings();
    previewLook();
    $("#bg-remove").hidden = false;
    $("#bg-dim-row").hidden = false;
    setError(formSettings);
  } catch (err) { setError(formSettings, err.message); }
});
$("#bg-remove").addEventListener("click", async () => {
  try {
    state = await api("DELETE", "/api/upload/background");
    settingsSnapshot = { ...state.settings };
    applySettings();
    previewLook();
    $("#bg-remove").hidden = true;
    $("#bg-dim-row").hidden = true;
  } catch (err) { setError(formSettings, err.message); }
});

$("#import-file").addEventListener("change", async e => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  try {
    const info = await api("POST", "/api/import/inspect", file, true);
    const what = `${info.links} snelkoppelingen in ${info.collections} ${info.collections === 1 ? "categorie" : "categorieën"}`;
    let mode = "append";
    if (info.replace) {
      if (!confirm(`Linker-back-up met ${what}.\n\nOK vervangt al je huidige snelkoppelingen en instellingen. Annuleren voegt de back-up toe zonder iets te verwijderen.`)) mode = "append";
      else mode = "replace";
    } else if (!confirm(`${info.kind}: ${what}. Toevoegen als nieuwe ${info.collections === 1 ? "categorie" : "categorieën"}?`)) {
      return;
    }
    const res = await api("POST", `/api/import?mode=${mode}`, file, true);
    state = res.state;
    settingsSnapshot = null;
    dlgSettings.close();
    currentId = null;
    applySettings();
    render();
    pollStatus();
    toast(`${res.links} snelkoppelingen geïmporteerd uit ${res.kind}`);
  } catch (err) { setError(formSettings, err.message); }
});

/* ================================================================ snel toevoegen */
const URLISH = /^(https?:\/\/\S+|[\w-]+(\.[\w-]+)+(:\d+)?(\/\S*)?|(\d{1,3}\.){3}\d{1,3}(:\d+)?(\/\S*)?)$/i;

// Ctrl+V met een adres ergens op de pagina (niet in een invoerveld)
document.addEventListener("paste", e => {
  if (document.querySelector("dialog[open]")) return;
  const tag = document.activeElement?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA") return;
  const text = (e.clipboardData?.getData("text") || "").trim();
  if (!URLISH.test(text)) return;
  e.preventDefault();
  openLink(null, null, { url: text });
});

// Een link of adres uit een ander tabblad of de adresbalk op de pagina laten vallen
document.addEventListener("dragover", e => {
  if (drag || !e.dataTransfer?.types.includes("text/uri-list")) return;
  e.preventDefault();
  document.body.classList.add("drop-url");
});
document.addEventListener("dragleave", e => { if (!e.relatedTarget) document.body.classList.remove("drop-url"); });
document.addEventListener("drop", e => {
  document.body.classList.remove("drop-url");
  if (drag || !e.dataTransfer?.types.includes("text/uri-list")) return;
  e.preventDefault();
  const url = e.dataTransfer.getData("text/uri-list").split("\n").find(l => l && !l.startsWith("#"))?.trim();
  if (!url) return;
  const sec = e.target.closest?.(".section");
  openLink(null, sec ? Number(sec.dataset.sid) : null, { url });
}, true);

// Bladwijzer-knop: opent Linker met ?add=<adres>&title=<titel>&back=1
$("#bookmarklet").href = `javascript:(()=>{location.href=${JSON.stringify(location.origin + "/?add=")}+encodeURIComponent(location.href)+"&title="+encodeURIComponent(document.title)+"&back=1"})()`;
$("#bookmarklet").addEventListener("click", e => { e.preventDefault(); toast("Sleep deze knop naar je bladwijzerbalk."); });

function handleAddParam() {
  const p = new URLSearchParams(location.search);
  const url = p.get("add");
  if (!url) return;
  history.replaceState(null, "", location.pathname + location.hash);
  if (p.get("back") === "1" && /^https?:\/\//i.test(url)) afterSave = url;
  openLink(null, null, { url, name: (p.get("title") || "").slice(0, 80) });
  dlgLink.addEventListener("close", () => { if (afterSave) { const go = afterSave; afterSave = null; location.replace(go); } }, { once: true });
}

/* ================================================================ zijbalk-breedte */
const SIDE_MIN = 170, SIDE_MAX = 440, SIDE_DEFAULT = 236;
const resizer = $("#resizer");
function sideWidth() { return $(".sidebar").getBoundingClientRect().width; }
function setSideWidth(w, save = true) {
  w = Math.round(Math.min(SIDE_MAX, Math.max(SIDE_MIN, w)));
  document.documentElement.style.setProperty("--side-w", w + "px");
  resizer.setAttribute("aria-valuenow", String(w));
  if (save) try { localStorage.setItem("linker-sidebar", String(w)); } catch { /* geen opslag */ }
}
resizer.setAttribute("aria-valuemin", String(SIDE_MIN));
resizer.setAttribute("aria-valuemax", String(SIDE_MAX));
resizer.addEventListener("pointerdown", e => {
  e.preventDefault();
  resizer.setPointerCapture(e.pointerId);
  document.body.classList.add("resizing");
  const startX = e.clientX, startW = sideWidth();
  const move = ev => setSideWidth(startW + ev.clientX - startX, false);
  const up = ev => {
    resizer.removeEventListener("pointermove", move);
    document.body.classList.remove("resizing");
    setSideWidth(startW + ev.clientX - startX);
  };
  resizer.addEventListener("pointermove", move);
  resizer.addEventListener("pointerup", up, { once: true });
});
resizer.addEventListener("dblclick", () => {
  document.documentElement.style.removeProperty("--side-w");
  try { localStorage.removeItem("linker-sidebar"); } catch { /* geen opslag */ }
});
resizer.addEventListener("keydown", e => {
  if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
  e.preventDefault();
  setSideWidth(sideWidth() + (e.key === "ArrowRight" ? 16 : -16));
});
resizer.setAttribute("aria-valuenow", String(Math.round(sideWidth())));

/* ================================================================ zijbalk inklappen */
const collapseBtn = $("#btn-collapse");
function setCollapsed(on) {
  document.documentElement.classList.toggle("side-collapsed", on);
  collapseBtn.setAttribute("aria-expanded", String(!on));
  collapseBtn.title = on ? "Zijbalk uitklappen" : "Zijbalk inklappen";
  $("span", collapseBtn).textContent = on ? "Uitklappen" : "Inklappen";
  try { localStorage.setItem("linker-sidebar-collapsed", on ? "1" : "0"); } catch { /* geen opslag */ }
}
collapseBtn.addEventListener("click", () => setCollapsed(!document.documentElement.classList.contains("side-collapsed")));
setCollapsed(document.documentElement.classList.contains("side-collapsed"));

/* ================================================================ start */
applySettings();
render();
pollStatus();
window.addEventListener("hashchange", () => {
  const id = Number(location.hash.slice(1));
  if (id && id !== currentId && cols().some(c => c.id === id)) openCollection(id);
});
handleAddParam();
