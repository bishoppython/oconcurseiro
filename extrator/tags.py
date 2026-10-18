"""#tags de cada concurso: estado, escolaridade, área e tipo de órgão.

Usadas no portal (clicáveis, entram na busca) e nos posts do canal do Telegram.
"""

import re
import unicodedata

# área -> padrões procurados no órgão, título e cargos (sem acento, minúsculo)
AREAS = {
    "Saude": r"enferm|medic[oa]|saude|farmac|odonto|dentist|fisioterap|nutricion|psicolog|hospital|"
             r"agente comunitario|biomedic|fonoaudiolog|veterinar",
    "Educacao": r"professor|educacao|pedagog|escola|docente|educador|universidade|instituto federal|"
                r"monitor escolar|cuidador",
    "Policial": r"policia|\bpm\b|\bpc\b|\bprf\b|\bpf\b|bombeir|guarda (civil|municipal)|penal|penitenci|"
                r"delegad|investigador|soldado|agente de seguranca|socioeducativ",
    "Militar": r"marinha|exercito|aeronautica|distrito naval|militar|oficia(l|is) temporari",
    "Tribunais": r"tribunal(?! de contas)|\btj[a-z]{0,2}\b|\btrt\b|\btre\b|\btrf\b|\bstj\b|\bstf\b|"
                 r"justica|judiciari",
    "Juridico": r"advogad|procurador|defensor|promotor|\bjuiz|ministerio publico|\bmp[a-z]{0,2}\b|"
                r"oficial de justica|juridic",
    "Fiscal": r"auditor|fiscal|receita|tributar|controladoria|\bcgu\b|tribunal de contas|\btce\b|\btcm\b|"
              r"contador|contabil",
    "Bancario": r"\bbanco|caixa economica|\bbb\b|banestes|banrisul|\bbacen\b|banpara|\bbrb\b|bancari",
    "TI": r"\bti\b|tecnologia da informacao|informatica|\bsistemas\b|desenvolvedor|programador|"
          r"analista de dados|suporte tecnico",
    # "assistente" sozinho pegaria "Assistente Social"; "secretaria" sozinho pegaria "Secretaria de Estado"
    "Administrativo": r"administrativ|assistente (de|em) (escritorio|gestao|administracao)|auxiliar de escritorio|"
                      r"escriturari|recepcionista|\bsecretario\b|secretari[oa] (escolar|executiv)",
    "Social": r"assistente social|assistencia social|\bcras\b|\bcreas\b|educador social|cuidador social",
    "Transito": r"detran|transito|\bder\b|rodoviari",
    "Engenharia": r"engenheir|engenharia|arquitet",
    "Legislativo": r"camara|assembleia legislativa|senado",
    "Prefeitura": r"prefeitura|municipio de",
    "Temporario": r"processo seletivo|seletivo|selecao simplificada|temporari|contratacao",
}
_AREAS = {nome: re.compile(padrao) for nome, padrao in AREAS.items()}
ESCOLARIDADES = (("fundamental", "Fundamental"), ("medio", "Medio"), ("tecnico", "Tecnico"),
                 ("superior", "Superior"))


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto or "") if not unicodedata.combining(c)).lower()


def calcular(concurso):
    """['PE', 'Superior', 'Saude', 'Prefeitura', ...] — sem '#', sem acento, na ordem: onde, nível, área."""
    tags = ["Nacional"] if concurso.get("nacional") else [u.upper() for u in concurso.get("ufs", [])]
    esc = sem_acento(concurso.get("escolaridade"))
    tags += [nome for chave, nome in ESCOLARIDADES if chave in esc]
    texto = sem_acento(f"{concurso.get('orgao')} {concurso.get('titulo')} {concurso.get('cargos', '')}")
    tags += [nome for nome, regex in _AREAS.items() if regex.search(texto)]
    if concurso.get("status") == "previsto":
        tags.append("Previsto")
    return tags
