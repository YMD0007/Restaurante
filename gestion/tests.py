import importlib
import os
import tempfile
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from core import urls as core_urls
from gestion import forms as forms_module
from gestion.admin import PerfilClienteAdmin
from gestion.context_processors import puntos_usuario
from gestion.models import Beneficio, Canje, Categoria, Pedido, PerfilCliente, Producto
from gestion.views import RegistroForm, calcular_puntos_canje, link_callback


class BaseGestionTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.categoria = Categoria.objects.create(nombre='Pizzas')
        self.otra_categoria = Categoria.objects.create(nombre='Bebidas')
        self.producto = Producto.objects.create(
            categoria=self.categoria,
            nombre='Pizza',
            descripcion='Pizza artesanal',
            precio=Decimal('25000.00'),
            puntos_otorgados=30,
        )
        self.otro_producto = Producto.objects.create(
            categoria=self.otra_categoria,
            nombre='Jugo',
            descripcion='Jugo natural',
            precio=Decimal('8000.00'),
            puntos_otorgados=8,
        )
        self.user = User.objects.create_user(
            username='cliente',
            email='cliente@example.com',
            password='ClaveSegura123',
        )
        self.perfil = PerfilCliente.objects.create(user=self.user, telefono='3001234567', puntos=40)
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='AdminClave123',
        )
        self.admin_perfil = PerfilCliente.objects.create(user=self.admin_user, telefono='3007654321', puntos=120)


