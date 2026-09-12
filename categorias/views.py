from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from .models import Categoria


@login_required
def categorias(request):
    categorias_qs = (
        Categoria.objects
        .annotate(
            produtos_count=Count(
                "produtos",
                distinct=True
            ),
            produtos_ativos_count=Count(
                "produtos",
                filter=Q(produtos__ativo=True),
                distinct=True
            ),
        )
        .order_by("nome")
    )

    total_categorias = categorias_qs.count()

    categorias_ativas = categorias_qs.filter(
        ativo=True
    ).count()

    total_produtos_classificados = (
        categorias_qs
        .aggregate(
            total=Count(
                "produtos",
                distinct=True
            )
        )
        .get("total", 0)
    )

    contexto = {
        "categorias": categorias_qs,
        "total_categorias": total_categorias,
        "categorias_ativas": categorias_ativas,
        "total_produtos_classificados": total_produtos_classificados,
    }

    return render(
        request,
        "categorias/categorias.html",
        contexto
    )
