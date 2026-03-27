from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('descargar-menu/', views.descargar_menu_pdf, name='descargar_menu_pdf'),
    path('registro/', views.registro, name='registro'),
# Debe tener el <int:producto_id> para saber QUÉ plato estás comprando
    path('pedir/<int:producto_id>/', views.realizar_pedido_simulado, name='realizar_pedido'),    
    # Esta línea es la clave para el login y logout
    path('accounts/', include('django.contrib.auth.urls')), 
    path('panel-control/', views.panel_admin_puntos, name='panel_admin'),
]