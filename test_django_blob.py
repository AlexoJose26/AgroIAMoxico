import os

import django
from django.core.files.base import ContentFile


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

django.setup()


from config.vercel_blob_storage import VercelBlobStorage


print("==============================================")
print(" TESTE DJANGO + VERCEL BLOB")
print("==============================================")

print()
print("A iniciar storage...")

storage = VercelBlobStorage()

print("Storage inicializado com sucesso.")

arquivo = ContentFile(
    b"Teste do Django com Vercel Blob - AgroIA Moxico.",
    name="teste-django.txt",
)

print()
print("A enviar ficheiro para o Vercel Blob...")

nome = storage.save(
    "testes/django/teste-django.txt",
    arquivo,
)

url = storage.url(nome)

print()
print("==============================================")
print(" UPLOAD REALIZADO COM SUCESSO!")
print("==============================================")
print()
print("Nome:")
print(nome)

print()
print("URL:")
print(url)

print()
print("==============================================")
print(" TESTE CONCLUÍDO")
print("==============================================")