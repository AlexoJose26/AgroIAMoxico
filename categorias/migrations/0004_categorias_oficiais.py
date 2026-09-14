from django.db import migrations

CATEGORIAS_OFICIAIS = [
    ("Cereal", "Culturas produtoras de grãos, como milho, arroz, trigo e sorgo, utilizadas principalmente na alimentação humana e animal."),
    ("Frutas", "Culturas que produzem frutos destinados ao consumo fresco, processamento ou comercialização, como banana, manga, citrinos e outras frutas."),
    ("Raízes e Tubérculos", "Culturas desenvolvidas principalmente pelas suas raízes ou tubérculos, como mandioca, batata, batata-doce e inhame."),
    ("Leguminosas", "Culturas utilizadas principalmente como fonte de proteínas e nutrientes, como feijão, ervilha, lentilha e outras leguminosas."),
    ("Oleaginosas", "Culturas utilizadas principalmente para a produção de óleos vegetais e outros derivados, como soja, girassol e outras sementes oleaginosas."),
    ("Hortícolas", "Culturas hortícolas destinadas principalmente à alimentação, incluindo hortaliças, folhas, legumes e outras plantas cultivadas em hortas."),
    ("Culturas Industriais", "Culturas produzidas principalmente como matéria-prima para transformação industrial, como algodão, cana-de-açúcar e outras culturas comerciais."),
    ("Especiarias", "Culturas utilizadas principalmente para aromatizar, temperar ou conservar alimentos, incluindo pimentas, ervas e outras plantas condimentares."),
]

def criar_categorias_oficiais(apps, schema_editor):
    Categoria = apps.get_model("categorias", "Categoria")

    nomes_oficiais = [nome for nome, descricao in CATEGORIAS_OFICIAIS]

    Categoria.objects.exclude(nome__in=nomes_oficiais).delete()

    for nome, descricao in CATEGORIAS_OFICIAIS:
        Categoria.objects.update_or_create(
            nome=nome,
            defaults={
                "descricao": descricao,
                "ativo": True,
            },
        )


def remover_categorias_oficiais(apps, schema_editor):
    Categoria = apps.get_model("categorias", "Categoria")

    nomes_oficiais = [nome for nome, descricao in CATEGORIAS_OFICIAIS]

    Categoria.objects.filter(nome__in=nomes_oficiais).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("categorias", "0002_categoria_categoria_nome_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(
            criar_categorias_oficiais,
            remover_categorias_oficiais,
        ),
    ]
