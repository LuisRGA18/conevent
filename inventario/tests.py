from django.test import TestCase
from django.contrib.auth import get_user_model
from espacios.models import Stand
from .models import ItemInventario, Incidencia

User = get_user_model()

class InventarioTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='staffuser',
            email='staff@uteq.edu.mx',
            password='Password123!',
            rol='ADMIN'
        )
        self.stand = Stand.objects.create(
            numero='B-01',
            zona='gimnasio'
        )

    def test_creacion_item_inventario(self):
        item = ItemInventario.objects.create(
            nombre='Mesa plegable blanca',
            descripcion='Mesa de plástico de 1.80m',
            estado='bueno',
            stand_asignado=self.stand
        )
        # Verificar autogeneración de UUID
        self.assertIsNotNone(item.uuid)
        self.assertEqual(str(item), 'Mesa plegable blanca (Stand B-01)')
        self.assertTrue(item.url_qr.startswith('/inventario/item/'))

    def test_creacion_incidencia(self):
        item = ItemInventario.objects.create(
            nombre='Silla acojinada negra',
            estado='regular'
        )
        incidencia = Incidencia.objects.create(
            item=item,
            titulo='Pata doblada',
            descripcion='Una de las patas traseras está ligeramente doblada hacia adentro.',
            prioridad='media',
            reportado_por=self.user
        )
        self.assertEqual(incidencia.item, item)
        self.assertFalse(incidencia.resuelta)
        self.assertEqual(str(incidencia), 'Pata doblada - Silla acojinada negra (Activa)')


class InventarioFlowTestCase(TestCase):
    def setUp(self):
        # Crear usuarios
        self.admin = User.objects.create_user(
            username='admin.test',
            email='admin@uteq.edu.mx',
            password='Password123!',
            rol='ADMIN'
        )
        self.alumno = User.objects.create_user(
            username='alumno.test',
            email='alumno@uteq.edu.mx',
            password='Password123!',
            rol='ALUMNO'
        )
        
        # Crear item
        self.item = ItemInventario.objects.create(
            nombre='Pantalla LCD 42 pulgadas',
            descripcion='Pantalla de demostración',
            estado='bueno'
        )

    def test_public_item_view_and_report_flow(self):
        # 1. Escanear UUID sin login (acceso público)
        url = f"/inventario/item/{self.item.uuid}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pantalla LCD 42 pulgadas')
        # Verificar que el formulario está oculto y se sugiere iniciar sesión
        self.assertContains(response, 'Inicio de Sesión Requerido')
        
        # 2. Iniciar sesión como alumno
        self.client.login(username='alumno.test', password='Password123!')
        
        # 3. Escanear UUID con login (se debe ver el formulario)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reportar una Falla / Necesidad')
        self.assertNotContains(response, 'Inicio de Sesión Requerido')
        
        # 4. Reportar incidencia desde el formulario
        post_data = {
            'titulo': 'Pantalla no enciende',
            'descripcion': 'Se presiona el botón de power y no responde.',
            'prioridad': 'alta'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302) # Redirige al mismo detalle
        
        # Verificar creación en base de datos
        self.assertEqual(Incidencia.objects.count(), 1)
        inc = Incidencia.objects.first()
        self.assertEqual(inc.titulo, 'Pantalla no enciende')
        self.assertEqual(inc.reportado_por, self.alumno)
        self.assertFalse(inc.resuelta)
        
        # 5. Panel admin de incidencias activas (alumno no debe poder entrar)
        panel_url = "/inventario/incidencias/"
        response = self.client.get(panel_url)
        self.assertEqual(response.status_code, 302) # Redirige por no tener permisos de admin
        
        # Iniciar sesión como admin
        self.client.login(username='admin.test', password='Password123!')
        response = self.client.get(panel_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pantalla no enciende')
        
        # 6. Marcar como resuelta en el panel admin
        resolve_data = {
            'incidencia_id': inc.id,
            'comentarios_resolucion': 'Se cambió el cable de alimentación dañado.'
        }
        response = self.client.post(panel_url, resolve_data)
        self.assertEqual(response.status_code, 302) # Redirige al mismo panel
        
        # Verificar resolución en base de datos
        inc.refresh_from_db()
        self.assertTrue(inc.resuelta)
        self.assertEqual(inc.comentarios_resolucion, 'Se cambió el cable de alimentación dañado.')
        self.assertIsNotNone(inc.fecha_resolucion)

    def test_qr_generation(self):
        self.client.login(username='admin.test', password='Password123!')
        
        # Generar código QR individual
        qr_url = f"/inventario/qr/{self.item.id}/"
        response = self.client.get(qr_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        
        # Generar códigos QR en lote (PDF)
        pdf_url = "/inventario/qr/lote/"
        response = self.client.get(pdf_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('attachment; filename='))


from django.urls import reverse

class InventarioGestionTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin.inv',
            email='admin.inv@uteq.edu.mx',
            password='Password123!',
            rol='ADMIN'
        )
        self.alumno = User.objects.create_user(
            username='alumno.inv',
            email='alumno.inv@uteq.edu.mx',
            password='Password123!',
            rol='ALUMNO'
        )
        self.item = ItemInventario.objects.create(
            nombre='Mesa Plástica',
            descripcion='Mesa plegable',
            estado='bueno'
        )

    def test_gestionar_inventario_acceso(self):
        url = reverse('inventario:gestionar_inventario')
        
        # 1. Alumno no puede acceder
        self.client.login(username='alumno.inv', password='Password123!')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        
        # 2. Admin sí puede acceder
        self.client.login(username='admin.inv', password='Password123!')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mesa Plástica')

    def test_crear_item_via_post(self):
        url = reverse('inventario:gestionar_inventario')
        self.client.login(username='admin.inv', password='Password123!')
        
        data = {
            'nombre': 'Silla plegable',
            'descripcion': 'Silla plástica',
            'estado': 'bueno',
            'stand_asignado': ''
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirects
        
        # Verify db
        self.assertTrue(ItemInventario.objects.filter(nombre='Silla plegable').exists())

    def test_cambiar_estado_item_view(self):
        url = reverse('inventario:cambiar_estado_item', args=[self.item.id])
        self.client.login(username='admin.inv', password='Password123!')
        
        data = {
            'estado': 'malo'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        
        self.item.refresh_from_db()
        self.assertEqual(self.item.estado, 'malo')

