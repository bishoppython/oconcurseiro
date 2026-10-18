from datetime import date

import pytest

from bot.banco import Banco
from bot.filtros import cartao, combina, mensagens_para
from bot.main import Bot
from bot.telegram import Bloqueado

HOJE = date(2026, 10, 18)


def concurso(link, orgao="Prefeitura X", ufs=("pe",), nacional=False, **extra):
    base = {"link": link, "orgao": orgao, "titulo": f"{orgao} abre concurso", "ufs": list(ufs),
            "nacional": nacional, "status": "aberto", "cargos": "", "escolaridade": "",
            "inscricao_fim": "2026-11-01", "vagas": 10, "salario_max": 5000.0}
    base.update(extra)
    return base


def filtros(uf=(), palavra=(), escolaridade=()):
    return {"uf": list(uf), "palavra": list(palavra), "escolaridade": list(escolaridade)}


def test_combina_estado_e_nacional():
    assert combina(concurso("a", ufs=["pe"]), filtros(uf=["pe"]))
    assert not combina(concurso("a", ufs=["df"]), filtros(uf=["pe"]))
    assert combina(concurso("a", ufs=["br"], nacional=True), filtros(uf=["pe"]))


def test_combina_palavra_sem_acento_e_escolaridade():
    c = concurso("a", cargos="Técnico em Enfermagem", escolaridade="Médio / Técnico")
    assert combina(c, filtros(palavra=["tecnico em enfermagem"]))
    assert combina(c, filtros(uf=["pe"], escolaridade=["medio"]))
    assert not combina(c, filtros(uf=["pe"], escolaridade=["superior"]))
    assert combina(concurso("b", status="previsto"), filtros(uf=["pe"], escolaridade=["superior"]))


def test_sem_estado_nem_palavra_nao_recebe_nada():
    assert not combina(concurso("a"), filtros())
    assert not combina(concurso("a"), filtros(escolaridade=["superior"]))


def test_muitos_concursos_viram_resumo():
    lote = [concurso(str(i)) for i in range(8)]
    [msg] = mensagens_para(lote, filtros(uf=["pe"]), HOJE)
    assert "8 concursos novos" in msg and "Ver todos no portal" in msg


def test_cartao_escapa_html_e_mostra_prazo():
    c = concurso("https://x/1", orgao="Câmara <A&B>", inscricao_fim="2026-10-18",
                 editais=["E1", "E2"], links_oficiais=[{"url": "https://banca.org", "dominio": "banca.org"}])
    texto = cartao(c, HOJE)
    assert "Câmara &lt;A&amp;B&gt;" in texto
    assert "último dia!" in texto
    assert "Editais (2)" in texto and "banca.org" in texto


class TgFalso:
    def __init__(self, bloqueados=()):
        self.enviadas, self.bloqueados = [], set(bloqueados)

    def enviar(self, chat_id, texto):
        if chat_id in self.bloqueados:
            raise Bloqueado("blocked")
        self.enviadas.append((chat_id, texto))


@pytest.fixture
def bot(tmp_path, monkeypatch):
    monkeypatch.setattr("bot.main.time.sleep", lambda s: None)
    lote = {"dados": [concurso("velho")]}
    b = Bot(TgFalso(), Banco(str(tmp_path / "t.db")), baixar=lambda: lote["dados"])
    b.lote = lote
    return b


def test_comandos(bot):
    assert "oConcurseiro" in bot.responder(1, "/start")
    assert "PE, PB" in bot.responder(1, "/estado pe PB")
    assert "não reconheci: XX" in bot.responder(1, "/estado XX")
    assert "professor" in bot.responder(1, "/palavra Professor")
    assert "Superior" in bot.responder(1, "/escolaridade Superior")
    assert bot.banco.filtros(1) == {"uf": ["pb", "pe"], "palavra": ["professor"], "escolaridade": ["superior"]}
    assert "Removido" in bot.responder(1, "/remover pb")
    assert "Não achei" in bot.responder(1, "/remover xyz")
    assert "apaguei seus dados" in bot.responder(1, "/parar")
    assert bot.banco.total_inscritos() == 0


def test_primeira_carga_nao_dispara_e_depois_so_avisa_novos(bot):
    bot.responder(1, "/estado PE")
    bot.responder(2, "/estado SP")
    assert bot.notificar() == 0  # primeira carga só marca como visto
    bot.lote["dados"] = [concurso("velho"), concurso("novo-pe"), concurso("novo-sp", ufs=["sp"])]
    assert bot.notificar() == 2
    assert [chat for chat, _ in bot.tg.enviadas] == [1, 2]
    assert bot.notificar() == 0  # nada novo


def test_quem_bloqueou_o_bot_tem_os_dados_apagados(bot):
    bot.responder(7, "/estado PE")
    bot.notificar()
    bot.tg.bloqueados.add(7)
    bot.lote["dados"].append(concurso("novo"))
    bot.notificar()
    assert bot.banco.total_inscritos() == 0


def test_buscar(bot):
    bot.lote["dados"] = [concurso("a", cargos="Enfermeiro"), concurso("b", cargos="Motorista")]
    resposta = bot.responder(1, "/buscar enfermeiro")
    assert "<b>1</b> concurso" in resposta and "Enfermeiro" in resposta
    assert "Nenhum concurso" in bot.responder(1, "/buscar astronauta")


def test_estados_por_sigla_ou_nome():
    from bot.main import ler_estados
    assert ler_estados("PE PB") == (["pe", "pb"], [])
    assert ler_estados("Pernambuco, Paraíba") == (["pe", "pb"], [])
    assert ler_estados("mato grosso do sul e Rio de Janeiro") == (["ms", "rj"], [])
    assert ler_estados("Pernambuc") == ([], ["Pernambuc"])


def test_hashtags_e_post_do_canal():
    from bot.filtros import hashtags, post_canal
    c = concurso("a", ufs=["pe"], escolaridade="Médio / Técnico / Superior")
    assert hashtags(c) == "#PE #Medio #Tecnico #Superior"
    assert hashtags(concurso("b", ufs=["br"], nacional=True, status="previsto")) == "#Nacional #Previsto"
    post = post_canal(c, HOJE)
    assert post.startswith("🆕 <b>Prefeitura X</b>") and "#PE" in post and "@oConcurseiroBR_bot" in post


def test_canal_recebe_novos_em_fila_com_pausa(bot, monkeypatch):
    relogio = {"t": 1000.0}
    monkeypatch.setattr("bot.main.time.time", lambda: relogio["t"])
    bot.canal = "@canal"
    bot.notificar()  # primeira carga: nada vai para o canal
    assert bot.banco.tamanho_fila() == 0
    bot.lote["dados"] += [concurso("n1", inscricao_fim="2026-11-30"), concurso("n2", inscricao_fim="2026-10-20")]
    bot.notificar()
    assert bot.banco.tamanho_fila() == 2
    assert bot.publicar_no_canal() is True        # publica o primeiro (n2, que encerra antes)
    assert bot.publicar_no_canal() is True        # ainda dentro da pausa: não publica
    relogio["t"] += 4
    assert bot.publicar_no_canal() is False       # publica o segundo; fila vazia
    canal = [t for chat, t in bot.tg.enviadas if chat == "@canal"]
    assert len(canal) == 2 and "20/10/2026" in canal[0]


def test_falha_no_canal_nao_trava_a_fila(bot):
    bot.canal = "@canal"
    bot.tg.bloqueados.add("@canal")
    bot.banco.enfileirar(["post"])
    assert bot.publicar_no_canal() is False and bot.banco.tamanho_fila() == 0
