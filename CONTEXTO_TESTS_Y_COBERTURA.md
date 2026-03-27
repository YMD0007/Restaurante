# Contexto de Pruebas y Cobertura

## Objetivo aplicado
- Elevar la cobertura automatizada del proyecto por encima del 90%.
- Implementar pruebas obligatorias con `Django TestCase` y `Client`.
- Validar login, navegacion, envio de formularios, pedidos y restricciones de acceso.
- Reducir riesgos funcionales y de seguridad que afectaban la estabilidad de las pruebas.

## Cambios aplicados

### 1. Correccion funcional en vistas
Archivo: `gestion/views.py`

- Se ajusto la vista `index` para manejar de forma segura el parametro `categoria`.
- Antes, un valor invalido como `?categoria=abc` podia provocar error por conversion con `int()`.
- Ahora:
  - si `categoria` es numerica, se filtran productos normalmente;
  - si `categoria` es invalida, la vista responde con lista vacia;
  - si no se envia `categoria`, se muestran todos los productos.

### 2. Endurecimiento basico de configuracion sensible
Archivo: `core/settings.py`

- Se reemplazaron valores sensibles hardcodeados por variables de entorno:
  - `DJANGO_SECRET_KEY`
  - `DJANGO_DEBUG`
  - `DJANGO_ALLOWED_HOSTS`
  - `EMAIL_BACKEND`
  - `EMAIL_HOST`
  - `EMAIL_PORT`
  - `EMAIL_USE_TLS`
  - `EMAIL_HOST_USER`
  - `EMAIL_HOST_PASSWORD`
  - `DEFAULT_FROM_EMAIL`
- Se dejaron valores por defecto orientados a desarrollo local para no romper el proyecto.

### 3. Implementacion de suite de pruebas automatizadas
Archivo: `gestion/tests.py`

- Se construyo una bateria completa de pruebas con `TestCase` y `Client`.
- Se agregaron fixtures base para:
  - categorias
  - productos
  - usuario cliente
  - superusuario
  - perfiles con puntos

## Cobertura funcional implementada

### Navegacion y vistas
- Carga del inicio (`index`) para usuario anonimo.
- Carga del inicio para usuario autenticado.
- Filtro por categoria valida.
- Manejo de categoria invalida sin error de servidor.
- Creacion automatica de perfil cuando un usuario autenticado no lo tiene.

### Registro e inicio de sesion
- Render del formulario de registro.
- Registro valido con creacion de usuario y perfil.
- Inicio de sesion automatico tras registro.
- Registro invalido con errores visibles.
- Login exitoso con `Client.login()` y con POST al login.
- Login fallido mostrando mensaje de error.

### Restricciones de acceso y puertas traseras
- Bloqueo de acceso al panel administrativo para anonimos.
- Bloqueo de acceso al panel administrativo para usuarios no superusuarios.
- Restriccion de compras simuladas a usuarios autenticados.
- Validacion de que la compra debe confirmarse por `POST` y no por `GET`.

### Panel administrativo personalizado
- Acceso correcto de superusuario al panel.
- Reseteo individual de puntos.
- Validacion de `perfil_id` invalido con respuesta 404.
- Creacion de categoria nueva.
- Validacion de categoria vacia.
- Validacion de categoria duplicada.

### Pedidos simulados
- Compra con dinero.
- Compra con puntos suficientes.
- Rechazo de compra con puntos insuficientes.
- Uso del metodo por defecto cuando no se envia `metodo_pago`.
- Manejo de producto inexistente con 404.
- Tolerancia a errores de correo tanto en compra con dinero como en canje por puntos.

### PDF y utilidades
- Descarga correcta del menu en PDF.
- Simulacion de error de generacion PDF con `mock`.
- Cobertura de `link_callback` para:
  - archivo media existente
  - archivo faltante
  - archivo static existente
  - URL externa

### Modelos y logica de negocio
- Cobertura de metodos `__str__` de los modelos principales.
- Prueba de `Pedido.save()` para verificar que:
  - no suma puntos al crear pedido incompleto;
  - suma puntos al pasar de incompleto a completado;
  - no duplica puntos al guardar otra vez el pedido ya completado.
- Prueba de `calcular_puntos_canje` para reglas personalizadas y fallback por precio.

### Admin y context processor
- Cobertura de la accion `resetear_puntos` en `gestion/admin.py`.
- Cobertura de `puntos_usuario` en `gestion/context_processors.py` para anonimo y autenticado.

### URLs globales
- Cobertura del bloque de `core/urls.py` que sirve archivos media cuando `DEBUG=True`.

## Herramientas de prueba utilizadas
- `django.test.TestCase`
- `django.test.Client`
- `RequestFactory`
- `unittest.mock.patch`
- `override_settings`
- `coverage.py`

## Comandos ejecutados
```bash
python manage.py test
coverage run manage.py test
coverage report -m
```

## Resultado final de cobertura
- Cobertura total alcanzada: `99%`

Detalle final relevante:
- `gestion/views.py`: 100%
- `gestion/models.py`: 100%
- `gestion/admin.py`: 100%
- `gestion/context_processors.py`: 100%
- `gestion/forms.py`: 100%
- `core/urls.py`: 100%

## Observacion final
- `manage.py` quedo en 82% porque no se fuerza artificialmente la rama del `ImportError` de Django; aun asi, la cobertura global del proyecto supera ampliamente el objetivo solicitado.
