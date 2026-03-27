import os
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.contrib.auth.forms import UserCreationForm
from django import forms
from xhtml2pdf import pisa
from .models import Producto, Categoria, PerfilCliente, Pedido


PUNTOS_CANJE_PERSONALIZADOS = {
    'pizza': 100,
    'pasta': 50,
    'tacos': 20,
    'burritos': 25,
}


def calcular_puntos_canje(producto):
    nombre_producto = (producto.nombre or '').strip().lower()
    return PUNTOS_CANJE_PERSONALIZADOS.get(nombre_producto, max(1, int(producto.precio / 1000)))

# --- FORMULARIO PERSONALIZADO DE REGISTRO ---
class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True)
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email',)

# --- UTILIDAD PARA IMÁGENES EN PDF ---
def link_callback(uri, rel):
    sUrl = settings.STATIC_URL
    sRoot = settings.STATIC_ROOT
    mUrl = settings.MEDIA_URL
    mRoot = settings.MEDIA_ROOT
    if uri.startswith(mUrl):
        path = os.path.join(mRoot, uri.replace(mUrl, ""))
    elif uri.startswith(sUrl):
        path = os.path.join(sRoot, uri.replace(sUrl, ""))
    else:
        return uri
    if not os.path.isfile(path):
        return uri
    return path

# --- VISTA PRINCIPAL (CARTA) ---
def index(request):
    categoria_id = request.GET.get('categoria')
    categorias = Categoria.objects.all()

    categoria_seleccionada = None
    if categoria_id and categoria_id.isdigit():
        categoria_seleccionada = int(categoria_id)
        productos = Producto.objects.filter(categoria_id=categoria_seleccionada)
    elif categoria_id:
        productos = Producto.objects.none()
    else:
        productos = Producto.objects.all()

    puntos_usuario = 0
    if request.user.is_authenticated:
        perfil, created = PerfilCliente.objects.get_or_create(user=request.user)
        puntos_usuario = perfil.puntos

    for producto in productos:
        producto.puntos_canje = calcular_puntos_canje(producto)
        producto.puntos_faltantes = max(0, producto.puntos_canje - puntos_usuario)

    context = {
        'productos': productos,
        'categorias': categorias,
        'categoria_seleccionada': categoria_seleccionada,
        'puntos_usuario': puntos_usuario,
    }
    return render(request, 'gestion/index.html', context)

# --- PANEL DE ADMINISTRADOR PERSONALIZADO ---
@user_passes_test(lambda u: u.is_superuser)
def panel_admin_puntos(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'reset_puntos':
            perfil_id = request.POST.get('perfil_id')
            perfil = get_object_or_404(PerfilCliente, id=perfil_id)
            perfil.puntos = 0
            perfil.save(update_fields=['puntos'])
            messages.success(request, f"Puntos reiniciados para {perfil.user.username}.")

        elif action == 'crear_categoria':
            nombre_categoria = request.POST.get('nombre_categoria', '').strip()

            if not nombre_categoria:
                messages.error(request, 'Debes escribir un nombre para la categoria.')
            elif Categoria.objects.filter(nombre__iexact=nombre_categoria).exists():
                messages.warning(request, 'Esa categoria ya existe.')
            else:
                Categoria.objects.create(nombre=nombre_categoria)
                messages.success(request, f"Categoria '{nombre_categoria}' creada correctamente.")

        return redirect('panel_admin')

    # Obtenemos todos los perfiles ordenados por los que tienen más puntos
    clientes = PerfilCliente.objects.all().order_by('-puntos')
    categorias = Categoria.objects.all().order_by('nombre')
    return render(request, 'gestion/admin_puntos.html', {'clientes': clientes, 'categorias': categorias})

# --- GENERACIÓN DE PDF ---
def descargar_menu_pdf(request):
    productos = Producto.objects.all()
    template_path = 'gestion/menu_pdf.html'
    context = {'productos': productos}
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="menu_restaurante.pdf"'
    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response, link_callback=link_callback)
    if pisa_status.err:
        return HttpResponse('Error al generar PDF')
    return response

