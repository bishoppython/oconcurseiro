// Portal do oConcurseiro: carrega data/concursos.json e filtra tudo no navegador.
const POR_PAGINA = 30;
const $ = (id) => document.getElementById(id);
const estado = { q: "", uf: "", status: "", ordem: "recentes", limite: POR_PAGINA };
let dados = { concursos: [], ufs: {} };

const semAcento = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const num = (n) => n.toLocaleString("pt-BR");
const reais = (v) => v >= 1000 ? `R$ ${num(+(v / 1000).toFixed(1))} mil` : `R$ ${num(v)}`;
const dataBR = (iso) => iso ? iso.split("-").reverse().join("/") : "";
const esc = (s) => (s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function destacar(texto, termos) {
  let html = esc(texto);
  if (!termos.length) return html;
  // marca os termos ignorando acentos, mapeando as posições do texto sem acento para o original
  const base = semAcento(texto);
  const marcas = [];
  for (const t of termos) {
    let i = base.indexOf(t);
    while (i !== -1) { marcas.push([i, i + t.length]); i = base.indexOf(t, i + t.length); }
  }
  if (!marcas.length) return html;
  marcas.sort((a, b) => a[0] - b[0]);
  let out = "", pos = 0;
  for (const [ini, fim] of marcas) {
    if (ini < pos) continue;
    out += esc(texto.slice(pos, ini)) + "<mark>" + esc(texto.slice(ini, fim)) + "</mark>";
    pos = fim;
  }
  return out + esc(texto.slice(pos));
}

function filtrar() {
  const termos = semAcento(estado.q).split(/\s+/).filter(Boolean);
  let lista = dados.concursos.filter((c) =>
    (!estado.status || c.status === estado.status) &&
    // escolher um estado também mostra os nacionais, que valem para todos
    (!estado.uf || c.ufs.includes(estado.uf) || (estado.uf !== "br" && c.nacional)) &&
    termos.every((t) => c._busca.includes(t)));
  const ordens = {
    recentes: (a, b) => (b.publicado || "").localeCompare(a.publicado || ""),
    vagas: (a, b) => (b.vagas ?? -1) - (a.vagas ?? -1),
    salario: (a, b) => (b.salario_max ?? -1) - (a.salario_max ?? -1),
  };
  return { lista: lista.sort(ordens[estado.ordem]), termos };
}

function cartao(c, termos) {
  const ufs = c.nacional ? '<span class="uf">Nacional</span>'
    : c.ufs.map((u) => `<span class="uf">${u.toUpperCase()}</span>`).join(" ");
  const vagas = c.vagas != null ? `<span><b>${num(c.vagas)}</b> vagas</span>` : `<span><b>${esc(c.vagas_texto || "Várias")}</b> vagas</span>`;
  const salario = c.salario_max ? `<span>até <b>${reais(c.salario_max)}</b></span>` : "";
  return `<a class="card" href="${esc(c.link)}" target="_blank" rel="noopener">
    <div class="card-top"><h2>${destacar(c.orgao, termos)}</h2>
      <span class="badge ${c.status}">${c.status === "aberto" ? "Aberto" : "Previsto"}</span></div>
    <p>${destacar(c.titulo, termos)}</p>
    <div class="facts">${ufs}${vagas}${salario}<span>📅 ${dataBR(c.publicado)}</span></div>
  </a>`;
}

function render() {
  const { lista, termos } = filtrar();
  const visiveis = lista.slice(0, estado.limite);
  $("list").innerHTML = visiveis.length ? visiveis.map((c) => cartao(c, termos)).join("")
    : '<p class="empty">Nenhum concurso encontrado com esses filtros. Tente outro termo ou estado.</p>';
  const vagas = lista.reduce((s, c) => s + (c.vagas || 0), 0);
  $("count").textContent = `${num(lista.length)} concurso${lista.length === 1 ? "" : "s"} · ${num(vagas)} vagas informadas`;
  $("more").hidden = lista.length <= estado.limite;
  salvarNaUrl();
}

function stats() {
  const cs = dados.concursos;
  const abertos = cs.filter((c) => c.status === "aberto").length;
  const vagas = cs.reduce((s, c) => s + (c.vagas || 0), 0);
  const quando = new Date(dados.atualizado).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  $("stats").innerHTML = [
    [num(abertos), "abertos"], [num(cs.length - abertos), "previstos"],
    [num(vagas), "vagas"], [quando, "última atualização"],
  ].map(([b, s]) => `<div class="stat"><b>${b}</b><span>${s}</span></div>`).join("");
}

function salvarNaUrl() {
  const p = new URLSearchParams();
  if (estado.q) p.set("q", estado.q);
  if (estado.uf) p.set("uf", estado.uf);
  if (estado.status) p.set("status", estado.status);
  if (estado.ordem !== "recentes") p.set("ordem", estado.ordem);
  history.replaceState(null, "", p.toString() ? `?${p}` : location.pathname);
}

function lerDaUrl() {
  const p = new URLSearchParams(location.search);
  estado.q = p.get("q") || "";
  estado.uf = dados.ufs[p.get("uf")] ? p.get("uf") : "";
  estado.status = ["aberto", "previsto"].includes(p.get("status")) ? p.get("status") : "";
  estado.ordem = ["vagas", "salario"].includes(p.get("ordem")) ? p.get("ordem") : "recentes";
  $("q").value = estado.q;
  $("uf").value = estado.uf;
  $("ordem").value = estado.ordem;
  document.querySelectorAll(".chips button").forEach((b) => b.classList.toggle("on", b.dataset.status === estado.status));
}

function ligar() {
  let espera;
  $("q").addEventListener("input", (e) => {
    clearTimeout(espera);
    espera = setTimeout(() => { estado.q = e.target.value.trim(); estado.limite = POR_PAGINA; render(); }, 150);
  });
  $("uf").addEventListener("change", (e) => { estado.uf = e.target.value; estado.limite = POR_PAGINA; render(); });
  $("ordem").addEventListener("change", (e) => { estado.ordem = e.target.value; render(); });
  document.querySelectorAll(".chips button").forEach((b) => b.addEventListener("click", () => {
    estado.status = b.dataset.status;
    document.querySelectorAll(".chips button").forEach((x) => x.classList.toggle("on", x === b));
    estado.limite = POR_PAGINA;
    render();
  }));
  $("more").addEventListener("click", () => { estado.limite += POR_PAGINA; render(); });
}

async function iniciar() {
  $("list").innerHTML = '<p class="empty">Carregando concursos…</p>';
  try {
    const r = await fetch("data/concursos.json", { cache: "no-cache" });
    dados = await r.json();
  } catch {
    $("list").innerHTML = '<p class="empty">Não foi possível carregar os concursos agora. Tente recarregar a página.</p>';
    return;
  }
  for (const c of dados.concursos) c._busca = semAcento(`${c.orgao} ${c.titulo}`);
  const opcoes = Object.entries(dados.ufs).sort(([a, x], [b, y]) => a === "br" ? -1 : b === "br" ? 1 : x.localeCompare(y));
  $("uf").insertAdjacentHTML("beforeend", opcoes.map(([uf, nome]) =>
    `<option value="${uf}">${uf === "br" ? "Só nacionais" : `${nome} (${uf.toUpperCase()})`}</option>`).join(""));
  lerDaUrl();
  ligar();
  stats();
  render();
}

iniciar();
