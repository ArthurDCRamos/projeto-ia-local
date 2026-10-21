
import base64
import bcrypt
import hashlib
import json
import os
import tempfile
import threading

from pathlib import Path


class GerenciadorDeAutenticacao:
    TIPOS_VALIDOS = {"desenvolvedor", "cliente"}
    def __init__(self, caminho_db=None):
        self.__arquivo_db = (
            Path(caminho_db)
            if caminho_db is not None
            else Path(__file__).resolve().parent / "usuarios.json"
        )

        self.__lock = threading.RLock()
        self.__usuarios_db = {}

        self.__arquivo_db.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.__carregar_usuarios()

    def __carregar_usuarios(self):
        """Carrega os usuários do arquivo JSON."""
        with self.__lock:
            if not self.__arquivo_db.exists():
                self.__salvar_usuarios()
                return

            try:
                with self.__arquivo_db.open(
                    "r", encoding="utf-8"
                ) as arquivo:
                    dados = json.load(arquivo)

                if not isinstance(dados, dict):
                    raise ValueError("Formato JSON inválido.")

                precisa_migrar = False

                for usuario, registro in dados.items():
                    if (not isinstance(usuario, str) or not usuario.strip()):
                        raise ValueError("Nome de usuário inválido.")

                    if not isinstance(registro, dict):
                        raise ValueError(
                            f"Registro inválido para '{usuario}'."
                        )

                    senha_hash = registro.get("senha_hash")
                    versao = registro.get("versao_auth")

                    if (
                        not isinstance(senha_hash, str)
                        or not isinstance(versao, int)
                        or isinstance(versao, bool)
                        or versao < 1
                    ):
                        raise ValueError(
                            f"Dados inválidos para '{usuario}'."
                        )

                    if not senha_hash.startswith(
                        ("$2a$", "$2b$", "$2y$")
                    ):
                        raise ValueError(
                            f"Hash bcrypt inválido para '{usuario}'."
                        )

                    tipo = registro.get("tipo")
                    
                    if tipo is None:
                        tipo="cliente"
                        precisa_migrar = True

                    if tipo not in self.TIPOS_VALIDOS:
                        raise ValueError(f"Tipo inválido para '{usuario}'.")

                    self.__usuarios_db[usuario] = {
                        "senha_hash": senha_hash,
                        "versao_auth": versao,
                        "tipo": tipo
                    }
                if precisa_migrar:
                    self.__salvar_usuarios()
                        
            except (json.JSONDecodeError, OSError, ValueError) as erro:
                raise RuntimeError(
                    f"Falha ao carregar usuários: {erro}"
                ) from erro

    def __salvar_usuarios(self):
        """Grava os dados usando substituição atômica."""
        arquivo_temporario = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.__arquivo_db.parent,
                delete=False
            ) as arquivo:
                arquivo_temporario = arquivo.name

                json.dump(
                    self.__usuarios_db,
                    arquivo,
                    ensure_ascii=False,
                    indent=4
                )

                arquivo.flush()
                os.fsync(arquivo.fileno())

            os.replace(
                arquivo_temporario,
                self.__arquivo_db
            )

        except OSError:
            if (
                arquivo_temporario
                and os.path.exists(arquivo_temporario)
            ):
                os.remove(arquivo_temporario)

            raise

    def _tratar_senha(self, senha_plana: str) -> bytes:
        """Aplica SHA-256 e Base64 antes do bcrypt."""
        if not isinstance(senha_plana, str):
            raise TypeError("A senha deve ser uma string.")

        digest = hashlib.sha256(
            senha_plana.encode("utf-8")
        ).digest()

        return base64.b64encode(digest)

    def cadastrar_usuario(
        self,
        usuario: str,
        senha_plana: str,
        tipo: str = "cliente"
    ) -> bool:
        """Cadastra um usuário novo."""
        if not isinstance(usuario, str) or not usuario.strip():
            return False

        usuario = usuario.strip()

        if not isinstance(senha_plana, str) or not senha_plana:
            return False
        if tipo not in self.TIPOS_VALIDOS:
            return False

        with self.__lock:
            if usuario in self.__usuarios_db:
                return False

            senha_hash = bcrypt.hashpw(
                self._tratar_senha(senha_plana),
                bcrypt.gensalt()
            ).decode("ascii")

            self.__usuarios_db[usuario] = {
                "senha_hash": senha_hash,
                "versao_auth": 1,
                "tipo": tipo
            }

            try:
                self.__salvar_usuarios()
            except OSError:
                del self.__usuarios_db[usuario]
                raise

            return True

    def autenticar_usuario(
        self,
        usuario: str,
        senha_plana: str
    ) -> bool:
        """Confere o usuário e a senha."""
        if (
            not isinstance(usuario, str)
            or not isinstance(senha_plana, str)
        ):
            return False

        with self.__lock:
            registro = self.__usuarios_db.get(usuario)

            if registro is None:
                return False

            try:
                return bcrypt.checkpw(
                    self._tratar_senha(senha_plana),
                    registro["senha_hash"].encode("ascii")
                )
            except (ValueError, TypeError):
                return False
    def obter_tipo_usuario(self, usuario: str):
        with self.__lock:
            registro = self.__usuarios_db.get(usuario)

            if registro is None:
                return None
            return registro["tipo"]



    def alterar_senha(
        self,
        usuario: str,
        senha_atual: str,
        nova_senha: str
    ) -> bool:
        """Altera a senha e incrementa a versão de autenticação."""
        if (
            not isinstance(usuario, str)
            or not isinstance(senha_atual, str)
            or not isinstance(nova_senha, str)
            or not nova_senha
        ):
            return False

        with self.__lock:
            registro = self.__usuarios_db.get(usuario)

            if registro is None:
                return False

            try:
                senha_correta = bcrypt.checkpw(
                    self._tratar_senha(senha_atual),
                    registro["senha_hash"].encode("ascii")
                )
            except (ValueError, TypeError):
                return False

            if not senha_correta:
                return False

            novo_hash = bcrypt.hashpw(
                self._tratar_senha(nova_senha),
                bcrypt.gensalt()
            ).decode("ascii")

            registro_anterior = registro.copy()

            self.__usuarios_db[usuario] = {
                "senha_hash": novo_hash,
                "versao_auth": registro["versao_auth"] + 1,
                "tipo": registro["tipo"]
            }

            try:
                self.__salvar_usuarios()
            except OSError:
                self.__usuarios_db[usuario] = registro_anterior
                raise

            return True

    def obter_versao_autenticacao(self, usuario: str):
        """Retorna a versão atual ou None se o usuário não existir."""
        with self.__lock:
            registro = self.__usuarios_db.get(usuario)

            if registro is None:
                return None

            return registro["versao_auth"]

    def validar_versao_autenticacao(
        self,
        usuario: str,
        versao: int
    ) -> bool:
        """Verifica se a versão guardada na sessão ainda é válida."""
        versao_atual = self.obter_versao_autenticacao(usuario)

        return (
            versao_atual is not None
            and type(versao) is int
            and versao == versao_atual
        )
