from extrator.concursos import extrair, mesclar
from extrator.ufs import ufs_citadas, ufs_do_distrito_naval, ufs_no_nome, ufs_no_titulo


def test_siglas_no_titulo():
    assert ufs_no_titulo("Câmara dos Deputados - DF abre concurso público") == ["df"]
    assert ufs_no_titulo("Comando do 1º Distrito Naval - RJ/MG abre vagas") == ["rj", "mg"]
    assert ufs_no_titulo("Marinha do Brasil - AM e RO abre processo seletivo") == ["am", "ro"]
    assert ufs_no_titulo("CRBio-01 - SP, MT e MS abre concurso público") == ["sp", "mt", "ms"]
    assert ufs_no_titulo("Processo seletivo MGS (MG) abre 643 vagas") == ["mg"]


def test_titulo_sem_estado():
    assert ufs_no_titulo("CGU abre concurso público com vagas para auditores") == []
    assert ufs_no_titulo("Marinha do Brasil - 3º Distrito Naval abre vagas") == []
    assert ufs_no_titulo("INB - Indústrias Nucleares do Brasil abre concurso") == []
    assert ufs_no_titulo("Concurso X - TI abre vagas") == []  # TI não é UF


def test_estado_no_nome_do_orgao():
    assert ufs_no_nome("MGS - Minas Gerais Administração e Serviços") == ["mg"]
    assert ufs_no_nome("Fundação de Saúde do Mato Grosso do Sul") == ["ms"]
    assert ufs_no_nome("Banco do Brasil") == []
    assert ufs_citadas("MGS abre processo seletivo", "MGS - Minas Gerais Administração") == ["mg"]


def test_previsto_nacional_com_estado_no_titulo_vira_estadual():
    html = """<table><tbody><tr><td><a href="https://concursosnobrasil.com/concursos/2026/10/16/mgs/"
      title="Processo seletivo MGS (MG) abre 643 vagas">MGS</a></td><td>643</td></tr></tbody></table>"""
    [mgs] = mesclar([extrair(html, uf) for uf in ("br", "mg")])
    assert not mgs["nacional"] and mgs["ufs"] == ["mg"]


def test_distrito_naval():
    assert ufs_do_distrito_naval("Marinha do Brasil - 3º Distrito Naval abre vagas") == ["ce", "rn", "pb", "pe", "al"]
    assert ufs_citadas("Marinha do Brasil - 7º Distrito Naval: edital", "Comando do 7º Distrito Naval") == ["df", "go", "to"]
    # sigla no título tem prioridade sobre o mapa
    assert ufs_citadas("Comando do 1º Distrito Naval - RJ/MG abre vagas", "Com1ºDN") == ["rj", "mg"]
