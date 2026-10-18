"""Extrator de concursos públicos do oConcurseiro.

Junta duas fontes em um único JSON para o portal em docs/:
- abertos: PCI Concursos (extrator/pci.py), que traz o prazo de inscrição, cargos e escolaridade;
- previstos: páginas por UF do ConcursosNoBrasil.com (mesma fonte e mesma ideia das APIs
  Vinimartinsc/concursosPublicosAPI e Jeiel0rbit/concursos-api-deno).
Os abertos do ConcursosNoBrasil são descartados: os links diferem do PCI e duplicariam a lista.

Uso: python -m extrator.concursos [saida.json]
"""

import json
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from extrator import pci, tags
from extrator.ufs import UFS, ufs_citadas

BASE_URL = "https://concursosnobrasil.com/concursos/{uf}/"
USER_AGENT = "Mozilla/5.0 (compatible; oConcurseiro/1.0; +https://github.com/bishoppython/oconcurseiro)"
PAUSA_S = 1.0  # entre uma página e outra, para não sobrecarregar a fonte
MIN_UFS_NACIONAL = 5  # listado em tantas UFs = nacional
MIN_PCI = 50  # menos que isso = página do PCI fora do ar ou com layout novo
DETALHES_VALIDADE_DIAS = 3  # notícia relida depois disso, para pegar retificações do edital
MAX_DETALHES_POR_EXECUCAO = 600  # teto de notícias lidas por execução (a 1 s cada)


RE_DATA = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")
# "R$ 13,5 mil", "R$ 4.100,00", "R$ 9 mil" — pega o maior valor citado no título
RE_SALARIO = re.compile(r"R\$\s*([\d.]+(?:,\d+)?)\s*(mil)?", re.I)


def para_int(texto):
    """'1.315' -> 1315; 'Várias' -> None."""
    digitos = re.sub(r"\D", "", texto or "")
    return int(digitos) if digitos else None


def salario_max(titulo):
    valores = []
    for numero, mil in RE_SALARIO.findall(titulo or ""):
        valor = float(numero.replace(".", "").replace(",", "."))
        valores.append(valor * 1000 if mil else valor)
    return max(valores) if valores else None


def extrair(html, uf):
    """Converte a tabela de uma página de UF em uma lista de concursos."""
    soup = BeautifulSoup(html, "html.parser")
    tabela = soup.find("table")
    if not tabela:
        return []
    concursos = []
    for linha in tabela.select("tbody tr"):
        celulas = linha.find_all("td")
        link = linha.find("a")
        if len(celulas) < 2 or not link or not link.get("href"):
            continue
        url = link["href"].strip()
        data = RE_DATA.search(url)
        titulo = (link.get("title") or link.get_text()).strip()
        vagas_texto = celulas[1].get_text(strip=True)
        concursos.append({
            "orgao": link.get_text(strip=True),
            "titulo": titulo,
            "link": url,
            "vagas": para_int(vagas_texto),
            "vagas_texto": vagas_texto,
            "salario_max": salario_max(titulo),
            "status": "previsto" if linha.select_one(".label-previsto") else "aberto",
            "inscricao_inicio": None,
            "inscricao_fim": None,
            "inscricao_texto": "",
            "cargos": "",
            "escolaridade": "",
            "publicado": "-".join(data.groups()) if data else None,
            "nacional": uf == "br",
            "ufs": [uf],
            "fonte": "cnb",
        })
    return concursos


def mesclar(listas):
    """Junta as listas de todas as UFs; o mesmo link vira um item só, com todas as UFs.

    Nacional = está na página "br" ou aparece em MIN_UFS_NACIONAL páginas ou mais (ex.: CGU),
    desde que o título ou o nome do órgão não cite um estado.
    """
    por_link = {}
    for lista in listas:
        for c in lista:
            atual = por_link.get(c["link"])
            if atual:
                atual["ufs"] = sorted(set(atual["ufs"]) | set(c["ufs"]))
                atual["nacional"] = atual["nacional"] or c["nacional"]
            else:
                por_link[c["link"]] = dict(c)
    for c in por_link.values():
        if c["nacional"] or len(c["ufs"]) >= MIN_UFS_NACIONAL:
            # estado citado ("MGS (MG)") vence a regra: o concurso é daquele estado, não nacional
            citadas = ufs_citadas(c["titulo"], c["orgao"])
            c["nacional"] = not citadas
            c["ufs"] = citadas or ["br"]
    return sorted(por_link.values(), key=lambda c: c["publicado"] or "", reverse=True)


