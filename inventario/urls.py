from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('item/<uuid:item_uuid>/', views.detalle_item_view, name='detalle_item'),
    path('incidencias/', views.incidencias_activas_view, name='incidencias_activas'),
    path('qr/<int:item_id>/', views.generar_qr_view, name='generar_qr'),
    path('qr/lote/', views.generar_qr_lote_pdf_view, name='generar_qr_lote'),
]
