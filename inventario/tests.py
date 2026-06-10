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
