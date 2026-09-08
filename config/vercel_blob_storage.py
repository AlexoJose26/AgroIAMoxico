import os
import uuid
from pathlib import Path
from urllib.parse import quote

import requests
from django.core.exceptions import SuspiciousOperation
from django.core.files.storage import Storage


class VercelBlobStorage(Storage):
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

        self.public_url = self.public_url.rstrip("/")

        self.api_url = "https://blob.vercel-storage.com"

        self.timeout = int(
            os.environ.get(
                "BLOB_REQUEST_TIMEOUT",
                "60",
            )
        )

    def _normalizar_nome(self, name):
        name = str(name).replace("\\", "/").lstrip("/")

        partes = Path(name).parts

        if ".." in partes:
            raise SuspiciousOperation(
                "Nome de ficheiro inválido."
            )

        return name

    def _gerar_nome_unico(self, name):
        name = self._normalizar_nome(name)

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

    def _blob_url(self, name):
        name = self._normalizar_nome(name)

        caminho = quote(
            name,
            safe="/",
        )

        return f"{self.api_url}/{caminho}"

    def _headers(self):
        return {
            "Authorization": (
                f"Bearer {self.token}"
            ),
        }

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

        headers = self._headers()

        headers["Content-Type"] = content_type

        headers["x-vercel-blob-access"] = "public"

        headers["x-vercel-blob-add-random-suffix"] = (
            "false"
        )

        try:
            response = requests.put(
                self._blob_url(name),
                data=conteudo,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as erro:
            raise RuntimeError(
                "Não foi possível comunicar com "
                f"o Vercel Blob: {erro}"
            ) from erro

        if not response.ok:
            try:
                detalhe = response.json()
            except ValueError:
                detalhe = response.text

            raise RuntimeError(
                "Erro ao enviar ficheiro para "
                f"o Vercel Blob: {detalhe}"
            )

        try:
            resultado = response.json()
        except ValueError as erro:
            raise RuntimeError(
                "O Vercel Blob devolveu uma resposta "
                "inválida após o upload."
            ) from erro

        pathname = resultado.get(
            "pathname",
            name,
        )

        return pathname

    def url(self, name):
        if not name:
            return ""

        name = self._normalizar_nome(name)

        if name.startswith("http://"):
            return name

        if name.startswith("https://"):
            return name

        return (
            f"{self.public_url}/"
            f"{name.lstrip('/')}"
        )

    def exists(self, name):
        if not name:
            return False

        name = self._normalizar_nome(name)

        try:
            response = requests.head(
                self._blob_url(name),
                headers=self._headers(),
                timeout=self.timeout,
            )

            return response.ok

        except requests.RequestException:
            return False

    def delete(self, name):
        if not name:
            return

        name = self._normalizar_nome(name)

        try:
            response = requests.delete(
                self._blob_url(name),
                headers=self._headers(),
                timeout=self.timeout,
            )

            if response.status_code in {
                200,
                204,
                404,
            }:
                return

        except requests.RequestException:
            return

    def size(self, name):
        if not name:
            raise FileNotFoundError(
                "Nome do ficheiro não informado."
            )

        name = self._normalizar_nome(name)

        try:
            response = requests.head(
                self._blob_url(name),
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as erro:
            raise RuntimeError(
                "Não foi possível consultar o "
                "Vercel Blob."
            ) from erro

        if response.status_code == 404:
            raise FileNotFoundError(
                "Ficheiro não encontrado no "
                "Vercel Blob."
            )

        if not response.ok:
            raise RuntimeError(
                "Não foi possível obter o tamanho "
                "do ficheiro."
            )

        content_length = response.headers.get(
            "Content-Length"
        )

        if content_length is None:
            raise NotImplementedError(
                "O Vercel Blob não forneceu "
                "Content-Length."
            )

        return int(content_length)

    def _open(self, name, mode="rb"):
        raise NotImplementedError(
            "A abertura direta de ficheiros pelo "
            "storage não está implementada."
        )
