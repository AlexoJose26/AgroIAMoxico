import os
import uuid
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import SuspiciousOperation
from django.core.files.storage import Storage
from vercel.blob import BlobClient


class VercelBlobStorage(Storage):
    def __init__(self):
        self.token = os.environ.get("BLOB_READ_WRITE_TOKEN")

        if not self.token:
            raise RuntimeError(
                "BLOB_READ_WRITE_TOKEN não está configurado."
            )

        self.client = BlobClient(
            token=self.token
        )

    def _normalizar_nome(self, name):
        name = str(name).replace("\\", "/").lstrip("/")

        if name.startswith("http://") or name.startswith("https://"):
            return name

        partes = Path(name).parts

        if ".." in partes:
            raise SuspiciousOperation(
                "Nome de ficheiro inválido."
            )

        return name

    def _gerar_nome_unico(self, name):
        name = self._normalizar_nome(name)

        if name.startswith("http://") or name.startswith("https://"):
            return name

        caminho = Path(name)

        diretorio = caminho.parent
        extensao = caminho.suffix.lower()
        nome_base = caminho.stem

        identificador = uuid.uuid4().hex

        novo_nome = (
            f"{nome_base}_{identificador}{extensao}"
        )

        if str(diretorio) == ".":
            return novo_nome

        return (
            f"{diretorio.as_posix()}/"
            f"{novo_nome}"
        )

    def _pathname_from_url(self, name):
        if not name:
            return ""

        name = str(name)

        if not (
            name.startswith("http://")
            or name.startswith("https://")
        ):
            return self._normalizar_nome(name)

        parsed = urlparse(name)

        pathname = parsed.path.lstrip("/")

        if not pathname:
            raise SuspiciousOperation(
                "URL do Blob inválida."
            )

        return pathname

    def _save(self, name, content):
        name = self._gerar_nome_unico(name)

        if hasattr(content, "seek"):
            content.seek(0)

        conteudo = content.read()

        if not conteudo:
            raise ValueError(
                "O ficheiro enviado está vazio."
            )

        content_type = getattr(
            content,
            "content_type",
            None,
        )

        if not content_type:
            content_type = (
                "application/octet-stream"
            )

        try:
            resultado = self.client.put(
                name,
                conteudo,
                access="public",
                content_type=content_type,
                add_random_suffix=False,
            )
        except Exception as erro:
            raise RuntimeError(
                "Não foi possível enviar o ficheiro "
                f"para o Vercel Blob: {erro}"
            ) from erro

        url = getattr(
            resultado,
            "url",
            None,
        )

        if not url and isinstance(resultado, dict):
            url = resultado.get("url")

        if not url:
            raise RuntimeError(
                "O Vercel Blob não devolveu a URL "
                "do ficheiro enviado."
            )

        return url

    def url(self, name):
        if not name:
            return ""

        name = str(name)

        if name.startswith("http://"):
            return name

        if name.startswith("https://"):
            return name

        raise RuntimeError(
            "O ficheiro armazenado no Vercel Blob "
            "não possui uma URL válida."
        )

    def exists(self, name):
        if not name:
            return False

        try:
            pathname = self._pathname_from_url(name)

            resultado = self.client.head(
                pathname
            )

            return resultado is not None

        except Exception:
            return False

    def delete(self, name):
        if not name:
            return

        try:
            pathname = self._pathname_from_url(name)

            self.client.delete(
                pathname
            )

        except Exception:
            return

    def size(self, name):
        if not name:
            raise FileNotFoundError(
                "Nome do ficheiro não informado."
            )

        try:
            pathname = self._pathname_from_url(name)

            resultado = self.client.head(
                pathname
            )

        except Exception as erro:
            raise RuntimeError(
                "Não foi possível consultar o "
                "Vercel Blob."
            ) from erro

        if resultado is None:
            raise FileNotFoundError(
                "Ficheiro não encontrado no "
                "Vercel Blob."
            )

        tamanho = getattr(
            resultado,
            "size",
            None,
        )

        if tamanho is None and isinstance(
            resultado,
            dict,
        ):
            tamanho = resultado.get("size")

        if tamanho is None:
            raise NotImplementedError(
                "O Vercel Blob não forneceu o "
                "tamanho do ficheiro."
            )

        return int(tamanho)

    def _open(self, name, mode="rb"):
        raise NotImplementedError(
            "A abertura direta de ficheiros pelo "
            "storage não está implementada."
        )
