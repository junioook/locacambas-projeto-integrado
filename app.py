"""Locaçambas — Sistema de Controle de Locação de Caçambas (Projeto Integrado).

Funcionalidades:
  • Login de atendente
  • Cadastro e consulta de clientes          (gravação + leitura no banco)
  • Registro de locação de caçamba            (gravação + leitura no banco)
  • Consulta de caçambas em campo e retirada
"""
import re
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database import conectar, inicializar

app = Flask(__name__)
app.secret_key = "troque-esta-chave-em-producao"


ICONES = {
    'locacao': '<svg viewBox="0 0 24 24"><path d="M20 8h-3V4H3c-1.1 0-2 .9-2 2v11h2c0 1.66 1.34 3 3 3s3-1.34 3-3h6c0 1.66 1.34 3 3 3s3-1.34 3-3h2v-5l-3-4zM6 18.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm13.5-9 1.96 2.5H17V9.5h2.5zm-1.5 9c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>',
    'clientes': '<svg viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>',
    'campo': '<svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>',
    'frota': '<svg viewBox="0 0 24 24"><path d="M3 6h18l-2 13H5L3 6zm5-3h8v2H8V3z"/></svg>',
    'livre': '<svg viewBox="0 0 24 24"><path d="M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>',
    'voltar': '<svg viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>'
}


@app.context_processor
def injetar_icones():
    return {"icones": ICONES}


@app.template_filter("data_br")
def data_br(iso):
    """2026-10-28 -> 28/10/2026"""
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


def ler_data(texto):
    """'26/10/2026' -> '2026-10-26' (formato ISO gravado no banco); None se inválida."""
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


@app.template_filter("fone")
def fone(num):
    """94991234567 -> (94) 99123-4567"""
    if len(num) == 11:
        return f"({num[:2]}) {num[2:7]}-{num[7:]}"
    if len(num) == 10:
        return f"({num[:2]}) {num[2:6]}-{num[6:]}"
    return num


# ---------------------------------------------------------------- autenticação
def login_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Faça login para acessar o sistema.", "erro")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_ = request.form.get("login", "").strip()
        senha = request.form.get("senha", "")
        with conectar() as con:
            u = con.execute("SELECT * FROM usuario WHERE login = ?", (login_,)).fetchone()
        if u and check_password_hash(u["senha_hash"], senha):
            session["usuario_id"], session["usuario_nome"] = u["id"], u["nome"]
            return redirect(url_for("inicio"))
        flash("Usuário ou senha inválidos.", "erro")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------- FUNCIONALIDADE 1: CLIENTES
TELEFONE_RE = re.compile(r"^\d{10,11}$")


def validar_cliente(nome, telefone, cpf_cnpj):
    erros = []
    if not nome:
        erros.append("O nome do cliente é obrigatório.")
    if not TELEFONE_RE.match(telefone):
        erros.append("Telefone inválido: informe DDD + número (10 ou 11 dígitos).")
    if cpf_cnpj and len(cpf_cnpj) not in (11, 14):
        erros.append("CPF deve ter 11 dígitos ou CNPJ 14 dígitos.")
    return erros


@app.route("/clientes", methods=["GET", "POST"])
@login_obrigatorio
def clientes():
    form = {}
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in ("nome", "cpf_cnpj", "telefone", "endereco")}
        telefone = re.sub(r"\D", "", form["telefone"])
        cpf_cnpj = re.sub(r"\D", "", form["cpf_cnpj"])
        erros = validar_cliente(form["nome"], telefone, cpf_cnpj)

        if not erros:
            with conectar() as con:
                if cpf_cnpj and con.execute(
                    "SELECT 1 FROM cliente WHERE cpf_cnpj = ?", (cpf_cnpj,)
                ).fetchone():
                    erros.append("Já existe um cliente com este CPF/CNPJ.")
                else:
                    con.execute(
                        "INSERT INTO cliente (nome, cpf_cnpj, telefone, endereco) VALUES (?, ?, ?, ?)",
                        (form["nome"], cpf_cnpj or None, telefone, form["endereco"]),
                    )
                    flash(f"Cliente “{form['nome']}” cadastrado com sucesso.", "ok")
                    return redirect(url_for("clientes"))
        for e in erros:
            flash(e, "erro")

    busca = request.args.get("q", "").strip()
    with conectar() as con:
        lista = con.execute(
            "SELECT * FROM cliente WHERE nome LIKE ? ORDER BY nome",
            (f"%{busca}%",),
        ).fetchall()
    return render_template("clientes.html", clientes=lista, form=form, busca=busca)


