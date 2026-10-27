
from datetime import timedelta
from functools import wraps
import os
import secrets
import hmac
from dotenv import load_dotenv

from flask import (
    Flask,
    redirect,
    session,
    render_template,
    request,
    jsonify,
    flash,
    url_for
)

from backend.auth import GerenciadorDeAutenticacao
from backend.controllers.chat_controller import criar_chat_blueprint

app = Flask(__name__)

load_dotenv()

app.secret_key = os.getenv("FLASK_SECRET_KEY")

# TEMPORÁRIO: configurar uma chave secreta persistente
# por variável de ambiente antes de publicar.


if not app.secret_key:
    raise RuntimeError(
        "A variável de ambiente FLASK_SECRET_KEY não foi configurada."
    )

# Expiração após 30 minutos sem atividade.
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

# Proteções do cookie da sessão.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True

sistema = GerenciadorDeAutenticacao()

def sessao_valida():
    """Confere se a sessão corresponde à versão atual do usuário."""
    usuario = session.get("usuario")
    versao = session.get("versao_auth")

    if not usuario or versao is None:
        return False

    return sistema.validar_versao_autenticacao(
        usuario,
        versao
    )


def exigir_login(api=False):
    """Protege páginas e endpoints autenticados."""

    def decorador(funcao):
        @wraps(funcao)
        def wrapper(*args, **kwargs):
            if not sessao_valida():
                session.clear()

                if api:
                    return jsonify({
                        "error": "Sessão inválida ou expirada. Faça login novamente."
                    }), 401

                return redirect("/login")

            return funcao(*args, **kwargs)

        return wrapper

    return decorador

app.register_blueprint(
    criar_chat_blueprint(exigir_login, app)
)

@app.route("/")
def index():
    if sessao_valida():
        return redirect("/chat")

    session.clear()
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")

        if sistema.autenticar_usuario(usuario, senha):
            # Limpa os dados anteriores antes de criar a sessão.
            session.clear()

            session["usuario"] = usuario
            session["versao_auth"] = (
                sistema.obter_versao_autenticacao(usuario)
            )

            # Ativa a expiração permanente de 30 minutos.
            session.permanent = True

            return redirect("/chat")

        return redirect("/erro")

    if sessao_valida():
        return redirect("/chat")

    session.clear()
    return render_template("login.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if sessao_valida():
        return redirect("/chat")
    
    if request.method == "GET":
        session["csrf_cadastro"] = secrets.token_urlsafe(32)
        return render_template("cadastro.html")

    token_form = request.form.get("csrf_token", "")
    token_sessao = session.get("csrf_cadastro", "")

    if not token_sessao or not hmac.compare_digest(
        token_form, token_sessao
    ):

        return "Requisição inválida. Atualize a página.", 400

    session.pop("csrf_token", None)

    usuario = request.form.get("usuario", "").strip()
    senha = request.form.get("senha", "")
    confirmar = request.form.get("confirmar_senha", "")
    if not usuario or not senha or not confirmar:
        flash("Preencha todos os campos.", "erro")
        return redirect(url_for("cadastro"))

    if not 3 <= len(usuario) <= 40:
        flash("O usuário deve ter entre 3 e 40 caracteres.", "erro")
        return redirect(url_for("cadastro"))

    if len(senha) < 12:
        flash("A senha deve ter pelo menos 12 caracteres.", "erro")
        return redirect(url_for("cadastro"))

    if len(senha) > 1024:
        flash("A senha ultrapassa o tamanho permitido.", "erro")
        return redirect(url_for("cadastro"))

    if senha != confirmar:
        flash("As senhas não coincidem.", "erro")
        return redirect(url_for("cadastro"))

    try:
        sucesso = sistema.cadastrar_usuario(
            usuario=usuario,
            senha_plana=senha,
            tipo="cliente"
        )
    except OSError:
        app.logger.exception("Falha ao persistir novo usuário.")
        flash("Não foi possível concluir o cadastro.", "erro")
        return redirect(url_for("cadastro"))

    if not sucesso:
        flash(
            "Não foi possível cadastrar. Verifique os dados "
            "ou tente outro nome de usuário.",
            "erro"
        )
        return redirect(url_for("cadastro"))

    flash("Cadastro realizado! Você já pode entrar na L.I.A.", "sucesso")
    return redirect(url_for("login"))


@app.route("/chat")
@exigir_login()
def chat():
    return render_template("chat.html")

@app.route("/erro")
def erro():
    return render_template("error.html")

@app.route("/logout", methods=["POST"])
@exigir_login()
def logout():
    session.clear()
    return redirect("/login")



if __name__ == "__main__":
    from waitress import serve

    serve(
        app,
        host="127.0.0.1",
        port=8081
    )
