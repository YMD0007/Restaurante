from django.contrib import admin
from django.contrib import messages
from .models import Categoria, Producto, PerfilCliente, Beneficio, Canje, Pedido

# --- CONFIGURACIÓN DE PRODUCTOS ---

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'categoria', 'puntos_otorgados')
    list_filter = ('categoria',)
    search_fields = ('nombre',)
    list_editable = ('precio', 'puntos_otorgados') # Permite editar precios rápido

admin.site.register(Categoria)

# --- CONFIGURACIÓN DE CLIENTES ---

@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ('user', 'telefono', 'puntos')
    search_fields = ('user__username', 'telefono')
    readonly_fields = ('puntos',) # Para que el admin no "invente" puntos manualmente
    actions = ('resetear_puntos',)

    @admin.action(description='Resetear puntos de clientes seleccionados')
    def resetear_puntos(self, request, queryset):
        actualizados = queryset.update(puntos=0)
        self.message_user(
            request,
            f"Se resetearon los puntos de {actualizados} cliente(s).",
            level=messages.SUCCESS,
        )

# --- CONFIGURACIÓN DE FIDELIZACIÓN ---

@admin.register(Beneficio)
class BeneficioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'puntos_requeridos', 'activo')
    list_editable = ('activo',)

@admin.register(Canje)
class CanjeAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'beneficio', 'fecha_canje', 'entregado')
    list_filter = ('entregado', 'fecha_canje')
    list_editable = ('entregado',)

# --- CONFIGURACIÓN DE PEDIDOS ---

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'total', 'completado', 'tipo', 'fecha')
    list_filter = ('completado', 'tipo', 'fecha')
    list_editable = ('completado',) 
    # Ordenar por los más recientes primero
    ordering = ('-fecha',)
