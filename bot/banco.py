"""Banco privado do bot (SQLite, no servidor): só o ID do chat, os filtros e o que já foi visto.

Nada daqui vai para o repositório público. /parar apaga tudo da pessoa (LGPD).
"""

import sqlite3
from datetime import datetime, timezone

TIPOS = ("uf", "palavra", "escolaridade")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS inscritos (
    chat_id INTEGER PRIMARY KEY,
    criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS filtros (
    chat_id INTEGER NOT NULL REFERENCES inscritos(chat_id) ON DELETE CASCADE,
    tipo TEXT NOT NULL CHECK (tipo IN ('uf', 'palavra', 'escolaridade')),
    valor TEXT NOT NULL,
    PRIMARY KEY (chat_id, tipo, valor)
);
CREATE TABLE IF NOT EXISTS vistos (
    link TEXT PRIMARY KEY,
    visto_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS estado (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
"""


def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Banco:
    def __init__(self, caminho):
        self.con = sqlite3.connect(caminho)
        self.con.execute("PRAGMA foreign_keys = ON")
        self.con.executescript(ESQUEMA)

    # inscritos e filtros ---------------------------------------------------
    def inscrever(self, chat_id):
        with self.con:
            self.con.execute("INSERT OR IGNORE INTO inscritos VALUES (?, ?)", (chat_id, agora()))

    def apagar(self, chat_id):
        with self.con:
            self.con.execute("DELETE FROM inscritos WHERE chat_id = ?", (chat_id,))

    def adicionar(self, chat_id, tipo, valor):
        self.inscrever(chat_id)
        with self.con:
            self.con.execute("INSERT OR IGNORE INTO filtros VALUES (?, ?, ?)", (chat_id, tipo, valor))

    def remover(self, chat_id, tipo, valor):
        with self.con:
            cur = self.con.execute("DELETE FROM filtros WHERE chat_id = ? AND tipo = ? AND valor = ?",
                                   (chat_id, tipo, valor))
        return cur.rowcount > 0

    def filtros(self, chat_id):
        """{'uf': [...], 'palavra': [...], 'escolaridade': [...]}"""
        out = {t: [] for t in TIPOS}
        for tipo, valor in self.con.execute(
                "SELECT tipo, valor FROM filtros WHERE chat_id = ? ORDER BY tipo, valor", (chat_id,)):
            out[tipo].append(valor)
        return out

    def todos_os_filtros(self):
        """{chat_id: filtros} de todos os inscritos."""
        out = {}
        for (chat_id,) in self.con.execute("SELECT chat_id FROM inscritos"):
            out[chat_id] = {t: [] for t in TIPOS}
        for chat_id, tipo, valor in self.con.execute("SELECT chat_id, tipo, valor FROM filtros"):
            out[chat_id][tipo].append(valor)
        return out

    def total_inscritos(self):
        return self.con.execute("SELECT COUNT(*) FROM inscritos").fetchone()[0]

    # concursos já vistos ---------------------------------------------------
    def tem_vistos(self):
        return self.con.execute("SELECT 1 FROM vistos LIMIT 1").fetchone() is not None

    def vistos(self):
        return {link for (link,) in self.con.execute("SELECT link FROM vistos")}

    def marcar_vistos(self, links):
        with self.con:
            self.con.executemany("INSERT OR IGNORE INTO vistos VALUES (?, ?)", [(l, agora()) for l in links])

    # estado do bot (offset do Telegram) -----------------------------------
    def ler(self, chave, padrao=None):
        linha = self.con.execute("SELECT valor FROM estado WHERE chave = ?", (chave,)).fetchone()
        return linha[0] if linha else padrao

    def gravar(self, chave, valor):
        with self.con:
            self.con.execute("INSERT OR REPLACE INTO estado VALUES (?, ?)", (chave, str(valor)))
