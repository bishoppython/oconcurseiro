"""UFs do Brasil e detecção de estados citados em títulos e nomes de órgãos."""

import re

UFS = {
    "br": "Nacional", "ac": "Acre", "al": "Alagoas", "ap": "Amapá", "am": "Amazonas", "ba": "Bahia",
    "ce": "Ceará", "df": "Distrito Federal", "es": "Espírito Santo", "go": "Goiás", "ma": "Maranhão",
    "mt": "Mato Grosso", "ms": "Mato Grosso do Sul", "mg": "Minas Gerais", "pa": "Pará", "pb": "Paraíba",
    "pr": "Paraná", "pe": "Pernambuco", "pi": "Piauí", "rj": "Rio de Janeiro", "rn": "Rio Grande do Norte",
    "rs": "Rio Grande do Sul", "ro": "Rondônia", "rr": "Roraima", "sc": "Santa Catarina", "sp": "São Paulo",
    "se": "Sergipe", "to": "Tocantins",
}

_SIGLA = r"[A-Z]{2}"
_LISTA = rf"{_SIGLA}(?:\s*(?:,|/|\be\b)\s*{_SIGLA})*"
# "Câmara dos Deputados - DF abre", "Marinha - AM e RO abre", "CRBio-01 - SP, MT e MS abre"
RE_APOS_TRACO = re.compile(rf"\s[-–]\s({_LISTA})\b")
# "Processo seletivo MGS (MG) abre", "(RJ/MG)"
RE_PARENTESES = re.compile(rf"\(({_LISTA})\)")
# área de cada Distrito Naval da Marinha, que o título nem sempre cita
DISTRITOS_NAVAIS = {
    "1": ["rj", "es", "mg"], "2": ["ba", "se"], "3": ["ce", "rn", "pb", "pe", "al"],
    "4": ["pa", "ap", "ma", "pi"], "5": ["rs", "sc"], "6": ["ms", "mt"],
    "7": ["df", "go", "to"], "8": ["sp", "pr"], "9": ["am", "rr", "ro", "ac"],
}
RE_DISTRITO_NAVAL = re.compile(r"(\d)º\s+Distrito\s+Naval", re.I)
# nomes mais longos primeiro, para "Mato Grosso do Sul" não virar "Mato Grosso"
_NOMES = sorted(((nome, uf) for uf, nome in UFS.items() if uf != "br"), key=lambda x: -len(x[0]))


def ufs_no_titulo(titulo):
    """Siglas de UF citadas no título, na ordem em que aparecem; [] se nenhuma."""
    for regex in (RE_APOS_TRACO, RE_PARENTESES):
        m = regex.search(titulo or "")
        if m:
            siglas = [s.lower() for s in re.findall(_SIGLA, m.group(1))]
            if siglas and all(s in UFS and s != "br" for s in siglas):
                return list(dict.fromkeys(siglas))
    return []


def ufs_no_nome(orgao):
    """UF cujo nome aparece no nome do órgão ("MGS - Minas Gerais Administração"); [] se nenhuma."""
    texto = orgao or ""
    for nome, uf in _NOMES:
        if re.search(rf"\b{re.escape(nome)}\b", texto):
            return [uf]
    return []


def ufs_do_distrito_naval(texto):
    m = RE_DISTRITO_NAVAL.search(texto or "")
    return list(DISTRITOS_NAVAIS.get(m.group(1), [])) if m else []


def ufs_citadas(titulo, orgao):
    return ufs_no_titulo(titulo) or ufs_no_nome(orgao) or ufs_do_distrito_naval(f"{titulo} {orgao}")
