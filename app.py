"""Sistema de Controle de Locação de Caçambas — Projeto Integrado.

Funcionalidades:
  • Login de atendente
  • Cadastro e consulta de clientes          (gravação + leitura no banco)
  • Registro de locação de caçamba            (gravação + leitura no banco)
  • Consulta de caçambas em campo e retirada
"""
import re
from datetime import date, timedelta
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database import conectar, inicializar

app = Flask(__name__)
app.secret_key = "troque-esta-chave-em-producao"


@app.template_filter("data_br")
def data_br(iso):
    """2026-10-28 -> 28/10/2026"""
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


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
            return redirect(url_for("cacambas"))
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
    form = {"data_entrega": hoje.isoformat(), "data_prev_ret": (hoje + timedelta(days=7)).isoformat()}

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
        if form["data_prev_ret"] < form["data_entrega"]:
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
                         form["data_entrega"], form["data_prev_ret"], valor),
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


# ------------------------------------------ CONSULTA: CAÇAMBAS EM CAMPO / RETIRADA
@app.route("/")
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
