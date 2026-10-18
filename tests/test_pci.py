from extrator.pci import detalhes_noticia, extrair, inscricao

HTML = """
<h2>NACIONAL</h2>
<div id="NACIONAL" class="ua"><div class="uf">NACIONAL</div><div class="uc">Inscrição até:</div></div>
<div class="na" data-url="x">
  <div class="ca"><a href="https://www.pciconcursos.com.br/noticias/camara-dos-deputados"
     title="Câmara dos Deputados - DF abre concurso público para analistas legislativos">Câmara dos Deputados</a>
  <div class="cb"><img src=""></div>
  <div class="cc">&nbsp;</div>
  <div class="cd">184 vagas até R$ 32.070,88<br><span>Analista Legislativo, Engenheiro<br><span>Superior</span></span>
  </div><div class="ce"><span>17/11/2026</span></div>
  <div class="clear"></div>
</div></div>
<div class="da" data-url="w">
  <div class="ca"><a href="https://www.pciconcursos.com.br/noticias/cgu" title="CGU abre concurso público com vagas para auditores">CGU - Controladoria-Geral da União</a>
  <div class="cc">&nbsp;</div>
  <div class="cd">60 vagas até R$ 23.000,00<br><span>Auditor<br><span>Superior</span></span>
  </div><div class="ce"><span>20/11/2026</span></div>
</div></div>
<div id="PE" class="ua"><div class="uf">PERNAMBUCO</div></div>
<div class="da" data-url="y">
  <div class="ca"><a href="https://www.pciconcursos.com.br/noticias/bombeiros-pe" title="Bombeiros PE">CBM - Corpo de Bombeiros Militar</a>
  <div class="cc">PE</div>
  <div class="cd">570 vagas até R$ 12.937,33<br><span>Soldado, 2º Tenente<br><span>Médio / Superior</span></span>
  </div><div class="ce"><span>Prorrogado até<br>23/11/2026</span></div>
</div></div>
<div class="na" data-url="z">
  <div class="ca"><a href="https://www.pciconcursos.com.br/noticias/prefeitura-x" title="Prefeitura X">Prefeitura X</a>
  <div class="cc">PE</div>
  <div class="cd">Cadastro reserva<br><span>Vários Cargos<br><span>Fundamental</span></span>
  </div><div class="ce"><span>Suspenso</span></div>
</div></div>
"""


def test_extrai_nacional_e_estadual():
    camara, cgu, bombeiros, prefeitura = extrair(HTML)
    # estava na seção "Nacional" do PCI, mas o título diz "- DF"
    assert not camara["nacional"] and camara["ufs"] == ["df"]
    assert cgu["nacional"] and cgu["ufs"] == ["br"]
    assert camara["vagas"] == 184
    assert camara["salario_max"] == 32070.88
    assert camara["cargos"] == "Analista Legislativo, Engenheiro"
    assert camara["escolaridade"] == "Superior"
    assert camara["inscricao_fim"] == "2026-11-17"
    assert camara["status"] == "aberto" and camara["fonte"] == "pci"

    assert not bombeiros["nacional"] and bombeiros["ufs"] == ["pe"]
    assert bombeiros["escolaridade"] == "Médio / Superior"
    assert bombeiros["inscricao_texto"] == "Prorrogado até 23/11/2026"

    assert prefeitura["status"] == "suspenso"
    assert prefeitura["vagas"] is None and prefeitura["salario_max"] is None
    assert prefeitura["vagas_texto"] == "Cadastro reserva"
    assert prefeitura["inscricao_fim"] is None


def test_formatos_de_prazo():
    assert inscricao("17/11/2026") == (None, "2026-11-17")
    assert inscricao("07/11 a 23/11/2026") == ("2026-11-07", "2026-11-23")
    assert inscricao("10 a 20/11/2026") == ("2026-11-10", "2026-11-20")
    assert inscricao("05/10/2026 a 03/11/2026") == ("2026-10-05", "2026-11-03")
    assert inscricao("Reabertura de 05/11 a 20/11/2026") == ("2026-11-05", "2026-11-20")
    assert inscricao("Reaberto até 30/10/2026") == (None, "2026-10-30")
    assert inscricao("Suspenso") == (None, None)


def test_pagina_sem_concursos():
    assert extrair("<html><body>manutenção</body></html>") == []


NOTICIA = """
<article>
  <p>Inscrições no site <a href="https://www.cebraspe.org.br/concursos/cd_26_analista">www.cebraspe.org.br/concursos/cd_26_analista</a>.</p>
  <p>Mais em <a href="https://www.camara.leg.br/">Câmara dos Deputados</a> e
     <a href="https://www.cebraspe.org.br/">Cebraspe</a> (mesmo domínio, ignorado).</p>
  <a href="https://www.pciconcursos.com.br/noticias/outra">outra notícia</a>
  <a href="https://t.me/share/url?url=x">Telegram</a>
</article>
<aside id="links"><ul>
  <li class="pdf"><a href="javascript:void(0);" class="edital-pdf-link" data-link="1" title="EDITAL Nº 1">EDITAL Nº 1</a></li>
  <li class="pdf"><a href="javascript:void(0);" class="edital-pdf-link" data-link="2" title="RETIFICAÇÃO Nº 1">RETIFICAÇÃO Nº 1</a></li>
</ul></aside>
"""


def test_detalhes_da_noticia():
    d = detalhes_noticia(NOTICIA)
    assert d["editais"] == ["EDITAL Nº 1", "RETIFICAÇÃO Nº 1"]
    assert [l["dominio"] for l in d["links_oficiais"]] == ["cebraspe.org.br", "camara.leg.br"]
    assert d["links_oficiais"][0]["url"] == "https://www.cebraspe.org.br/concursos/cd_26_analista"


def test_noticia_sem_editais():
    assert detalhes_noticia("<article><p>texto</p></article>") == {"editais": [], "links_oficiais": []}
