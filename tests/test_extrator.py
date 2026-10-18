from extrator.concursos import extrair, mesclar, para_int, salario_max

HTML = """
<table><thead><tr><th>Órgão</th><th>Vagas</th></tr></thead><tbody>
<tr><td><a href="https://concursosnobrasil.com/concursos/pe/2026/10/02/concurso-pc-pe/"
       title="Concurso PC PE edital oferece 1.315 vagas com salários de até R$ 13,5 mil"> PC PE </a></td>
    <td class="center"> 1.315</td></tr>
<tr><td><a href="https://concursosnobrasil.com/concursos/2026/06/24/concurso-cgu/"
       title="Concurso CGU é autorizado com 60 vagas"> CGU </a><div class="label-previsto">previsto</div></td>
    <td class="center"> 60</td></tr>
<tr><td><a href="https://concursosnobrasil.com/concursos/2026/09/29/ibge/" title="IBGE prepara seleção"> IBGE </a></td>
    <td class="center"> Várias</td></tr>
</tbody></table>
"""


def test_extrai_campos():
    pc, cgu, ibge = extrair(HTML, "pe")
    assert pc["orgao"] == "PC PE"
    assert pc["vagas"] == 1315
    assert pc["salario_max"] == 13500
    assert pc["status"] == "aberto"
    assert pc["publicado"] == "2026-10-02"
    assert not pc["nacional"]
    assert cgu["status"] == "previsto"
    assert not cgu["nacional"]  # só a mescla decide o que é nacional
    assert ibge["vagas"] is None and ibge["vagas_texto"] == "Várias"


def test_pagina_sem_tabela():
    assert extrair("<html><body>fora do ar</body></html>", "pe") == []


def test_mescla_sem_duplicar():
    itens = mesclar([extrair(HTML, "pe"), extrair(HTML, "rj")])
    assert len(itens) == 3
    cgu = next(c for c in itens if c["orgao"] == "CGU")
    assert cgu["ufs"] == ["pe", "rj"] and not cgu["nacional"]
    assert itens[0]["publicado"] >= itens[-1]["publicado"]


def test_nacional_pela_pagina_br_ou_por_muitas_ufs():
    em_cinco = mesclar([extrair(HTML, uf) for uf in ("pe", "rj", "sp", "mg", "ba")])
    assert all(c["nacional"] and c["ufs"] == ["br"] for c in em_cinco)
    so_br = mesclar([extrair(HTML, "br"), extrair(HTML, "pe")])
    assert all(c["nacional"] for c in so_br)


def test_conversoes():
    assert para_int("36.946") == 36946
    assert para_int("Várias") is None
    assert salario_max("ganhos de R$ 4.100,00 a R$ 9 mil") == 9000
    assert salario_max("sem salário") is None


def test_detalhar_usa_cache_e_le_so_o_vencido(monkeypatch):
    from datetime import date, timedelta

    from extrator import concursos

    monkeypatch.setattr(concursos.time, "sleep", lambda s: None)
    hoje = date.today().isoformat()
    velho = (date.today() - timedelta(days=10)).isoformat()
    anteriores = [
        {"link": "a", "detalhado_em": hoje, "editais": ["E1"], "links_oficiais": []},
        {"link": "b", "detalhado_em": velho, "editais": ["antigo"], "links_oficiais": []},
    ]
    abertos = [{"link": "a"}, {"link": "b"}, {"link": "c"}]
    lidos = []

    class Resp:
        text = '<aside id="links"><a class="edital-pdf-link" title="NOVO"></a></aside>'
        def raise_for_status(self): pass

    class Sessao:
        def get(self, url, timeout):
            lidos.append(url)
            return Resp()

    concursos.detalhar(abertos, anteriores, Sessao())
    assert lidos == ["b", "c"]  # "a" está no cache e ainda vale
    assert abertos[0]["editais"] == ["E1"]
    assert abertos[1]["editais"] == ["NOVO"] and abertos[1]["detalhado_em"] == hoje