# --- SISTEMA DE REGISTRO CON NOTIFICACIÓN ---
def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            PerfilCliente.objects.create(user=user)
            
            try:
                send_mail(
                    'Bienvenido a Sabores Leales - Tu cuenta ya esta activa',
                    (
                        f'Hola {user.username},\n\n'
                        'Gracias por registrarte en Sabores Leales. Tu cuenta ya esta activa y lista para usar.\n\n'
                        'Desde ahora podras:\n'
                        '- Explorar nuestro menu\n'
                        '- Realizar pedidos\n'
                        '- Acumular y canjear puntos por beneficios\n\n'
                        'Nos alegra tenerte con nosotros.\n'
                        'Equipo Sabores Leales'
                    ),
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=True,
                )
            except:
                pass
                
            login(request, user)
            return redirect('index')
    else:
        form = RegistroForm()
    return render(request, 'registration/registro.html', {'form': form})

# --- SIMULACIÓN DE COMPRA BLINDADA ---
@login_required
def realizar_pedido_simulado(request, producto_id):
    if request.method != 'POST':
        messages.warning(request, 'Para confirmar la compra debes usar el boton Pedir ahora.')
        return redirect('index')

    producto = get_object_or_404(Producto, id=producto_id)
    perfil, created = PerfilCliente.objects.get_or_create(user=request.user)
    metodo_pago = request.POST.get('metodo_pago', 'dinero')
    puntos_canje = calcular_puntos_canje(producto)

    if metodo_pago == 'puntos':
        if perfil.puntos < puntos_canje:
            messages.error(
                request,
                f"No tienes puntos suficientes para canjear {producto.nombre}. Necesitas {puntos_canje} pts.",
            )
            return redirect('index')

        Pedido.objects.create(
            cliente=perfil,
            total=0,
            tipo='sitio',
            completado=True,
        )

        perfil.puntos -= puntos_canje
        perfil.save(update_fields=['puntos'])

        try:
            send_mail(
                'Canje realizado con puntos - Pedido confirmado',
                (
                    f'Hola {request.user.username},\n\n'
                    'Tu pedido fue canjeado correctamente con puntos.\n\n'
                    f'Detalle del canje:\n'
                    f'- Producto: {producto.nombre}\n'
                    f'- Costo en puntos: {puntos_canje} pts\n'
                    f'- Saldo restante: {perfil.puntos} pts\n\n'
                    'Gracias por seguir disfrutando Sabores Leales.'
                ),
                settings.EMAIL_HOST_USER,
                [request.user.email],
                fail_silently=True,
            )
        except:
            pass

        messages.success(request, f"Canje exitoso: {producto.nombre}. Tu pedido se esta preparando.")
        return redirect('index')

    Pedido.objects.create(
        cliente=perfil,
        total=producto.precio,
        tipo='sitio',
        completado=True,
    )

    perfil.puntos += producto.puntos_otorgados
    perfil.save(update_fields=['puntos'])
    
    try:
        send_mail(
            'Pedido confirmado - Puntos acreditados en tu cuenta',
            (
                f'Hola {request.user.username},\n\n'
                'Tu pedido fue recibido correctamente y ya se encuentra en preparacion.\n\n'
                f'Detalle del pedido:\n'
                f'- Producto: {producto.nombre}\n'
                f'- Valor: ${producto.precio:.0f}\n'
                f'- Puntos ganados: {producto.puntos_otorgados} pts\n'
                f'- Saldo actual: {perfil.puntos} pts\n\n'
                'Gracias por elegir Sabores Leales.\n'
                'Te esperamos de nuevo muy pronto.'
            ),
            settings.EMAIL_HOST_USER,
            [request.user.email],
            fail_silently=True,
        )
    except:
        pass

    messages.success(request, f"Tu pedido de {producto.nombre} se esta preparando.")
         
    return redirect('index')
