"""Concursos com inscrições abertas do PCI Concursos (pciconcursos.com.br/concursos/).

Uma única página traz o país inteiro, agrupado por UF, com prazo de inscrição, cargos,
escolaridade, vagas e salário de cada concurso.
"""

import re

from bs4 import BeautifulSoup

from extrator.ufs import ufs_citadas

URL = "https://www.pciconcursos.com.br/concursos/"

RE_DATA = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
# início de um período: "07/11 a", "10 a", "05/11/2026 a"
RE_INICIO = re.compile(r"(\d{1,2})(?:/(\d{1,2}))?(?:/(\d{4}))?\s+a\s")
RE_VAGAS = re.compile(r"([\d.]+)\s+vagas?", re.I)
RE_SALARIO = re.compile(r"R\$\s*([\d.]+(?:,\d+)?)")
RE_CR = re.compile(r"cadastro|\bCR\b", re.I)


def iso(dia, mes, ano):
    return f"{int(ano):04d}-{int(mes):02d}-{int(dia):02d}"


def inscricao(texto):
    """'07/11 a 23/11/2026' -> ('2026-11-07', '2026-11-23'); 'Suspenso' -> (None, None)."""
    datas = RE_DATA.findall(texto)
    if not datas:
        return None, None
    dia, mes, ano = datas[-1]
    fim = iso(dia, mes, ano)
    inicio = RE_INICIO.search(texto)
    if not inicio:
        return None, fim
    d, m, a = inicio.groups()
    return iso(d, m or mes, a or ano), fim


def detalhes(cd):
    """Bloco 'cd': '184 vagas até R$ 32.070,88<br><span>cargos<br><span>escolaridade</span></span>'."""
    resumo = cd.find(string=True, recursive=False) or ""
    externo = cd.find("span")
    interno = externo.find("span") if externo else None
    cargos = externo.find(string=True, recursive=False) if externo else ""
    vagas = RE_VAGAS.search(resumo)
    salario = RE_SALARIO.search(resumo)
    return {
        "vagas": int(vagas.group(1).replace(".", "")) if vagas else None,
        "vagas_texto": vagas.group(1) if vagas else ("Cadastro reserva" if RE_CR.search(resumo) else "Várias"),
        "salario_max": float(salario.group(1).replace(".", "").replace(",", ".")) if salario else None,
        "cargos": (cargos or "").strip(),
        "escolaridade": interno.get_text(strip=True) if interno else "",
    }


def extrair(html):
    soup = BeautifulSoup(html, "html.parser")
    concursos, secao = [], None
    # percorre a página em ordem: cada "ua" abre a seção de uma UF, cada "ca" é um concurso
    for div in soup.find_all("div", class_=["ua", "ca"]):
        classes = div.get("class", [])
        if "ua" in classes:
            secao = (div.get("id") or "").lower()
            continue
        link = div.find("a")
        item = div.parent
        if not link or not link.get("href") or not secao:
            continue
        cc, cd, ce = (item.find("div", class_=c) for c in ("cc", "cd", "ce"))
        prazo = ce.get_text(" ", strip=True) if ce else ""
        inicio, fim = inscricao(prazo)
        titulo = (link.get("title") or "").strip()
        uf = (cc.get_text(strip=True).lower() if cc else "") or secao
        ufs = [uf]
        if secao == "nacional":
            # a seção "Nacional" do PCI também traz federais de poucos estados
            # ("Câmara dos Deputados - DF", "Marinha - AM e RO"): só é nacional se nenhum estado for citado
            ufs = ufs_citadas(titulo, link.get_text(strip=True)) or ["br"]
        nacional = ufs == ["br"]
        concursos.append({
            "orgao": link.get_text(strip=True),
            "titulo": titulo,
            "link": link["href"].strip(),
            **(detalhes(cd) if cd else {"vagas": None, "vagas_texto": "Várias", "salario_max": None,
                                        "cargos": "", "escolaridade": ""}),
            "status": "suspenso" if "suspens" in prazo.lower() else "aberto",
            "inscricao_inicio": inicio,
            "inscricao_fim": fim,
            "inscricao_texto": prazo,
            "publicado": None,
            "nacional": nacional,
            "ufs": ufs,
            "fonte": "pci",
        })
    return concursos


# links de compartilhamento e do próprio PCI não são "links oficiais"
IGNORAR_DOMINIOS = ("pciconcursos.com.br", "pci.app.br", "t.me", "linkedin.com", "facebook.com", "x.com",
                    "twitter.com", "whatsapp.com", "wa.me", "instagram.com", "youtube.com", "google.com")
MAX_LINKS_OFICIAIS = 3


def dominio(url):
    return re.sub(r"^www\.", "", url.split("/")[2].lower()) if url.count("/") >= 2 else ""


def detalhes_noticia(html):
    """Da página da notícia: nomes dos editais (o PDF fica atrás de captcha, então não é baixado)
    e links oficiais citados no texto (site da banca e do órgão)."""
    soup = BeautifulSoup(html, "html.parser")
    editais = [a.get("title") or a.get_text(strip=True) for a in soup.select("#links a.edital-pdf-link")]
    links, vistos = [], set()
    artigo = soup.find("article")
    for a in artigo.find_all("a", href=True) if artigo else []:
        url = a["href"].strip()
        dom = dominio(url)
        if not url.startswith("http") or not dom or dom in vistos:
            continue
        if any(dom == d or dom.endswith("." + d) for d in IGNORAR_DOMINIOS):
            continue
        vistos.add(dom)
        links.append({"texto": a.get_text(strip=True), "url": url, "dominio": dom})
    return {"editais": [e.strip() for e in editais if e.strip()], "links_oficiais": links[:MAX_LINKS_OFICIAIS]}
