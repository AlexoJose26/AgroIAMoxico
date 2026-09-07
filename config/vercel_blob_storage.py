import os
import uuid
from pathlib import Path

from django.core.files.storage import Storage
from django.core.exceptions import SuspiciousOperation

from vercel.blob import BlobClient


class VercelBlobStorage(Storage):
    """
    Storage Django baseado no Vercel Blob.

    Utilizado em produção para armazenar:
    - fotos de perfil;
    - imagens dos produtos;
    - imagens dos diagnósticos.
    """

    def __init__(self):
        self.token = os.environ.get("BLOB_READ_WRITE_TOKEN")

        if not self.token:
            raise RuntimeError(
                "BLOB_READ_WRITE_TOKEN não está configurado."
            )

        self.public_url = os.environ.get("BLOB_PUBLIC_URL")

        if not self.public_url:
            raise RuntimeError(
                "BLOB_PUBLIC_URL não está configurado."
            )

        self.client = BlobClient(token=self.token)

    # ============================================================
    # NORMALIZAÇÃO
    # ============================================================

    def _normalizar_nome(self, name):
        name = str(name).replace("\\", "/").lstrip("/")

        partes = Path(name).parts

        if ".." in partes:
            raise SuspiciousOperation(
                "Nome de ficheiro inválido."
            )

        return name

    # ============================================================
    # NOME ÚNICO
    # ============================================================

    def _gerar_nome_unico(self, name):
        name = self._normalizar_nome(name)

        caminho = Path(name)

        diretorio = caminho.parent
        extensao = caminho.suffix.lower()
        nome_base = caminho.stem

        identificador = uuid.uuid4().hex

        novo_nome = f"{nome_base}_{identificador}{extensao}"

        if str(diretorio) == ".":
            return novo_nome

        return f"{diretorio.as_posix()}/{novo_nome}"

    # ============================================================
    # GUARDAR
    # ============================================================

    def _save(self, name, content):
        name = self._gerar_nome_unico(name)

        if hasattr(content, "seek"):
            content.seek(0)

        conteudo = content.read()

        content_type = getattr(
            content,
            "content_type",
            None,
        )

        if not content_type:
            content_type = "application/octet-stream"

        resultado = self.client.put(
            name,
            conteudo,
            access="public",
            content_type=content_type,
        )

        return resultado.pathname

    # ============================================================
    # URL PÚBLICA
    # ============================================================

    def url(self, name):
        if not name:
            return ""

        name = self._normalizar_nome(name)

        return (
            f"{self.public_url.rstrip('/')}/"
            f"{name.lstrip('/')}"
        )

    # ============================================================
    # EXISTÊNCIA
    # ============================================================

    def exists(self, name):
        # _save() cria nomes únicos, portanto não precisamos
        # consultar o filesystem local.
        return False

    # ============================================================
    # ELIMINAR
    # ============================================================

    def delete(self, name):
        if not name:
            return

        name = self._normalizar_nome(name)

        try:
            self.client.delete(name)
        except Exception:
            # Se o ficheiro já não existir, não interrompemos
            # a operação do Django.
            pass

    # ============================================================
    # TAMANHO
    # ============================================================

    def size(self, name):
        raise NotImplementedError(
            "size() não está implementado para este storage."
        )

    # ============================================================
    # ABRIR
    # ============================================================

    def _open(self, name, mode="rb"):
        raise NotImplementedError(
            "A abertura direta pelo storage não está implementada."
        )
