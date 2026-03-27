from django.db import models
from django.contrib.auth.models import User

# --- 1. CATÁLOGO DEL RESTAURANTE ---

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nombre

class Producto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)
    puntos_otorgados = models.IntegerField(default=10) # Puntos que gana el cliente al comprarlo

    def __str__(self):
        return self.nombre


# --- 2. CLIENTES Y FIDELIZACIÓN ---

class PerfilCliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    puntos = models.PositiveIntegerField(default=0)
    telefono = models.CharField(max_length=15)

    def __str__(self):
        return self.user.username

class Beneficio(models.Model):
    """Estrategias de fidelización: Premios que el dueño ofrece"""
    titulo = models.CharField(max_length=100)
    descripcion = models.TextField()
    puntos_requeridos = models.PositiveIntegerField()
    foto_referencia = models.ImageField(upload_to='beneficios/', null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.titulo} ({self.puntos_requeridos} pts)"

class Canje(models.Model):
    """Registro de uso de puntos por parte del cliente"""
    cliente = models.ForeignKey(PerfilCliente, on_delete=models.CASCADE)
    beneficio = models.ForeignKey(Beneficio, on_delete=models.CASCADE)
    fecha_canje = models.DateTimeField(auto_now_add=True)
    entregado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.cliente.user.username} canjeó {self.beneficio.titulo}"


# --- 3. PEDIDOS (EL MOTOR ECONÓMICO) ---

class Pedido(models.Model):
    TIPO_CHOICES = [('sitio', 'En el sitio'), ('domicilio', 'A domicilio')]
    
    cliente = models.ForeignKey(PerfilCliente, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(choices=TIPO_CHOICES, max_length=10, default='sitio')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    completado = models.BooleanField(default=False)

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente.user.username}"

    def save(self, *args, **kwargs):
        """Lógica automática: Al marcar como completado, suma puntos al cliente"""
        if self.pk: # Si el pedido ya existe
            pedido_antiguo = Pedido.objects.get(pk=self.pk)
            # Si cambia de NO completado a SÍ completado
            if not pedido_antiguo.completado and self.completado:
                # Regla: 1 punto por cada $1000 de compra
                puntos_a_sumar = int(self.total / 1000)
                self.cliente.puntos += puntos_a_sumar
                self.cliente.save()
        
        super(Pedido, self).save(*args, **kwargs)