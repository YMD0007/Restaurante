# Contexto del Proyecto - Restaurante Sabores Leales

## 1) Resumen funcional
- Proyecto web en Django para restaurante con sistema de fidelizacion por puntos.
- Usuarios clientes pueden registrarse, iniciar sesion, ver menu, simular pedidos y acumular puntos.
- Admin/superusuario puede ver panel de clientes, resetear puntos y crear categorias.
- El menu se puede descargar en PDF, ahora incluyendo imagenes de los productos.

## 2) Stack tecnico
- Backend: Django
- Base de datos: SQLite (`db.sqlite3`)
- Frontend: Templates Django + Bootstrap + CSS custom
- PDF: `xhtml2pdf`

## 3) Estructura principal
- `core/`: configuracion global de Django (settings, urls)
- `gestion/`: app principal (modelos, vistas, admin, urls)
- `templates/gestion/`: vistas de menu, base, panel admin, pdf
- `templates/registration/`: login y registro
- `media/`: almacenamiento de imagenes subidas (productos/beneficios)

## 4) Modelos clave (`gestion/models.py`)
- `Categoria`: categorias de comida
- `Producto`: plato/producto con precio, imagen y puntos otorgados
- `PerfilCliente`: perfil extendido del usuario con telefono y puntos
- `Beneficio`: recompensas canjeables por puntos
- `Canje`: historial de canjes
- `Pedido`: pedido con tipo, total y estado completado

Nota: En `Pedido.save()` hay logica que suma puntos al completar pedido (1 punto por cada 1000 del total).

## 5) Vistas y rutas principales
- Home/Menu: `gestion.views.index` -> `/`
- Descargar PDF: `gestion.views.descargar_menu_pdf` -> `/descargar-menu/`
- Registro: `gestion.views.registro` -> `/registro/`
- Login/Logout Django auth: `/accounts/`
- Simular pedido: `gestion.views.realizar_pedido_simulado` -> `/pedir/<producto_id>/`
- Panel admin personalizado: `gestion.views.panel_admin_puntos` -> `/panel-control/`

## 6) Cambios importantes realizados recientemente
- Se instalo dependencia faltante `xhtml2pdf` y `manage.py check` quedo en verde.
- Se mejoro la interfaz visual en:
  - `templates/gestion/base.html`
  - `templates/gestion/index.html`
  - `templates/registration/login.html`
  - `templates/registration/registro.html`
  - `templates/gestion/admin_puntos.html`
- Precios sin decimales en:
  - `templates/gestion/index.html`
  - `templates/gestion/menu_pdf.html`
- Se quito el icono de pestana (favicon vacio) en `templates/gestion/base.html`.
- Badge de puntos en navbar corregido para que el texto sea visible.
- Se agrego context processor global para exponer `puntos_usuario` en todas las plantillas:
  - `gestion/context_processors.py`
  - registro en `core/settings.py`
- En panel admin personalizado se agrego:
  - Reset de puntos por cliente
  - Creacion de categorias de comida
- PDF del menu ahora incluye imagen por producto (con placeholder si no hay imagen).

## 7) Admin
- Django admin clasico: `/admin/`
- `Categoria` ya esta registrada en `gestion/admin.py`.
- `PerfilClienteAdmin` incluye accion masiva para resetear puntos.

## 8) Configuracion relevante
- `LOGIN_REDIRECT_URL = 'index'`
- `LOGOUT_REDIRECT_URL = 'index'`
- `MEDIA_URL = '/media/'`, `MEDIA_ROOT = BASE_DIR / 'media'`
- En `core/urls.py` se sirven media files en DEBUG.

## 9) Seguridad y deuda tecnica (prioridad alta)
- Hay credenciales SMTP hardcodeadas en `core/settings.py` (`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`).
- Recomendado mover credenciales a variables de entorno (`.env`) cuanto antes.

## 10) Dependencias
- No existe aun `requirements.txt` en la raiz.
- Recomendado crear `requirements.txt` para reproducibilidad del entorno.

## 11) Comandos utiles
- Verificar proyecto: `python manage.py check`
- Ejecutar servidor: `python manage.py runserver`
- Migraciones:
  - `python manage.py makemigrations`
  - `python manage.py migrate`

## 12) Estado actual
- Proyecto funcional en desarrollo local.
- UI actualizada, puntos visibles en navbar y herramientas admin ampliadas.
- Exportacion PDF activa con imagenes.
