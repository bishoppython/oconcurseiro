from extrator.tags import calcular


def c(orgao="Prefeitura de X", cargos="", escolaridade="", **extra):
    base = {"orgao": orgao, "titulo": f"{orgao} abre concurso", "cargos": cargos, "escolaridade": escolaridade,
            "ufs": ["pe"], "nacional": False, "status": "aberto"}
    base.update(extra)
    return base


def test_estado_escolaridade_e_area():
    assert calcular(c(cargos="Técnico em Enfermagem, Professor", escolaridade="Médio / Técnico")) == \
        ["PE", "Medio", "Tecnico", "Saude", "Educacao", "Prefeitura"]


def test_nacional_e_previsto():
    assert calcular(c(orgao="INSS", ufs=["br"], nacional=True, status="previsto")) == ["Nacional", "Previsto"]


def test_sem_falsos_positivos_comuns():
    assert "Administrativo" not in calcular(c(cargos="Assistente Social"))
    assert "Social" in calcular(c(cargos="Assistente Social"))
    assert "Administrativo" not in calcular(c(orgao="Secretaria de Estado da Saúde"))
    assert "Tribunais" not in calcular(c(orgao="Tribunal de Contas do Estado"))
    assert "Fiscal" in calcular(c(orgao="Tribunal de Contas do Estado"))


def test_policial_e_transito():
    assert "Policial" in calcular(c(orgao="PM PE", cargos="Soldado"))
    assert "Transito" in calcular(c(orgao="DETRAN - Departamento Estadual de Trânsito", cargos="Agente de Trânsito"))
