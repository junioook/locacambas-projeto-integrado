"""Criação e acesso ao banco de dados SQLite do sistema de locação de caçambas."""
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).with_name("cacambas.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuario (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    login       TEXT    NOT NULL UNIQUE,
    senha_hash  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS cliente (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    cpf_cnpj    TEXT    UNIQUE,
    telefone    TEXT    NOT NULL,
    endereco    TEXT,
    criado_em   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS cacamba (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    numero      TEXT    NOT NULL UNIQUE,
    capacidade  REAL    NOT NULL,              -- em m³
    status      TEXT    NOT NULL DEFAULT 'DISPONIVEL'
                CHECK (status IN ('DISPONIVEL', 'LOCADA', 'MANUTENCAO'))
);

CREATE TABLE IF NOT EXISTS locacao (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id      INTEGER NOT NULL REFERENCES cliente(id),
    cacamba_id      INTEGER NOT NULL REFERENCES cacamba(id),
    usuario_id      INTEGER NOT NULL REFERENCES usuario(id),
    endereco_obra   TEXT    NOT NULL,
    data_entrega    TEXT    NOT NULL,
    data_prev_ret   TEXT    NOT NULL,
    data_retirada   TEXT,
    valor           REAL    NOT NULL CHECK (valor > 0),
    status          TEXT    NOT NULL DEFAULT 'ATIVA'
                    CHECK (status IN ('ATIVA', 'ENCERRADA'))
);
"""


def conectar():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def inicializar():
    """Cria as tabelas e insere dados iniciais (usuário e frota) se o banco estiver vazio."""
    with conectar() as con:
        con.executescript(SCHEMA)
        if con.execute("SELECT COUNT(*) FROM usuario").fetchone()[0] == 0:
            con.execute(
                "INSERT INTO usuario (nome, login, senha_hash) VALUES (?, ?, ?)",
                ("Atendente", "admin", generate_password_hash("admin123")),
            )
        if con.execute("SELECT COUNT(*) FROM cacamba").fetchone()[0] == 0:
            frota = [("C-01", 4), ("C-02", 4), ("C-03", 5), ("C-04", 5), ("C-05", 7)]
            con.executemany(
                "INSERT INTO cacamba (numero, capacidade) VALUES (?, ?)", frota
            )


if __name__ == "__main__":
    inicializar()
    print(f"Banco criado em {DB_PATH}")
