from .models import PerfilCliente


def puntos_usuario(request):
    if not request.user.is_authenticated:
        return {"puntos_usuario": 0}

    perfil, _ = PerfilCliente.objects.get_or_create(user=request.user)
    return {"puntos_usuario": perfil.puntos}
