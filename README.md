# 📢 oConcurseiro

Buscador de concursos públicos do Brasil. Um extrator em Python coleta os concursos **abertos e previstos** dos 26 estados, do DF e os nacionais, junta tudo em um único JSON e publica um portal de busca no GitHub Pages.

**Portal:** https://bishoppython.github.io/oconcurseiro/

![Atualizar concursos](https://github.com/bishoppython/oconcurseiro/actions/workflows/atualizar.yml/badge.svg)

## O que o portal faz

- Busca por órgão, cargo ou cidade, sem diferenciar acentos (os termos encontrados ficam destacados)
- Filtro por estado (os nacionais aparecem em todos) e por situação (abertos ou previstos)
- Ordenação por mais recentes, mais vagas ou maior salário
- Filtros guardados na URL, para compartilhar uma busca: [`?uf=pe&q=prefeitura`](https://bishoppython.github.io/oconcurseiro/?uf=pe&q=prefeitura)
- Tema claro e escuro, funciona no celular

## Como funciona

```
GitHub Actions (6h, 12h e 18h em Recife)
   │
   ▼
extrator/concursos.py ── baixa /concursos/{uf}/ das 28 páginas (1 s entre elas)
   │                     lê a tabela: órgão, título, link, vagas, "previsto"
   │                     deduz data (do link) e salário máximo (do título)
   │                     junta repetidos: o mesmo link vira um item só
   ▼
docs/data/concursos.json ── commit automático só quando algo mudou
   │
   ▼
docs/ (GitHub Pages) ── portal estático, filtra tudo no navegador
```

**Concurso nacional:** aparece na página "br" ou em 5 estados ou mais (ex.: CGU, IBGE, INSS).

**Proteção contra falhas:** se mais da metade das páginas falhar ou nada for extraído (fonte fora do ar ou layout novo), o extrator encerra com erro e o JSON anterior continua publicado.

### Formato do JSON

```json
{
  "atualizado": "2026-10-18T05:09:25+00:00",
  "fonte": "https://concursosnobrasil.com",
  "ufs": { "br": "Nacional", "pe": "Pernambuco", "...": "..." },
  "falhas": [],
  "concursos": [
    {
      "orgao": "PC PE",
      "titulo": "Concurso PC PE edital oferece 1.315 vagas com salários de até R$ 13,5 mil",
      "link": "https://concursosnobrasil.com/concursos/pe/2026/10/02/...",
      "vagas": 1315,
      "vagas_texto": "1.315",
      "salario_max": 13500.0,
      "status": "aberto",
      "publicado": "2026-10-02",
      "nacional": false,
      "ufs": ["pe"]
    }
  ]
}
```

`vagas` é `null` quando a fonte diz "Várias". `salario_max` é `null` quando o título não cita valor.

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

- Dados: [ConcursosNoBrasil.com](https://concursosnobrasil.com), a quem pertence o conteúdo. Projeto não oficial e educativo: confira sempre o edital.
- O extrator une as abordagens de duas APIs abertas (MIT):
  - [Vinimartinsc/concursosPublicosAPI](https://github.com/Vinimartinsc/concursosPublicosAPI) (Flask + BeautifulSoup): link, vagas e status "previsto" por categoria
  - [Jeiel0rbit/concursos-api-deno](https://github.com/Jeiel0rbit/concursos-api-deno) (Deno): leitura da tabela por UF, coleta periódica e separação entre abertos e previstos

---

Feito por [Anderson Bispo](https://bishoppython.github.io/obispo/) · oBispo
