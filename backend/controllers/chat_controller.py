import requests

from flask import Blueprint, jsonify, request

from backend.models.ia_model import (
    gerar_resposta,
    LLMOcupadaError
)


def criar_chat_blueprint(exigir_login, app):
    chat_bp = Blueprint("chat", __name__)

    @chat_bp.route("/api/chat", methods=["POST"])
    @exigir_login(api=True)
    def api_chat():
        try:
            dados = request.get_json(silent=True)

            if not isinstance(dados, dict):
                return jsonify({
                    "error": "Requisição JSON inválida"
                }), 400

            mensagem = dados.get("message", "")

            if not isinstance(mensagem, str) or not mensagem.strip():
                return jsonify({
                    "error": "Mensagem vazia"
                }), 400

            app.logger.info("Solicitação recebida pelo controller")

            texto = gerar_resposta(mensagem.strip())

            return jsonify({
                "response": texto
            })

        except LLMOcupadaError as erro:
            return jsonify({
                "error": str(erro)
            }), 503

        except requests.RequestException:
            app.logger.exception("Erro ao comunicar com a LLM")

            return jsonify({
                "error": "Erro ao comunicar com a IA"
            }), 502

        except (KeyError, IndexError, TypeError, ValueError):
            app.logger.exception("Resposta inválida da LLM")

            return jsonify({
                "error": "Resposta inválida da IA"
            }), 502

        except Exception:
            app.logger.exception("Erro interno no chat")

            return jsonify({
                "error": "Erro interno"
            }), 500

    return chat_bp
