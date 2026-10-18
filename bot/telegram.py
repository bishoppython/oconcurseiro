"""Cliente mínimo da API do Telegram (long polling: não precisa abrir porta no servidor)."""

import logging
import time

import requests

log = logging.getLogger("telegram")


class Bloqueado(Exception):
    """A pessoa bloqueou o bot ou apagou a conta: os dados dela devem ser apagados."""


class Telegram:
    def __init__(self, token, sessao=None):
        self.base = f"https://api.telegram.org/bot{token}/"
        self.sessao = sessao or requests.Session()

    def _chamar(self, metodo, tempo_http=30, **params):
        r = self.sessao.post(self.base + metodo, json=params, timeout=tempo_http)
        dados = r.json()
        if not dados.get("ok"):
            if r.status_code == 403:
                raise Bloqueado(dados.get("description"))
            if r.status_code == 429:  # limite de envio: espera o que o Telegram pedir e tenta de novo
                espera = dados.get("parameters", {}).get("retry_after", 5)
                log.warning("limite do Telegram; esperando %s s", espera)
                time.sleep(espera)
                return self._chamar(metodo, tempo_http, **params)
            raise RuntimeError(f"{metodo}: {dados.get('description')}")
        return dados["result"]

    def atualizacoes(self, offset, espera=25):
        """Mensagens novas; segura a conexão até `espera` s se não houver nenhuma."""
        return self._chamar("getUpdates", tempo_http=espera + 10, offset=offset, timeout=espera,
                            allowed_updates=["message"])

    def enviar(self, chat_id, texto):
        self._chamar("sendMessage", chat_id=chat_id, text=texto, parse_mode="HTML",
                     link_preview_options={"is_disabled": True})

    def definir_comandos(self, comandos):
        self._chamar("setMyCommands", commands=[{"command": c, "description": d} for c, d in comandos])