def baixar(uf, sessao):
    r = sessao.get(BASE_URL.format(uf=uf), timeout=30)
    r.raise_for_status()
    return r.text


def coletar_cnb(sessao):
    listas, falhas = [], []
    for uf in UFS:
        try:
            itens = extrair(baixar(uf, sessao), uf)
            print(f"{uf.upper()}: {len(itens)} concursos")
            listas.append(itens)
        except requests.RequestException as e:
            print(f"{uf.upper()}: falhou ({e})", file=sys.stderr)
            falhas.append(uf)
        time.sleep(PAUSA_S)
    return mesclar(listas), falhas


def coletar_pci(sessao):
    r = sessao.get(pci.URL, timeout=60)
    r.raise_for_status()
    return pci.extrair(r.text)


def carregar_anteriores(saida):
    try:
        return json.loads(saida.read_text(encoding="utf-8")).get("concursos", [])
    except (OSError, ValueError):
        return []


def detalhar(abertos, anteriores, sessao):
    """Põe editais e links oficiais em cada aberto, lendo só as notícias novas ou vencidas."""
    cache = {c["link"]: c for c in anteriores if c.get("detalhado_em")}
    hoje = date.today().isoformat()
    vencimento = (date.today() - timedelta(days=DETALHES_VALIDADE_DIAS)).isoformat()
    lidas = falhas = 0
    for c in abertos:
        antigo = cache.get(c["link"])
        if antigo:
            c.update(editais=antigo.get("editais", []), links_oficiais=antigo.get("links_oficiais", []),
                     detalhado_em=antigo["detalhado_em"])
        else:
            c.update(editais=[], links_oficiais=[])
        if (antigo and antigo["detalhado_em"] >= vencimento) or lidas >= MAX_DETALHES_POR_EXECUCAO:
            continue
        lidas += 1
        try:
            r = sessao.get(c["link"], timeout=30)
            r.raise_for_status()
            c.update(pci.detalhes_noticia(r.text), detalhado_em=hoje)
        except requests.RequestException as e:
            falhas += 1  # fica com o que já havia; tenta de novo na próxima execução
            print(f"notícia falhou: {c['link']} ({e})", file=sys.stderr)
        time.sleep(PAUSA_S)
    print(f"notícias lidas: {lidas} ({falhas} falharam); {len(abertos) - lidas} vieram do cache")


def main():
    saida = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/data/concursos.json")
    sessao = requests.Session()
    sessao.headers["User-Agent"] = USER_AGENT
    try:
        abertos = coletar_pci(sessao)
    except requests.RequestException as e:
        sys.exit(f"PCI falhou ({e}); JSON anterior mantido")
    print(f"PCI: {len(abertos)} concursos com inscrições abertas")
    if len(abertos) < MIN_PCI:
        # fonte fora do ar ou mudou o layout: mantém o JSON anterior em vez de publicar quase vazio
        sys.exit(f"PCI trouxe só {len(abertos)} concursos; JSON anterior mantido")

    anteriores = carregar_anteriores(saida)
    detalhar(abertos, anteriores, sessao)

    cnb, falhas = coletar_cnb(sessao)
    previstos = [c for c in cnb if c["status"] == "previsto"]
    if len(falhas) > len(UFS) // 2 or not previstos:
        previstos = [c for c in anteriores if c.get("status") == "previsto"]
        print(f"ConcursosNoBrasil incompleto; mantidos {len(previstos)} previstos da coleta anterior")

    for c in abertos + previstos:
        c["tags"] = tags.calcular(c)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps({
        "atualizado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fontes": {"pci": "https://www.pciconcursos.com.br/concursos/", "cnb": "https://concursosnobrasil.com"},
        "ufs": UFS,
        "falhas": falhas,
        "concursos": abertos + previstos,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(abertos)} abertos e {len(previstos)} previstos salvos em {saida}")


if __name__ == "__main__":
    main()