# ------------------------------------------------- FUNCIONALIDADE 2: LOCAÇÃO
@app.route("/locacoes/nova", methods=["GET", "POST"])
@login_obrigatorio
def nova_locacao():
    hoje = date.today()
    form = {"data_entrega": hoje.strftime("%d/%m/%Y"),
            "data_prev_ret": (hoje + timedelta(days=7)).strftime("%d/%m/%Y")}

    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in
                ("cliente_id", "cacamba_id", "endereco_obra", "data_entrega", "data_prev_ret", "valor")}
        erros = []
        if not form["cliente_id"]:
            erros.append("Selecione o cliente.")
        if not form["cacamba_id"]:
            erros.append("Selecione a caçamba.")
        if not form["endereco_obra"]:
            erros.append("Informe o endereço da obra.")
        entrega, prev_ret = ler_data(form["data_entrega"]), ler_data(form["data_prev_ret"])
        if not entrega or not prev_ret:
            erros.append("Informe as datas no formato dd/mm/aaaa.")
        elif prev_ret < entrega:
            erros.append("A previsão de retirada não pode ser anterior à entrega.")
        try:
            valor = float(form["valor"].replace(",", "."))
            if valor <= 0:
                raise ValueError
        except ValueError:
            erros.append("Informe um valor maior que zero.")

        if not erros:
            with conectar() as con:
                cac = con.execute("SELECT * FROM cacamba WHERE id = ?", (form["cacamba_id"],)).fetchone()
                # Regra de negócio: só é possível locar uma caçamba DISPONÍVEL
                if cac is None or cac["status"] != "DISPONIVEL":
                    erros.append(f"A caçamba {cac['numero'] if cac else ''} não está disponível para locação.")
                else:
                    con.execute(
                        """INSERT INTO locacao (cliente_id, cacamba_id, usuario_id, endereco_obra,
                                                data_entrega, data_prev_ret, valor)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (form["cliente_id"], cac["id"], session["usuario_id"], form["endereco_obra"],
                         entrega, prev_ret, valor),
                    )
                    con.execute("UPDATE cacamba SET status = 'LOCADA' WHERE id = ?", (cac["id"],))
                    flash(f"Locação registrada: caçamba {cac['numero']} enviada para a obra.", "ok")
                    return redirect(url_for("cacambas"))
        for e in erros:
            flash(e, "erro")

    with conectar() as con:
        lista_clientes = con.execute("SELECT id, nome FROM cliente ORDER BY nome").fetchall()
        lista_cacambas = con.execute("SELECT * FROM cacamba ORDER BY numero").fetchall()
    return render_template("nova_locacao.html", clientes=lista_clientes,
                           cacambas=lista_cacambas, form=form)


# ------------------------------------------------------------ TELA INICIAL
@app.route("/")
@login_obrigatorio
def inicio():
    hoje = date.today().isoformat()
    with conectar() as con:
        total = con.execute("SELECT COUNT(*) FROM cacamba").fetchone()[0]
        disponiveis = con.execute(
            "SELECT COUNT(*) FROM cacamba WHERE status = 'DISPONIVEL'").fetchone()[0]
        em_campo = con.execute(
            "SELECT COUNT(*) FROM locacao WHERE status = 'ATIVA'").fetchone()[0]
        atrasadas = con.execute(
            "SELECT COUNT(*) FROM locacao WHERE status = 'ATIVA' AND data_prev_ret < ?",
            (hoje,)).fetchone()[0]
    return render_template("inicio.html", total=total, disponiveis=disponiveis,
                           em_campo=em_campo, atrasadas=atrasadas)


# ------------------------------------------ CONSULTA: CAÇAMBAS EM CAMPO / RETIRADA
@app.route("/cacambas")
@login_obrigatorio
def cacambas():
    with conectar() as con:
        em_campo = con.execute(
            """SELECT l.id, c.numero, c.capacidade, cl.nome AS cliente, cl.telefone,
                      l.endereco_obra, l.data_entrega, l.data_prev_ret, l.valor
                 FROM locacao l
                 JOIN cacamba c  ON c.id  = l.cacamba_id
                 JOIN cliente cl ON cl.id = l.cliente_id
                WHERE l.status = 'ATIVA'
                ORDER BY l.data_prev_ret"""
        ).fetchall()
        frota = con.execute("SELECT * FROM cacamba ORDER BY numero").fetchall()
    return render_template("cacambas.html", em_campo=em_campo, frota=frota,
                           hoje=date.today().isoformat())


@app.route("/locacoes/<int:locacao_id>/retirar", methods=["POST"])
@login_obrigatorio
def retirar(locacao_id):
    with conectar() as con:
        loc = con.execute("SELECT * FROM locacao WHERE id = ? AND status = 'ATIVA'", (locacao_id,)).fetchone()
        if loc:
            con.execute("UPDATE locacao SET status = 'ENCERRADA', data_retirada = date('now','localtime') WHERE id = ?",
                        (locacao_id,))
            con.execute("UPDATE cacamba SET status = 'DISPONIVEL' WHERE id = ?", (loc["cacamba_id"],))
            flash("Retirada registrada. Caçamba disponível novamente.", "ok")
    return redirect(url_for("cacambas"))


inicializar()

if __name__ == "__main__":
    app.run(debug=True)
