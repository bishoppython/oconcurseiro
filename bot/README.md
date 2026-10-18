# 🤖 Bot de alertas do oConcurseiro (Telegram)

Cada pessoa escolhe estados, palavras-chave e escolaridade, e o bot avisa no privado quando sai concurso **novo** que combina. Os dados vêm do JSON público do portal, que o GitHub Actions atualiza 3 vezes ao dia.

## Comandos

| Comando | O que faz |
|---|---|
| `/start` | boas-vindas e instruções |
| `/estado PE` | recebe concursos do estado (aceita vários e nomes: `/estado PE PB`, `/estado Pernambuco`) |
| `/palavra professor` | recebe por palavra-chave, sem diferenciar acento (várias separadas por vírgula) |
| `/escolaridade superior` | só concursos com essa escolaridade (`fundamental`, `medio`, `tecnico`, `superior`) |
| `/minhas` | mostra os filtros e um link para o portal já filtrado |
| `/remover PE` | remove um filtro (`/remover tudo` limpa todos) |
| `/buscar enfermeiro` | busca agora entre os abertos, pelos que encerram antes |
| `/parar` | para os alertas e **apaga os dados** da pessoa |

## Regras

- Precisa de pelo menos um estado **ou** uma palavra-chave para receber alertas (ninguém recebe o país inteiro).
- Concursos nacionais chegam para quem escolheu qualquer estado.
- Escolaridade filtra só concursos que têm essa informação; previstos (sem edital) passam.
- Até 5 concursos novos de uma vez chegam um por mensagem; acima disso, chega um resumo com link para o portal.
- Na primeira execução, tudo o que já existe é marcado como visto: ninguém recebe centenas de mensagens.

## Privacidade (LGPD)

O banco SQLite (`data/oconcurseiro.db`) fica **só no servidor** e guarda apenas o número do chat, os filtros e os links já vistos. Nada disso vai para o repositório. `/parar` apaga tudo da pessoa, e quem bloqueia o bot tem os dados apagados automaticamente.

## Como funciona

```
laço único (bot/main.py)
 ├── getUpdates (long polling, 25 s) ──► responde comandos   ← não precisa abrir porta
 └── a cada 30 min: baixa data/concursos.json do portal
        └── links que ainda não estão em "vistos" = concursos novos
              └── para cada inscrito: filtros.combina() ──► sendMessage
```

## Rodar no servidor

```bash
git clone https://github.com/bishoppython/oconcurseiro.git && cd oconcurseiro/bot
cp .env.example .env            # e cole o token do @BotFather
docker compose up -d --build
docker compose logs -f          # deve aparecer "no ar" e "primeira carga"
```

Atualizar: `git pull && docker compose up -d --build`.

| Variável | Padrão | |
|---|---|---|
| `TELEGRAM_TOKEN` | — | token do bot (obrigatório, só no `.env`) |
| `DADOS_URL` | JSON do portal | de onde vêm os concursos |
| `INTERVALO_MIN` | 30 | intervalo entre checagens |
| `BANCO` | `data/oconcurseiro.db` | caminho do SQLite |
