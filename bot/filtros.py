"""Regras de quem recebe o quê e o texto das mensagens (sem rede, fácil de testar)."""

import unicodedata
from datetime import date
from html import escape
from urllib.parse import urlencode

PORTAL = "https://bishoppython.github.io/oconcurseiro/"
ESCOLARIDADES = {"fundamental": "Fundamental", "medio": "Médio", "tecnico": "Técnico", "superior": "Superior"}
MAX_CARTOES = 5  # acima disso, a pessoa recebe um resumo em vez de uma mensagem por concurso
MAX_RESUMO = 15


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto or "") if not unicodedata.combining(c)).lower()


def combina(concurso, filtros):
    """O concurso interessa a quem tem esses filtros?

    Precisa de pelo menos um estado ou uma palavra-chave (sem isso, ninguém recebe tudo do país).
    Estado: a UF do concurso ou concurso nacional. Palavra: qualquer uma, no órgão, título ou cargos.
    Escolaridade: qualquer uma; concurso sem essa informação (previstos) passa.
    """
    ufs, palavras, escolaridades = filtros["uf"], filtros["palavra"], filtros["escolaridade"]
    if not ufs and not palavras:
        return False
    if ufs and not (concurso.get("nacional") or set(ufs) & set(concurso.get("ufs", []))):
        return False
    if palavras:
        texto = sem_acento(f"{concurso.get('orgao')} {concurso.get('titulo')} {concurso.get('cargos', '')}")
        if not any(sem_acento(p) in texto for p in palavras):
            return False
    esc = sem_acento(concurso.get("escolaridade", ""))
    if escolaridades and esc and not any(e in esc for e in escolaridades):
        return False
    return True


def link_portal(filtros):
    params = {}
    if len(filtros["uf"]) == 1:
        params["uf"] = filtros["uf"][0]
    if len(filtros["palavra"]) == 1:
        params["q"] = filtros["palavra"][0]
    if len(filtros["escolaridade"]) == 1:
        params["escolaridade"] = filtros["escolaridade"][0]
    return PORTAL + ("?" + urlencode(params) if params else "")


def reais(valor):
    if valor >= 1000:
        return f"R$ {valor / 1000:.1f} mil".replace(".", ",").replace(",0 mil", " mil")
    return f"R$ {valor:.2f}".replace(".", ",")


def data_br(iso):
    return "/".join(reversed(iso.split("-"))) if iso else ""


def prazo(concurso, hoje):
    if concurso.get("status") == "previsto":
        return "🔮 Previsto (edital ainda não saiu)"
    if concurso.get("status") == "suspenso":
        return "⏸️ Inscrições suspensas"
    fim = concurso.get("inscricao_fim")
    if not fim:
        return ""
    dias = (date.fromisoformat(fim) - hoje).days
    if dias < 0:
        return f"Inscrições encerradas em {data_br(fim)}"
    falta = "último dia!" if dias == 0 else "falta 1 dia" if dias == 1 else f"faltam {dias} dias"
    return f"📝 Inscrições até {data_br(fim)} ({falta})"


def onde(concurso):
    return "Nacional" if concurso.get("nacional") else ", ".join(u.upper() for u in concurso.get("ufs", []))


def cartao(concurso, hoje=None):
    """Mensagem (HTML do Telegram) de um concurso."""
    hoje = hoje or date.today()
    vagas = f"{concurso['vagas']:,}".replace(",", ".") + " vagas" if concurso.get("vagas") else concurso.get("vagas_texto") or "Várias vagas"
    linha = [onde(concurso), vagas]
    if concurso.get("salario_max"):
        linha.append(f"até {reais(concurso['salario_max'])}")
    partes = [f"🆕 <b>{escape(concurso['orgao'])}</b>", escape(" · ".join(linha))]
    if concurso.get("cargos"):
        cargos = concurso["cargos"] + (f" · {concurso['escolaridade']}" if concurso.get("escolaridade") else "")
        partes.append(escape(cargos))
    if p := prazo(concurso, hoje):
        partes.append(p)
    links = [f'<a href="{escape(concurso["link"])}">📰 Notícia</a>']
    if concurso.get("editais"):
        n = len(concurso["editais"])
        links.append(f'<a href="{escape(concurso["link"])}#links">📄 {"Edital" if n == 1 else f"Editais ({n})"}</a>')
    for l in concurso.get("links_oficiais", [])[:2]:
        links.append(f'<a href="{escape(l["url"])}">🌐 {escape(l["dominio"])}</a>')
    partes.append(" · ".join(links))
    return "\n".join(partes)


def resumo(concursos, filtros, hoje=None):
    """Uma mensagem só quando há muitos concursos novos para a mesma pessoa."""
    hoje = hoje or date.today()
    linhas = [f"🆕 <b>{len(concursos)} concursos novos</b> com os seus filtros:\n"]
    for c in concursos[:MAX_RESUMO]:
        fim = f" · até {data_br(c['inscricao_fim'])}" if c.get("inscricao_fim") else " · previsto" if c.get("status") == "previsto" else ""
        linhas.append(f'• <a href="{escape(c["link"])}">{escape(c["orgao"])}</a> ({escape(onde(c))}){fim}')
    if len(concursos) > MAX_RESUMO:
        linhas.append(f"… e mais {len(concursos) - MAX_RESUMO}.")
    linhas.append(f'\n<a href="{link_portal(filtros)}">Ver todos no portal</a>')
    return "\n".join(linhas)


def mensagens_para(concursos, filtros, hoje=None):
    """As mensagens que uma pessoa recebe para uma leva de concursos novos."""
    escolhidos = [c for c in concursos if combina(c, filtros)]
    if not escolhidos:
        return []
    # os que encerram antes vêm primeiro; previstos no fim
    escolhidos.sort(key=lambda c: (c.get("status") == "previsto", c.get("inscricao_fim") or "9999"))
    if len(escolhidos) <= MAX_CARTOES:
        return [cartao(c, hoje) for c in escolhidos]
    return [resumo(escolhidos, filtros, hoje)]


def buscar(concursos, termo, filtros, limite=5, hoje=None):
    """Abertos que combinam com o termo (e com o estado da pessoa, se houver), por prazo."""
    hoje_iso = (hoje or date.today()).isoformat()
    t = sem_acento(termo)
    achados = [
        c for c in concursos
        if c.get("status") == "aberto" and (c.get("inscricao_fim") or "9999") >= hoje_iso
        and t in sem_acento(f"{c.get('orgao')} {c.get('titulo')} {c.get('cargos', '')}")
        and (not filtros["uf"] or c.get("nacional") or set(filtros["uf"]) & set(c.get("ufs", [])))
    ]
    achados.sort(key=lambda c: c.get("inscricao_fim") or "9999")
    return achados[:limite], len(achados)
