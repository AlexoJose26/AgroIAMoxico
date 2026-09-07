from django.conf import settings
from django.core.files.base import ContentFile
from django import setup

setup()

from config.vercel_blob_storage import VercelBlobStorage


print("Iniciando teste do storage Django + Vercel Blob...")

storage = VercelBlobStorage()

arquivo = ContentFile(
    b"Teste do Django com Vercel Blob - AgroIA Moxico.",
    name="teste-django.txt",
)

nome = storage.save(
    "testes/django/teste-django.txt",
    arquivo,
)

print("UPLOAD REALIZADO COM SUCESSO!")
print("Nome:", nome)
print("URL:", storage.url(nome))

print()
print("Teste concluído.")