class IndexViewTests(BaseGestionTestCase):
    def test_index_muestra_productos_para_anonimo(self):
        response = self.client.get(reverse('index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pizza')
        self.assertContains(response, 'Jugo')
        self.assertEqual(response.context['puntos_usuario'], 0)
        self.assertIsNone(response.context['categoria_seleccionada'])

    def test_index_filtra_por_categoria_valida(self):
        response = self.client.get(reverse('index'), {'categoria': self.categoria.id})

        self.assertEqual(response.status_code, 200)
        productos = list(response.context['productos'])
        self.assertEqual(productos, [self.producto])
        self.assertEqual(response.context['categoria_seleccionada'], self.categoria.id)

    def test_index_con_categoria_invalida_devuelve_lista_vacia(self):
        response = self.client.get(reverse('index'), {'categoria': 'abc'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['productos']), [])
        self.assertContains(response, 'No encontramos platos en esta categoría.')

    def test_index_crea_perfil_para_usuario_autenticado_si_no_existe(self):
        usuario_sin_perfil = User.objects.create_user(
            username='nuevo',
            email='nuevo@example.com',
            password='ClaveSegura123',
        )
        self.client.login(username='nuevo', password='ClaveSegura123')

        response = self.client.get(reverse('index'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(PerfilCliente.objects.filter(user=usuario_sin_perfil).exists())
        self.assertEqual(response.context['puntos_usuario'], 0)


class RegistroTests(BaseGestionTestCase):
    def test_registro_get_renderiza_formulario(self):
        response = self.client.get(reverse('registro'))

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], RegistroForm)
        self.assertContains(response, 'CREAR MI CUENTA')

    @patch('gestion.views.send_mail')
    def test_registro_post_valido_crea_usuario_perfil_e_inicia_sesion(self, mocked_send_mail):
        response = self.client.post(
            reverse('registro'),
            {
                'username': 'registro_ok',
                'email': 'registro@example.com',
                'password1': 'ClaveSegura12345',
                'password2': 'ClaveSegura12345',
            },
        )

        self.assertRedirects(response, reverse('index'))
        usuario = User.objects.get(username='registro_ok')
        self.assertTrue(PerfilCliente.objects.filter(user=usuario).exists())
        self.assertEqual(int(self.client.session['_auth_user_id']), usuario.id)
        mocked_send_mail.assert_called_once()

    @patch('gestion.views.send_mail', side_effect=Exception('smtp caido'))
    def test_registro_post_valido_tolera_error_de_correo(self, mocked_send_mail):
        response = self.client.post(
            reverse('registro'),
            {
                'username': 'registro_mail_error',
                'email': 'mailerror@example.com',
                'password1': 'ClaveSegura12345',
                'password2': 'ClaveSegura12345',
            },
        )

        self.assertRedirects(response, reverse('index'))
        self.assertTrue(User.objects.filter(username='registro_mail_error').exists())
        mocked_send_mail.assert_called_once()

    def test_registro_post_invalido_muestra_errores(self):
        User.objects.create_user(username='repetido', password='ClaveSegura123')

        response = self.client.post(
            reverse('registro'),
            {
                'username': 'repetido',
                'email': 'duplicado@example.com',
                'password1': 'ClaveSegura12345',
                'password2': 'ClaveSegura12345',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'corrige los errores')


class AutenticacionYAccesoTests(BaseGestionTestCase):
    def test_login_con_client_login_y_post_login(self):
        self.assertTrue(self.client.login(username='cliente', password='ClaveSegura123'))
        self.client.logout()

        response = self.client.post(
            reverse('login'),
            {'username': 'cliente', 'password': 'ClaveSegura123'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('index'))

    def test_login_acepta_correo(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'cliente@example.com', 'password': 'ClaveSegura123'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('index'))

    def test_login_superusuario_redirige_a_panel_admin(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'admin', 'password': 'AdminClave123'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('panel_admin'))

    def test_login_superusuario_acepta_correo(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'admin@example.com', 'password': 'AdminClave123'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('panel_admin'))

    def test_login_invalido_muestra_error(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'cliente', 'password': 'mal'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Usuario o contrasena incorrectos.')

    def test_panel_admin_restringe_puerta_trasera_a_anonimo_y_usuario_normal(self):
        response_anon = self.client.get(reverse('panel_admin'))
        self.assertEqual(response_anon.status_code, 302)
        self.assertIn(reverse('login'), response_anon.url)

        self.client.login(username='cliente', password='ClaveSegura123')
        response_user = self.client.get(reverse('panel_admin'))
        self.assertEqual(response_user.status_code, 302)
        self.assertIn(reverse('login'), response_user.url)

    def test_realizar_pedido_exige_login(self):
        response = self.client.post(reverse('realizar_pedido', args=[self.producto.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)


class PanelAdminTests(BaseGestionTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='admin', password='AdminClave123')

    def test_panel_admin_get_superusuario(self):
        response = self.client.get(reverse('panel_admin'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestion de clientes leales')
        self.assertContains(response, self.user.username)

    def test_panel_admin_resetea_puntos(self):
        response = self.client.post(
            reverse('panel_admin'),
            {'action': 'reset_puntos', 'perfil_id': self.perfil.id},
            follow=True,
        )

        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.puntos, 0)
        self.assertContains(response, 'Puntos reiniciados para cliente.')

    def test_panel_admin_reset_puntos_invalido_devuelve_404(self):
        response = self.client.post(reverse('panel_admin'), {'action': 'reset_puntos', 'perfil_id': 999999})

        self.assertEqual(response.status_code, 404)

    def test_panel_admin_crea_categoria(self):
        response = self.client.post(
            reverse('panel_admin'),
            {'action': 'crear_categoria', 'nombre_categoria': 'Postres'},
            follow=True,
        )

        self.assertTrue(Categoria.objects.filter(nombre='Postres').exists())
        self.assertContains(response, 'Postres')
        self.assertContains(response, 'creada correctamente')

    def test_panel_admin_categoria_vacia(self):
        response = self.client.post(
            reverse('panel_admin'),
            {'action': 'crear_categoria', 'nombre_categoria': '   '},
            follow=True,
        )

        self.assertContains(response, 'Debes escribir un nombre para la categoria.')

    def test_panel_admin_categoria_duplicada(self):
        response = self.client.post(
            reverse('panel_admin'),
            {'action': 'crear_categoria', 'nombre_categoria': 'pizzas'},
            follow=True,
        )

        self.assertContains(response, 'Esa categoria ya existe.')

    def test_panel_admin_crea_producto_sin_foto(self):
        response = self.client.post(
            reverse('panel_admin'),
            {
                'action': 'crear_producto',
                'nombre_producto': 'Lasana mixta',
                'descripcion_producto': 'Pasta gratinada con salsa de la casa.',
                'precio_producto': '32000',
                'puntos_otorgados': '25',
                'categoria_id': str(self.categoria.id),
            },
            follow=True,
        )

        producto = Producto.objects.get(nombre='Lasana mixta')
        self.assertEqual(producto.categoria, self.categoria)
        self.assertFalse(bool(producto.imagen))
        self.assertContains(response, 'creado correctamente')

    def test_panel_admin_crea_producto_con_foto(self):
        imagen = SimpleUploadedFile(
            'combo.jpg',
            b'filecontent',
            content_type='image/jpeg',
        )

        self.client.post(
            reverse('panel_admin'),
            {
                'action': 'crear_producto',
                'nombre_producto': 'Combo familiar',
                'descripcion_producto': 'Incluye pizza, bebida y postre.',
                'precio_producto': '54000',
                'puntos_otorgados': '40',
                'categoria_id': str(self.categoria.id),
                'imagen_producto': imagen,
            },
        )

        producto = Producto.objects.get(nombre='Combo familiar')
        self.assertTrue(bool(producto.imagen))

    def test_panel_admin_producto_exige_categoria(self):
        response = self.client.post(
            reverse('panel_admin'),
            {
                'action': 'crear_producto',
                'nombre_producto': 'Malteada',
                'descripcion_producto': 'Bebida fria',
                'precio_producto': '12000',
                'puntos_otorgados': '12',
                'categoria_id': '',
            },
            follow=True,
        )

        self.assertFalse(Producto.objects.filter(nombre='Malteada').exists())
        self.assertContains(response, 'Completa nombre, descripcion, precio y categoria para guardar el producto.')

    def test_panel_admin_edita_producto(self):
        response = self.client.post(
            reverse('panel_admin'),
            {
                'action': 'editar_producto',
                'producto_id': str(self.producto.id),
                'nombre_producto': 'Pizza premium',
                'descripcion_producto': 'Pizza artesanal con ingredientes extra.',
                'precio_producto': '29000',
                'puntos_otorgados': '45',
                'categoria_id': str(self.otra_categoria.id),
            },
            follow=True,
        )

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, 'Pizza premium')
        self.assertEqual(self.producto.categoria, self.otra_categoria)
        self.assertEqual(str(self.producto.precio), '29000.00')
        self.assertEqual(self.producto.puntos_otorgados, 45)
        self.assertContains(response, 'actualizado correctamente')

    def test_panel_admin_elimina_producto(self):
        response = self.client.post(
            reverse('panel_admin'),
            {
                'action': 'eliminar_producto',
                'producto_id': str(self.otro_producto.id),
            },
            follow=True,
        )

        self.assertFalse(Producto.objects.filter(id=self.otro_producto.id).exists())
        self.assertContains(response, 'eliminado correctamente')


class PedidoSimuladoTests(BaseGestionTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='cliente', password='ClaveSegura123')

    def test_get_no_permite_confirmar_pedido(self):
        response = self.client.get(reverse('realizar_pedido', args=[self.producto.id]), follow=True)

        self.assertRedirects(response, reverse('index'))
        mensajes = [message.message for message in get_messages(response.wsgi_request)]
        self.assertIn('Para confirmar la compra debes usar el boton Pedir ahora.', mensajes)

    @patch('gestion.views.send_mail')
    def test_post_con_dinero_crea_pedido_y_suma_puntos(self, mocked_send_mail):
        response = self.client.post(
            reverse('realizar_pedido', args=[self.producto.id]),
            {'metodo_pago': 'dinero'},
            follow=True,
        )

        self.perfil.refresh_from_db()
        pedido = Pedido.objects.latest('id')
        self.assertEqual(pedido.total, self.producto.precio)
        self.assertTrue(pedido.completado)
        self.assertEqual(self.perfil.puntos, 70)
        self.assertContains(response, 'Tu pedido de Pizza se esta preparando.')
        mocked_send_mail.assert_called_once()

    @patch('gestion.views.send_mail')
    def test_post_sin_metodo_pago_usa_dinero_por_defecto(self, mocked_send_mail):
        response = self.client.post(reverse('realizar_pedido', args=[self.otro_producto.id]), follow=True)

        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.puntos, 48)
        self.assertRedirects(response, reverse('index'))
        mocked_send_mail.assert_called_once()

    @patch('gestion.views.send_mail')
    def test_post_con_puntos_suficientes_descuenta_saldo(self, mocked_send_mail):
        self.perfil.puntos = 150
        self.perfil.save(update_fields=['puntos'])

        response = self.client.post(
            reverse('realizar_pedido', args=[self.producto.id]),
            {'metodo_pago': 'puntos'},
            follow=True,
        )

        self.perfil.refresh_from_db()
        pedido = Pedido.objects.latest('id')
        self.assertEqual(pedido.total, 0)
        self.assertEqual(self.perfil.puntos, 50)
        self.assertContains(response, 'Canje exitoso: Pizza. Tu pedido se esta preparando.')
        mocked_send_mail.assert_called_once()

    @patch('gestion.views.send_mail')
    def test_post_con_puntos_insuficientes_no_crea_pedido(self, mocked_send_mail):
        response = self.client.post(
            reverse('realizar_pedido', args=[self.producto.id]),
            {'metodo_pago': 'puntos'},
            follow=True,
        )

        self.assertEqual(Pedido.objects.count(), 0)
        self.assertContains(response, 'No tienes puntos suficientes para canjear Pizza.')
        mocked_send_mail.assert_not_called()

    @patch('gestion.views.send_mail', side_effect=Exception('smtp caido'))
    def test_post_tolera_error_de_correo(self, mocked_send_mail):
        response = self.client.post(
            reverse('realizar_pedido', args=[self.producto.id]),
            {'metodo_pago': 'dinero'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('index'))
        mocked_send_mail.assert_called_once()

    @patch('gestion.views.send_mail', side_effect=Exception('smtp caido'))
    def test_canje_tolera_error_de_correo(self, mocked_send_mail):
        self.perfil.puntos = 150
        self.perfil.save(update_fields=['puntos'])

        response = self.client.post(
            reverse('realizar_pedido', args=[self.producto.id]),
            {'metodo_pago': 'puntos'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('index'))
        mocked_send_mail.assert_called_once()

    def test_producto_inexistente_devuelve_404(self):
        response = self.client.post(reverse('realizar_pedido', args=[999999]), {'metodo_pago': 'dinero'})

        self.assertEqual(response.status_code, 404)


class PdfViewTests(BaseGestionTestCase):
    def test_descargar_menu_pdf_exitoso(self):
        response = self.client.get(reverse('descargar_menu_pdf'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename="menu_restaurante.pdf"', response['Content-Disposition'])

    @patch('gestion.views.pisa.CreatePDF', return_value=SimpleNamespace(err=True))
    def test_descargar_menu_pdf_maneja_error(self, mocked_create_pdf):
        response = self.client.get(reverse('descargar_menu_pdf'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error al generar PDF')
        mocked_create_pdf.assert_called_once()


class ModelosYHelpersTests(BaseGestionTestCase):
    def test_modelos_str(self):
        beneficio = Beneficio.objects.create(titulo='Postre gratis', descripcion='Helado', puntos_requeridos=60)
        canje = Canje.objects.create(cliente=self.perfil, beneficio=beneficio)
        pedido = Pedido.objects.create(cliente=self.perfil, total=Decimal('1000.00'), tipo='sitio', completado=False)

        self.assertEqual(str(self.categoria), 'Pizzas')
        self.assertEqual(str(self.producto), 'Pizza')
        self.assertEqual(str(self.perfil), 'cliente')
        self.assertEqual(str(beneficio), 'Postre gratis (60 pts)')
        self.assertEqual(str(canje), 'cliente canjeó Postre gratis')
        self.assertEqual(str(pedido), f'Pedido {pedido.id} - cliente')

    def test_pedido_save_suma_puntos_solo_en_transicion_a_completado(self):
        pedido = Pedido.objects.create(cliente=self.perfil, total=Decimal('4500.00'), tipo='sitio', completado=False)
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.puntos, 40)

        pedido.completado = True
        pedido.save()
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.puntos, 44)

        pedido.save()
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.puntos, 44)

    def test_calcular_puntos_canje_personalizado_y_fallback(self):
        producto_personalizado = Producto(
            categoria=self.categoria,
            nombre='  tacos ',
            descripcion='desc',
            precio=Decimal('2000.00'),
        )
        producto_fallback = Producto(
            categoria=self.categoria,
            nombre='Sopa',
            descripcion='desc',
            precio=Decimal('3500.00'),
        )
        producto_minimo = Producto(
            categoria=self.categoria,
            nombre='',
            descripcion='desc',
            precio=Decimal('500.00'),
        )

        self.assertEqual(calcular_puntos_canje(producto_personalizado), 20)
        self.assertEqual(calcular_puntos_canje(producto_fallback), 3)
        self.assertEqual(calcular_puntos_canje(producto_minimo), 1)

    def test_link_callback_media_existente_faltante_y_url_externa(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            media_dir = os.path.join(temp_dir, 'media')
            static_dir = os.path.join(temp_dir, 'static')
            os.makedirs(os.path.join(media_dir, 'productos'))
            os.makedirs(os.path.join(static_dir, 'css'))
            media_file = os.path.join(media_dir, 'productos', 'demo.txt')
            static_file = os.path.join(static_dir, 'css', 'site.css')
            with open(media_file, 'w', encoding='utf-8') as file_obj:
                file_obj.write('demo')
            with open(static_file, 'w', encoding='utf-8') as file_obj:
                file_obj.write('body {}')

            with override_settings(MEDIA_ROOT=media_dir, MEDIA_URL='/media/', STATIC_ROOT=static_dir, STATIC_URL='/static/'):
                self.assertEqual(
                    os.path.normpath(link_callback('/media/productos/demo.txt', None)),
                    os.path.normpath(media_file),
                )
                self.assertEqual(link_callback('/media/productos/falta.txt', None), '/media/productos/falta.txt')
                self.assertEqual(
                    os.path.normpath(link_callback('/static/css/site.css', None)),
                    os.path.normpath(static_file),
                )
                self.assertEqual(link_callback('https://example.com/logo.png', None), 'https://example.com/logo.png')

    def test_context_processor_para_anonimo_y_autenticado(self):
        request_anon = self.factory.get('/')
        request_anon.user = AnonymousUser()
        self.assertEqual(puntos_usuario(request_anon), {'puntos_usuario': 0})

        usuario_sin_perfil = User.objects.create_user(
            username='contexto',
            email='contexto@example.com',
            password='ClaveSegura123',
        )
        request_auth = self.factory.get('/')
        request_auth.user = usuario_sin_perfil
        self.assertEqual(puntos_usuario(request_auth), {'puntos_usuario': 0})
        self.assertTrue(PerfilCliente.objects.filter(user=usuario_sin_perfil).exists())

    def test_formularios_de_registro_exponen_email(self):
        form_vista = RegistroForm()
        form_modulo = forms_module.RegistroForm()

        self.assertIn('email', form_vista.fields)
        self.assertIn('email', form_modulo.fields)


class AdminActionTests(BaseGestionTestCase):
    def test_accion_admin_resetea_puntos_y_envia_mensaje(self):
        admin_model = PerfilClienteAdmin(PerfilCliente, AdminSite())
        request = self.factory.post('/admin/gestion/perfilcliente/')
        request.user = self.admin_user

        with patch.object(admin_model, 'message_user') as mocked_message_user:
            admin_model.resetear_puntos(request, PerfilCliente.objects.filter(pk=self.perfil.pk))

        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.puntos, 0)
        mocked_message_user.assert_called_once()


class CoreUrlsAndManageTests(TestCase):
    @override_settings(DEBUG=True, MEDIA_URL='/media/', MEDIA_ROOT='media-test')
    def test_core_urls_agrega_static_en_debug(self):
        reloaded = importlib.reload(core_urls)

        self.assertTrue(any(getattr(pattern, 'pattern', None) and 'media/' in str(pattern.pattern) for pattern in reloaded.urlpatterns))
