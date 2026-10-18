"""Bot de alertas do oConcurseiro no Telegram.

Laço único: espera mensagens (long polling) e, a cada INTERVALO_MIN, baixa o JSON do portal
e avisa cada inscrito dos concursos novos que combinam com os filtros dele.

Concursos novos também vão para o canal público (TELEGRAM_CANAL), um a cada PAUSA_CANAL_S.

Variáveis: TELEGRAM_TOKEN (obrigatória), TELEGRAM_CANAL, DADOS_URL, BANCO, INTERVALO_MIN.
"""

import logging
import os
import re
import time

import requests

from bot.banco import Banco
from bot.filtros import (ESCOLARIDADES, PORTAL, buscar, cartao, link_portal, mensagens_para, post_canal,
                         sem_acento)
from bot.telegram import Bloqueado, Telegram
from extrator.ufs import UFS as NOMES_UF

DADOS_URL = os.environ.get("DADOS_URL", PORTAL + "data/concursos.json")
BANCO = os.environ.get("BANCO", "data/oconcurseiro.db")
INTERVALO_MIN = int(os.environ.get("INTERVALO_MIN", "30"))
CANAL = os.environ.get("TELEGRAM_CANAL", "").strip()  # "@oConcurseiroBR"; vazio = sem canal
PAUSA_ENVIO_S = 0.05  # bem abaixo do limite de ~30 mensagens/s do Telegram
PAUSA_CANAL_S = 3.5   # num mesmo canal o limite é ~20 mensagens por minuto

UFS = {uf for uf in NOMES_UF if uf != "br"}
UF_POR_NOME = {sem_acento(nome): uf for uf, nome in NOMES_UF.items() if uf != "br"}
NOMES_TIPO = {"uf": "Estados", "palavra": "Palavras-chave", "escolaridade": "Escolaridade"}

COMANDOS = [
    ("estado", "Receber concursos de um estado: /estado PE"),
    ("palavra", "Receber por palavra-chave: /palavra professor"),
    ("escolaridade", "Filtrar por escolaridade: /escolaridade superior"),
    ("minhas", "Ver meus filtros"),
    ("remover", "Remover um filtro: /remover PE"),
    ("buscar", "Buscar agora: /buscar enfermeiro"),
    ("parar", "Parar os alertas e apagar meus dados"),
    ("ajuda", "Como usar"),
]

BOAS_VINDAS = """👋 Olá! Eu sou o <b>oConcurseiro</b>.

Aviso quando sair concurso novo que combine com o que você procura, várias vezes ao dia.

<b>Comece escolhendo um estado ou uma palavra-chave:</b>
/estado PE (pode pôr mais de um: /estado PE PB)
/palavra professor (ou várias: /palavra enfermeiro, técnico em enfermagem)

<b>Opcional:</b> /escolaridade superior (fundamental, medio, tecnico, superior)

Concursos nacionais chegam para todos os estados. /minhas mostra seus filtros e /buscar procura agora.

🔒 Eu guardo só o número deste chat e os seus filtros. /parar apaga tudo."""

log = logging.getLogger("oconcurseiro")


def ler_estados(arg):
    """'PE PB', 'pe, pb' ou 'Pernambuco, Paraíba' -> (['pe', 'pb'], [inválidos])."""
    siglas, invalidos = [], []
    for parte in re.split(r"[,;/]+|\s+e\s+", arg):
        parte = parte.strip()
        if not parte:
            continue
        uf = UF_POR_NOME.get(sem_acento(parte))
        if uf:
            siglas.append(uf)
            continue
        for token in parte.split():  # "PE PB"
            t = token.lower()
            (siglas if t in UFS else invalidos).append(t if t in UFS else token)
    return list(dict.fromkeys(siglas)), invalidos


def normalizar_escolaridade(texto):
    t = sem_acento(texto).strip()
    return t if t in ESCOLARIDADES else None


def descrever(filtros):
    linhas = []
    for tipo, nome in NOMES_TIPO.items():
        if filtros[tipo]:
            valores = [v.upper() if tipo == "uf" else ESCOLARIDADES.get(v, v) for v in filtros[tipo]]
            linhas.append(f"<b>{nome}:</b> {', '.join(valores)}")
    return "\n".join(linhas)


