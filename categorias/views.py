from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from .models import Categoria

@login_required
def lista_categorias(request):
    categorias = Categoria.objects.annotate(
        produtos_count=Count('produtos', distinct=True),
        produtos_ativos_count=Count(
            'produtos',
            filter=Q(produtos__ativo=True),
            distinct=True
        )
    ).order_by('nome')

    total_categorias = Categoria.objects.count()
    categorias_ativas = Categoria.objects.filter(ativo=True).count()
    categorias_inativas = Categoria.objects.filter(ativo=False).count()

    total_produtos_classificados = categorias.aggregate(
        total=Count('produtos', distinct=True)
    )['total'] or 0

    contexto = {
        'categorias': categorias,
        'total_categorias': total_categorias,
        'categorias_ativas': categorias_ativas,
        'categorias_inativas': categorias_inativas,
        'total_produtos_classificados': total_produtos_classificados,
    }

    return render(
        request,
        'categorias/lista_categorias.html',
        contexto
    )

@login_required
def detalhe_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    produtos = categoria.produtos.all().order_by('nome')

    contexto = {
        'categoria': categoria,
        'produtos': produtos,
        'total_produtos': categoria.total_produtos,
        'total_produtos_ativos': categoria.total_produtos_ativos,
        'total_produtos_inativos': categoria.total_produtos_inativos,
    }

    return render(
        request,
        'categorias/detalhe_categoria.html',
        contexto
    )
