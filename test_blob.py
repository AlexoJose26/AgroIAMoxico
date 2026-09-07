import os

from dotenv import load_dotenv
from vercel.blob import BlobClient

load_dotenv(".env.local")

token = os.environ.get("BLOB_READ_WRITE_TOKEN")

if not token:
    raise RuntimeError("BLOB_READ_WRITE_TOKEN não encontrado.")

print("Token encontrado com sucesso.")

client = BlobClient(token=token)

resultado = client.put(
    "testes/agroia-sdk-oficial.txt",
    b"Teste do SDK oficial da Vercel Blob - AgroIA Moxico.",
    access="public",
)

print("UPLOAD REALIZADO COM SUCESSO!")
print("URL:", resultado.url)
print("PATHNAME:", resultado.pathname)