class Bot:
    def __init__(self, tg, banco, baixar=None):
        self.tg, self.banco = tg, banco
        self.baixar = baixar or self._baixar
        self.concursos = []  # última leva baixada, usada pelo /buscar
        self.canal = CANAL
        self.ultimo_post = 0.0

    # dados do portal ------------------------------------------------------
    @staticmethod
    def _baixar():
        r = requests.get(DADOS_URL, timeout=30, headers={"Cache-Control": "no-cache"})
        r.raise_for_status()
        return r.json()["concursos"]

    # comandos -------------------------------------------------------------
    def responder(self, chat_id, texto):
        """Trata uma mensagem e devolve a resposta (ou None)."""
        m = re.match(r"^/(\w+)(?:@\w+)?\s*(.*)$", (texto or "").strip(), re.S)
        if not m:
            return "Use /estado, /palavra ou /buscar. /ajuda mostra tudo."
        cmd, arg = m.group(1).lower(), m.group(2).strip()

        if cmd in ("start", "ajuda", "help"):
            self.banco.inscrever(chat_id)
            return BOAS_VINDAS
        if cmd == "parar":
            self.banco.apagar(chat_id)
            return "✅ Pronto: parei os alertas e apaguei seus dados. Para voltar, é só mandar /start."
        if cmd == "estado":
            siglas, invalidos = ler_estados(arg)
            if not siglas or invalidos:
                extra = f" (não reconheci: {', '.join(invalidos)})" if invalidos else ""
                return f"Mande a sigla ou o nome do estado{extra}. Exemplo: /estado PE ou /estado PE PB"
            for s in siglas:
                self.banco.adicionar(chat_id, "uf", s)
            return self._confirmar(chat_id, f"✅ Estado(s) adicionado(s): {', '.join(s.upper() for s in siglas)}.")
        if cmd == "palavra":
            palavras = [p.strip().lower() for p in arg.split(",") if len(p.strip()) >= 3]
            if not palavras:
                return "Mande a palavra-chave (3 letras ou mais). Exemplo: /palavra professor"
            for p in palavras:
                self.banco.adicionar(chat_id, "palavra", p)
            return self._confirmar(chat_id, f"✅ Palavra(s)-chave adicionada(s): {', '.join(palavras)}.")
        if cmd == "escolaridade":
            nivel = normalizar_escolaridade(arg)
            if not nivel:
                return "Escolha uma: /escolaridade fundamental, medio, tecnico ou superior"
            self.banco.adicionar(chat_id, "escolaridade", nivel)
            return self._confirmar(chat_id, f"✅ Escolaridade adicionada: {ESCOLARIDADES[nivel]}.")
        if cmd == "remover":
            return self._remover(chat_id, arg)
        if cmd == "minhas":
            filtros = self.banco.filtros(chat_id)
            if not any(filtros.values()):
                return "Você ainda não tem filtros. Comece com /estado PE ou /palavra professor."
            return f"{descrever(filtros)}\n\n<a href=\"{link_portal(filtros)}\">Ver no portal</a>"
        if cmd == "buscar":
            return self._buscar(chat_id, arg)
        return "Não conheço esse comando. /ajuda mostra o que eu sei fazer."

    def _confirmar(self, chat_id, texto):
        filtros = self.banco.filtros(chat_id)
        aviso = "" if filtros["uf"] or filtros["palavra"] else "\n\nFalta um estado ou uma palavra-chave para os alertas começarem."
        return f"{texto}\n\n{descrever(filtros)}{aviso}"

    def _remover(self, chat_id, arg):
        alvo = arg.strip().lower()
        if not alvo:
            return "Diga o que remover. Exemplo: /remover PE, /remover professor ou /remover tudo"
        filtros = self.banco.filtros(chat_id)
        if alvo == "tudo":
            for tipo, valores in filtros.items():
                for v in valores:
                    self.banco.remover(chat_id, tipo, v)
            return "✅ Removi todos os seus filtros. Você não vai receber alertas até adicionar outro."
        esc = normalizar_escolaridade(alvo)
        for tipo, valor in (("uf", alvo), ("palavra", alvo), ("escolaridade", esc)):
            if valor and self.banco.remover(chat_id, tipo, valor):
                return self._confirmar(chat_id, f"✅ Removido: {alvo}.")
        return f"Não achei “{arg}” nos seus filtros. Veja com /minhas."

    def _buscar(self, chat_id, termo):
        if len(termo) < 3:
            return "Mande o que procurar (3 letras ou mais). Exemplo: /buscar enfermeiro"
        if not self.concursos:
            self.concursos = self.baixar()
        filtros = self.banco.filtros(chat_id)
        achados, total = buscar(self.concursos, termo, filtros)
        if not achados:
            return f"Nenhum concurso aberto com “{termo}” agora. Use /palavra {termo} para ser avisado quando sair."
        onde = " nos seus estados" if filtros["uf"] else ""
        topo = f"🔎 <b>{total}</b> concurso(s) aberto(s) com “{termo}”{onde}. Os que encerram antes:\n"
        return topo + "\n\n".join(cartao(c).replace("🆕 ", "") for c in achados)

    # alertas --------------------------------------------------------------
    def notificar(self):
        """Avisa os inscritos dos concursos que apareceram desde a última checagem."""
        self.concursos = self.baixar()
        links = {c["link"] for c in self.concursos}
        if not self.banco.tem_vistos():
            # primeira execução: tudo o que já existe vira "visto", senão cada pessoa receberia centenas
            self.banco.marcar_vistos(links)
            log.info("primeira carga: %d concursos marcados como vistos", len(links))
            return 0
        vistos = self.banco.vistos()
        novos = [c for c in self.concursos if c["link"] not in vistos]
        enviadas = 0
        if novos and self.canal:
            # os que encerram antes primeiro; previstos no fim
            ordem = sorted(novos, key=lambda c: (c.get("status") == "previsto", c.get("inscricao_fim") or "9999"))
            self.banco.enfileirar(post_canal(c) for c in ordem)
        if novos:
            for chat_id, filtros in self.banco.todos_os_filtros().items():
                for texto in mensagens_para(novos, filtros):
                    if not self._enviar(chat_id, texto):
                        break
                    enviadas += 1
            self.banco.marcar_vistos(c["link"] for c in novos)
        log.info("%d concursos novos, %d mensagens enviadas", len(novos), enviadas)
        return enviadas

    def anotar_canal(self, upd):
        """Registra o canal quando o bot vira admin dele ou quando há post lá (para achar o ID)."""
        evento = upd.get("my_chat_member") or upd.get("channel_post")
        chat = (evento or {}).get("chat", {})
        if chat.get("type") != "channel":
            return
        status = (upd.get("my_chat_member") or {}).get("new_chat_member", {}).get("status", "post")
        nome = f"@{chat['username']}" if chat.get("username") else "(canal privado)"
        log.info("canal detectado: %s %s id=%s status=%s", chat.get("title"), nome, chat.get("id"), status)
        self.banco.gravar("canal_detectado", f"{chat.get('id')} {nome} {chat.get('title')}")

    def publicar_no_canal(self):
        """Publica o próximo post da fila, se já passou a pausa. Volta True se ainda há fila."""
        if not self.canal:
            return False
        item = self.banco.proximo_da_fila()
        if not item:
            return False
        if time.time() - self.ultimo_post >= PAUSA_CANAL_S:
            id_, texto = item
            try:
                self.tg.enviar(self.canal, texto)
            except (Bloqueado, RuntimeError) as e:
                # bot fora do canal ou sem permissão: descarta para não travar a fila
                log.warning("não consegui publicar no canal %s: %s", self.canal, e)
            self.banco.tirar_da_fila(id_)
            self.ultimo_post = time.time()
        return self.banco.tamanho_fila() > 0

    def _enviar(self, chat_id, texto):
        try:
            self.tg.enviar(chat_id, texto)
            time.sleep(PAUSA_ENVIO_S)
            return True
        except Bloqueado:
            log.info("chat bloqueou o bot; dados apagados")
            self.banco.apagar(chat_id)
            return False

    # laço principal -------------------------------------------------------
    def rodar(self):
        self.tg.definir_comandos(COMANDOS)
        offset = int(self.banco.ler("offset", 0))
        proxima = 0.0
        log.info("no ar; %d inscritos; canal: %s", self.banco.total_inscritos(), self.canal or "nenhum")
        while True:
            try:
                if time.time() >= proxima:
                    proxima = time.time() + INTERVALO_MIN * 60
                    self.notificar()
                # com fila no canal, espera pouco por mensagens para voltar logo ao próximo post
                espera = 3 if self.publicar_no_canal() else 25
                for upd in self.tg.atualizacoes(offset, espera):
                    offset = upd["update_id"] + 1
                    self.anotar_canal(upd)
                    msg = upd.get("message") or {}
                    chat = msg.get("chat", {})
                    if chat.get("type") != "private" or "text" not in msg:
                        continue
                    resposta = self.responder(chat["id"], msg["text"])
                    if resposta:
                        self._enviar(chat["id"], resposta)
                self.banco.gravar("offset", offset)
            except (requests.RequestException, RuntimeError, ValueError) as e:
                log.warning("erro no laço: %s", e)
                time.sleep(10)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise SystemExit("defina TELEGRAM_TOKEN (no .env do servidor)")
    os.makedirs(os.path.dirname(BANCO) or ".", exist_ok=True)
    Bot(Telegram(token), Banco(BANCO)).rodar()


if __name__ == "__main__":
    main()
