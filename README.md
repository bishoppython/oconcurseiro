# 📢 oConcurseiro

Buscador de concursos públicos do Brasil. Um extrator em Python coleta os concursos **com inscrições abertas** (com prazo de inscrição, cargos, escolaridade, vagas e salário) e os **previstos** dos 26 estados, do DF e os nacionais, junta tudo em um único JSON e publica um portal de busca no GitHub Pages.

**Portal:** https://bishoppython.github.io/oconcurseiro/

![Atualizar concursos](https://github.com/bishoppython/oconcurseiro/actions/workflows/atualizar.yml/badge.svg)

## O que o portal faz

- Prazo de inscrição em cada concurso, com contagem de dias (em vermelho quando faltam 7 dias ou menos)
- Busca por órgão, cargo ou cidade, sem diferenciar acentos (os termos encontrados ficam destacados)
- Filtro por estado (os nacionais aparecem em todos), escolaridade e situação (abertos ou previstos)
- Ordenação por inscrições terminando, mais vagas, maior salário ou previstos mais recentes
- Concursos cujo prazo já passou aparecem como "Encerrado", no fim da lista
- Filtros guardados na URL, para compartilhar uma busca: [`?uf=pe&q=prefeitura`](https://bishoppython.github.io/oconcurseiro/?uf=pe&q=prefeitura)
- Tema claro e escuro, funciona no celular

## Como funciona

```
GitHub Actions (6h, 12h e 18h em Recife)
   │
   ├─► extrator/pci.py ─────── ABERTOS: pciconcursos.com.br/concursos/ (1 página, o país inteiro)
   │                           órgão, link, UF, vagas, salário, cargos, escolaridade e
   │                           prazo de inscrição ("17/11/2026", "07/11 a 23/11/2026",
   │                           "Prorrogado até…", "Suspenso")
   │
   └─► extrator/concursos.py ─ PREVISTOS: concursosnobrasil.com/concursos/{uf}/ (28 páginas, 1 s entre elas)
                               só os marcados "previsto"; data tirada do link; repetidos viram um item só
   │
   ▼
docs/data/concursos.json ── commit automático só quando algo mudou
   │
   ▼
docs/ (GitHub Pages) ── portal estático, filtra tudo no navegador
```

**Por que duas fontes:** o PCI traz o prazo de inscrição e os detalhes de cada concurso aberto, mas a página de previstos dele é só uma lista de notícias. O ConcursosNoBrasil marca os previstos na mesma tabela dos abertos. Os abertos do ConcursosNoBrasil são descartados, porque os links diferem dos do PCI e a lista ficaria duplicada.

**Concurso nacional:** no PCI, está na seção "Nacional". Nos previstos, aparece na página "br" ou em 5 estados ou mais (ex.: CGU, IBGE, INSS).

**Proteção contra falhas:** se o PCI falhar ou trouxer menos de 50 concursos (fonte fora do ar ou layout novo), o extrator encerra com erro e o JSON anterior continua publicado. Se o ConcursosNoBrasil falhar, os previstos da coleta anterior são mantidos.

### Formato do JSON

```json
{
  "atualizado": "2026-10-18T05:09:25+00:00",
  "fontes": { "pci": "https://www.pciconcursos.com.br/concursos/", "cnb": "https://concursosnobrasil.com" },
  "ufs": { "br": "Nacional", "pe": "Pernambuco", "...": "..." },
  "falhas": [],
  "concursos": [
    {
      "orgao": "CBM - Corpo de Bombeiros Militar",
      "titulo": "Secretaria de Defesa Social - PE retifica concurso com 570 vagas para Bombeiros",
      "link": "https://www.pciconcursos.com.br/noticias/...",
      "vagas": 570,
      "vagas_texto": "570",
      "salario_max": 12937.33,
      "cargos": "Soldado, 2º Tenente",
      "escolaridade": "Médio / Superior",
      "status": "aberto",
      "inscricao_inicio": null,
      "inscricao_fim": "2026-11-23",
      "inscricao_texto": "Prorrogado até 23/11/2026",
      "publicado": null,
      "nacional": false,
      "ufs": ["pe"],
      "fonte": "pci"
    }
  ]
}
```

- `status`: `aberto`, `suspenso` (PCI) ou `previsto` (ConcursosNoBrasil). O portal mostra como "Encerrado" um aberto cujo `inscricao_fim` já passou.
- `vagas` é `null` quando a fonte diz "Várias" ou "Cadastro reserva" (texto em `vagas_texto`). `salario_max` é `null` quando não há valor.
- `inscricao_*` e `cargos`/`escolaridade` só existem nos abertos (PCI); `publicado` (data da notícia) só nos previstos.

O JSON também serve como API pública: `https://bishoppython.github.io/oconcurseiro/data/concursos.json`.

## Rodar localmente

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q                 # testes do extrator
.venv/bin/python -m extrator.concursos        # gera docs/data/concursos.json
cd docs && python3 -m http.server 8000        # portal em http://localhost:8000
```

## Próximos passos

- Alertas no Telegram e no WhatsApp por estado e palavra-chave
- Resumo por e-mail com os concursos novos da semana
- Página de detalhe com cargos, escolaridade e prazos de inscrição

## Créditos

- Dados: [PCI Concursos](https://www.pciconcursos.com.br/concursos/) e [ConcursosNoBrasil.com](https://concursosnobrasil.com), a quem pertence o conteúdo. Projeto não oficial e educativo: confira sempre o edital.
- O extrator do ConcursosNoBrasil une as abordagens de duas APIs abertas (MIT), e o do PCI segue a mesma lógica:
  - [Vinimartinsc/concursosPublicosAPI](https://github.com/Vinimartinsc/concursosPublicosAPI) (Flask + BeautifulSoup): link, vagas e status "previsto" por categoria
  - [Jeiel0rbit/concursos-api-deno](https://github.com/Jeiel0rbit/concursos-api-deno) (Deno): leitura da tabela por UF, coleta periódica e separação entre abertos e previstos

---

Feito por [Anderson Bispo](https://bishoppython.github.io/obispo/) · oBispo
