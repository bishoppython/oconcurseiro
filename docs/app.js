// Portal do oConcurseiro: carrega data/concursos.json e filtra tudo no navegador.
const POR_PAGINA = 30;
const URGENTE_DIAS = 7;
const $ = (id) => document.getElementById(id);
const estado = { q: "", uf: "", escolaridade: "", status: "", ordem: "prazo", limite: POR_PAGINA };
let dados = { concursos: [], ufs: {} };

const semAcento = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const num = (n) => n.toLocaleString("pt-BR");
const reais = (v) => v >= 1000 ? `R$ ${num(+(v / 1000).toFixed(1))} mil` : `R$ ${num(v)}`;
const dataBR = (iso) => iso ? iso.split("-").reverse().join("/") : "";
const esc = (s) => (s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// "hoje" no fuso do usuário, em AAAA-MM-DD, para comparar com as datas do JSON
const hoje = (() => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); })();
const diasAte = (iso) => Math.round((new Date(iso) - new Date(hoje)) / 86400000);

// situação vista pelo usuário: o PCI às vezes mantém na lista concursos cujo prazo já passou
function situacao(c) {
  if (c.status === "aberto" && c.inscricao_fim && c.inscricao_fim < hoje) return "encerrado";
  return c.status;
}
const ROTULO = { aberto: "Aberto", previsto: "Previsto", suspenso: "Suspenso", encerrado: "Encerrado" };

function destacar(texto, termos) {
  if (!termos.length) return esc(texto);
  // marca os termos ignorando acentos, mapeando as posições do texto sem acento para o original
  const base = semAcento(texto);
  const marcas = [];
  for (const t of termos) {
    let i = base.indexOf(t);
    while (i !== -1) { marcas.push([i, i + t.length]); i = base.indexOf(t, i + t.length); }
  }
  if (!marcas.length) return esc(texto);
  marcas.sort((a, b) => a[0] - b[0]);
  let out = "", pos = 0;
  for (const [ini, fim] of marcas) {
    if (ini < pos) continue;
    out += esc(texto.slice(pos, ini)) + "<mark>" + esc(texto.slice(ini, fim)) + "</mark>";
    pos = fim;
  }
  return out + esc(texto.slice(pos));
}

// peso de cada situação na ordem "inscrições terminando": abertos primeiro, encerrados por último
const PESO = { aberto: 0, suspenso: 1, previsto: 2, encerrado: 3 };

function filtrar() {
  const termos = semAcento(estado.q).split(/\s+/).filter(Boolean);
  const lista = dados.concursos.filter((c) =>
    (!estado.status || c._situacao === estado.status) &&
    // escolher um estado também mostra os nacionais, que valem para todos
    (!estado.uf || c.ufs.includes(estado.uf) || (estado.uf !== "br" && c.nacional)) &&
    (!estado.escolaridade || c._escolaridade.includes(estado.escolaridade)) &&
    termos.every((t) => c._busca.includes(t)));
  const ordens = {
    prazo: (a, b) => PESO[a._situacao] - PESO[b._situacao] ||
      (a.inscricao_fim || "9999").localeCompare(b.inscricao_fim || "9999") ||
      (b.publicado || "").localeCompare(a.publicado || ""),
    vagas: (a, b) => (b.vagas ?? -1) - (a.vagas ?? -1),
    salario: (a, b) => (b.salario_max ?? -1) - (a.salario_max ?? -1),
    recentes: (a, b) => (b.publicado || "").localeCompare(a.publicado || ""),
  };
  return { lista: lista.sort(ordens[estado.ordem]), termos };
}

function prazo(c) {
  if (c._situacao === "previsto") return c.publicado ? `<span>📰 notícia de ${dataBR(c.publicado)}</span>` : "";
  if (c._situacao === "suspenso") return '<span class="prazo encerrado">⏸️ Inscrições suspensas</span>';
  if (!c.inscricao_fim) return "";
  if (c._situacao === "encerrado") return `<span class="prazo encerrado">Inscrições encerradas em ${dataBR(c.inscricao_fim)}</span>`;
  const dias = diasAte(c.inscricao_fim);
  if (c.inscricao_inicio && c.inscricao_inicio > hoje) {
    return `<span class="prazo">📝 Inscrições de ${dataBR(c.inscricao_inicio)} a ${dataBR(c.inscricao_fim)}</span>`;
  }
  const falta = dias === 0 ? "último dia!" : dias === 1 ? "falta 1 dia" : `faltam ${dias} dias`;
  return `<span class="prazo${dias <= URGENTE_DIAS ? " urgente" : ""}">📝 Inscrições até ${dataBR(c.inscricao_fim)} · ${falta}</span>`;
}

