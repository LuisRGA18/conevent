from usuarios.models import Evento

def contexto_global_conevent(request):
    """
    Context processor para inyectar datos del evento y recinto activo en todas las plantillas.
    Permite dinamismo en la barra lateral y cabeceras sin repetir lógica en cada vista.
    """
    contexto = {
        'evento_activo_global': None,
        'recinto_activo_nombre': None,
        'nombre_mapa_sidebar': 'Mapa del Recinto'
    }

    if not request.user.is_authenticated:
        return contexto

    evento_id = request.session.get('evento_activo_id')
    evento = None
    if evento_id:
        try:
            evento = Evento.objects.select_related('recinto').get(pk=evento_id)
        except Evento.DoesNotExist:
            evento = None

    if not evento:
        evento = Evento.objects.filter(estatus__in=['PUBLICADO', 'activo']).select_related('recinto').first()

    if evento and evento.recinto:
        contexto['evento_activo_global'] = evento
        recinto = evento.recinto
        rec_nombre = recinto.nombre
        contexto['recinto_activo_nombre'] = rec_nombre

        # Regla de dinamismo por ID / nombre de recinto:
        if recinto.id == 1 or 'auditorio' in rec_nombre.lower():
            contexto['nombre_mapa_sidebar'] = 'Mapa del Auditorio'
        elif recinto.id == 2 or 'k' in rec_nombre.lower() or 'dtai' in rec_nombre.lower():
            contexto['nombre_mapa_sidebar'] = 'Mapa del Edificio K'
        else:
            contexto['nombre_mapa_sidebar'] = f'Mapa de {rec_nombre}'
    else:
        contexto['nombre_mapa_sidebar'] = 'Mapa del Recinto'

    return contexto
