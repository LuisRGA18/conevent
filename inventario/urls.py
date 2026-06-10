from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('item/<uuid:item_uuid>/', views.detalle_item_view, name='detalle_item'),
]