function cartao(c, termos) {
  const ufs = c.nacional ? '<span class="uf">Nacional</span>'
    : c.ufs.map((u) => `<span class="uf">${u.toUpperCase()}</span>`).join(" ");
  const vagas = c.vagas != null ? `<span><b>${num(c.vagas)}</b> vaga${c.vagas === 1 ? "" : "s"}</span>`
    : `<span><b>${esc(c.vagas_texto || "Várias")}</b>${c.vagas_texto === "Cadastro reserva" ? "" : " vagas"}</span>`;
  const salario = c.salario_max ? `<span>até <b>${reais(c.salario_max)}</b></span>` : "";
  const cargos = c.cargos ? `<p class="cargos">${destacar(c.cargos, termos)}${c.escolaridade ? ` <span>· ${esc(c.escolaridade)}</span>` : ""}</p>` : "";
  return `<a class="card" href="${esc(c.link)}" target="_blank" rel="noopener">
    <div class="card-top"><h2>${destacar(c.orgao, termos)}</h2>
      <span class="badge ${c._situacao}">${ROTULO[c._situacao]}</span></div>
    <p>${destacar(c.titulo, termos)}</p>
    ${cargos}
    ${prazo(c)}
    <div class="facts">${ufs}${vagas}${salario}</div>
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
  const conta = (s) => cs.filter((c) => c._situacao === s).length;
  const urgentes = cs.filter((c) => c._situacao === "aberto" && c.inscricao_fim && diasAte(c.inscricao_fim) <= URGENTE_DIAS).length;
  const quando = new Date(dados.atualizado).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  $("stats").innerHTML = [
    [num(conta("aberto")), "inscrições abertas"], [num(urgentes), `encerram em ${URGENTE_DIAS} dias`],
    [num(conta("previsto")), "previstos"], [quando, "última atualização"],
  ].map(([b, s]) => `<div class="stat"><b>${b}</b><span>${s}</span></div>`).join("");
}

const CAMPOS = { q: "q", uf: "uf", escolaridade: "escolaridade", status: "status", ordem: "ordem" };
const PADRAO = { q: "", uf: "", escolaridade: "", status: "", ordem: "prazo" };

function salvarNaUrl() {
  const p = new URLSearchParams();
  for (const k in CAMPOS) if (estado[k] !== PADRAO[k]) p.set(k, estado[k]);
  history.replaceState(null, "", p.toString() ? `?${p}` : location.pathname);
}

function lerDaUrl() {
  const p = new URLSearchParams(location.search);
  const valido = (k, opcoes) => opcoes.includes(p.get(k)) ? p.get(k) : PADRAO[k];
  estado.q = p.get("q") || "";
  estado.uf = valido("uf", Object.keys(dados.ufs));
  estado.escolaridade = valido("escolaridade", ["fundamental", "medio", "tecnico", "superior"]);
  estado.status = valido("status", ["aberto", "previsto"]);
  estado.ordem = valido("ordem", ["prazo", "vagas", "salario", "recentes"]);
  for (const k of ["q", "uf", "escolaridade", "ordem"]) $(k).value = estado[k];
  document.querySelectorAll(".chips button").forEach((b) => b.classList.toggle("on", b.dataset.status === estado.status));
}

function ligar() {
  let espera;
  $("q").addEventListener("input", (e) => {
    clearTimeout(espera);
    espera = setTimeout(() => { estado.q = e.target.value.trim(); estado.limite = POR_PAGINA; render(); }, 150);
  });
  for (const k of ["uf", "escolaridade", "ordem"]) {
    $(k).addEventListener("change", (e) => { estado[k] = e.target.value; estado.limite = POR_PAGINA; render(); });
  }
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
  for (const c of dados.concursos) {
    c._situacao = situacao(c);
    c._busca = semAcento(`${c.orgao} ${c.titulo} ${c.cargos || ""}`);
    c._escolaridade = semAcento(c.escolaridade);
  }
  const opcoes = Object.entries(dados.ufs).sort(([a, x], [b, y]) => a === "br" ? -1 : b === "br" ? 1 : x.localeCompare(y));
  $("uf").insertAdjacentHTML("beforeend", opcoes.map(([uf, nome]) =>
    `<option value="${uf}">${uf === "br" ? "Só nacionais" : `${nome} (${uf.toUpperCase()})`}</option>`).join(""));
  lerDaUrl();
  ligar();
  stats();
  render();
}

iniciar();
