# DOCUMENTO DE EVIDENCIA TÉCNICA — MÓDULO DE EVENTOS POR PARÁMETROS DE LUGAR Y MAPAS MULTINIVEL
**Proyecto:** ConEvent (SIGEA — Sistema Inteligente de Gestión de Eventos Académicos)  
**Dominio de Producción:** [https://conevent.duckdns.org](https://conevent.duckdns.org)  
**Tareas de Cronograma Validadas:** Filas 30, 31, 32 y 33 (RF-10, RF-12, RF-13, RF-14)  
**Estado Anterior:** 0% — **Estado Actual:** 100% COMPLETADO Y OPERATIVO EN PRODUCCIÓN  

---

## 1. Resumen de Arquitectura Multi-Evento
La transformación arquitectónica RF-10 desacopló las entidades del sistema (proyectos, stands, criterios y evaluaciones) de una configuración monolítica, vinculándolas a un modelo central `Evento`. Esto permite a la institución albergar concurrentemente múltiples congresos, foros y concursos (ej. *Expo DTAI*, *Feria de Emprendimiento*, *Semana de Ingeniería*), cada uno con sus propias fechas, recintos físicos y participantes.

---

## 2. Gestión de Sesión y Clave PIN de Acceso (Filas 31 y 33 del Cronograma)

### 2.1 Modelo `ParticipacionEvento` y Evento Activo
En `usuarios/models.py`:
```python
class Evento(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estatus = models.CharField(max_length=20, default='activo')
    recinto = models.ForeignKey('espacios.Recinto', on_delete=models.PROTECT, related_name='eventos')
    clave_acceso = models.CharField(max_length=20, blank=True, null=True, help_text="PIN de inscripción")


class ParticipacionEvento(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participaciones_eventos')
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='participantes')
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'evento')
```

### 2.2 Flujo Ligero de Membresía (Sin 2FA Invasivo)
En `usuarios/views.py`:
- `eventos_portal_view` (`/auth/eventos/`): Despliega las tarjetas de todos los eventos activos.
- `seleccionar_evento_view`: Almacena `request.session['evento_activo_id'] = evento.id`, permitiendo que todo el dashboard y los mapas filtren el contexto sin recargar la sesión.
- `unirse_evento_view`: Solicita el PIN de inscripción una sola ocasión y crea el registro `ParticipacionEvento`. El usuario no vuelve a ser interrumpido por códigos de seguridad en visitas subsecuentes.

---

## 3. Backend y Motor de Mapas SVG Multinivel (Fila 32 del Cronograma)

### 3.1 Endpoint `/api/stands/mapa/` en `espacios/api_views.py`
Provee una respuesta JSON optimizada agrupada por plantas físicas, con información serializada de proyectos, líderes, evaluadores y colores por carrera:
```python
# espacios/api_views.py
resultado.append({
    'recinto_id': recinto.pk,
    'recinto_nombre': recinto.nombre,
    'planta_id': planta.pk,
    'planta_nombre': planta.nombre,
    'nivel': planta.nivel,
    'filas': planta.filas,
    'columnas': planta.columnas,
    'geometria': planta.descripcion,
    'stands': stands_data
})
```

### 3.2 Motores SVG en `templates/espacios/mapa_auditorio.html`

1. **Auditorio UTEQ (Recinto 1 — Planta Única):**
   - Distribución de 70 stands en grilla de 7 columnas por 10 filas ($11.7\text{m} \times 30\text{m}$).
   - Escenario principal superior y marcadores de zona (`A`, `B`, `C`).

2. **Edificio K / DTAI — Planta Baja (Nivel 0):**
   - Geometría en **"L" invertida hacia la izquierda** uniendo el pasillo principal ($29\text{m} \times 5\text{m}$) con la extensión ($16\text{m} \times 6.67\text{m}$).
   - Stands ubicados **exclusivamente en las orillas** (`pos_col = 1` y `pos_col = 2`), dejando un pasillo central libre de $70\text{px}$ para circulación con la etiqueta `"PASILLO CENTRAL"`.
   - Rótulo `"↑ ENTRADA PRINCIPAL"` sobre el frente exterior de $6.67\text{m}$.

3. **Edificio K / DTAI — Planta Alta (Nivel 1):**
   - Geometría alargada de $29\text{m} \times 5\text{m}$ con bota de ensanchamiento posterior a $7.33\text{m}$.
   - Stands ubicados en orillas y fila de cierre posterior sobre muro de fondo.
   - Rótulo `"↑ LLEGADA DE ESCALERAS / ENTRADA"`.

---

## 4. Desobstrucción Topológica de Escaleras (RF-14)

En `espacios/management/commands/poblar_auditorio.py` y el motor SVG se implementó la remoción de celdas que colisionaban con barreras arquitectónicas reales:

```python
# espacios/management/commands/poblar_auditorio.py

# PLANTA BAJA:
# Se omitieron las filas 21 a 24 (stands PB-41 a PB-48) para despejar el cubo de escaleras
for fila in range(1, 21):
    for col in [1, 2]:
        Stand.objects.create(planta=planta, numero=f"PB-{str(creados + 1).zfill(2)}", ...)

# PLANTA ALTA:
# Se omitieron los stands en la orilla derecha en las filas 25 a 27 (PA-52, PA-54, PA-56)
for fila in range(25, 30):
    Stand.objects.create(planta=planta, numero=f"PA-{str(creados + 1).zfill(2)}", pos_col=1, ...)
    if fila in [28, 29]: # Solo filas 28 y 29 en el muro derecho
        Stand.objects.create(planta=planta, numero=f"PA-{str(creados + 1).zfill(2)}", pos_col=2, ...)
```

En `templates/espacios/mapa_auditorio.html` se renderiza el área protegida con recuadros de advertencia arquitectónica rotulados `"ÁREA DE ESCALERAS"` y `"ESCALERAS"`, impidiendo la asignación accidental de mesas a dicho espacio.

---

## 5. Guía de Capturas Recomendadas para Auditoría

| No. | Elemento a Evidenciar | Procedimiento / URL | Justificación Técnica |
|:---:|:----------------------|:-------------------|:----------------------|
| **1** | Portal de Selección de Eventos | `https://conevent.duckdns.org/auth/eventos/` | Valida el catálogo de eventos disponibles y el modal para ingresar PIN. |
| **2** | Mapa Interactivo del Auditorio | `/espacios/mapa/?recinto=1` | Muestra la grilla 7x10 con escenario superior y stands libres/ocupados. |
| **3** | Mapa Edificio K Planta Baja (L) | `/espacios/mapa/?recinto=2` (Pestaña "Planta Baja") | Exhibe la forma en L a la izquierda, pasillo central libre >70px, cubo de escaleras y entrada principal. |
| **4** | Mapa Edificio K Planta Alta | `/espacios/mapa/?recinto=2` (Pestaña "Planta Alta") | Muestra el pasillo alargado con ensanchamiento, llegada de escaleras desobstruida y fila de fondo. |
| **5** | Interacción con Side-Panel | Clic sobre un stand ocupado | Comprueba el despliegue de detalles del proyecto, carrera y evaluador asignado. |
