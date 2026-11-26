# DOCUMENTO DE EVIDENCIA TÉCNICA — SEGUIMIENTO DE PRUEBAS QA, DESPLIEGUE EN GCP Y CIERRE
**Proyecto:** ConEvent (SIGEA — Sistema Inteligente de Gestión de Eventos Académicos)  
**Dominio de Producción:** [https://conevent.duckdns.org](https://conevent.duckdns.org)  
**Tareas de Cronograma Validadas:** Filas 40 a 63  
**Estado Anterior:** 0% — **Estado Actual:** 100% COMPLETADO Y OPERATIVO EN PRODUCCIÓN  

---

## 1. Plan de Pruebas y Matriz de Hallazgos Corregidos (Filas 41 a 48 del Cronograma)

Durante el ciclo de estabilización e integración continua, se ejecutó un protocolo riguroso de Aseguramiento de Calidad (QA) que detectó y resolvió de raíz excepciones técnicas críticas:

| ID Incidencia | Tipo de Error | Módulo / Ubicación | Causa Raíz | Solución Definitiva Aplicada |
|:---:|:---|:---|:---|:---|
| **BUG-01** | `UnboundLocalError: cannot access local variable 'Proyecto'` | `usuarios/views.py` (`index_view`) | Importaciones locales de `Proyecto` dentro de ramas condicionales `elif rol == 'ALUMNO':` sombreaban el alcance del símbolo a nivel de toda la función. | Se extrajeron todas las importaciones de modelos a la cabecera del módulo `usuarios/views.py`, normalizando el ámbito léxico. |
| **BUG-02** | `IntegrityError: duplicate key value violates unique constraint "usuarios_evento_pkey"` | Base de datos PostgreSQL | Desincronización entre la secuencia interna de autoincremento `usuarios_evento_id_seq` y los registros insertados manualmente vía fixture con IDs fijos. | Ejecución de `SELECT setval('usuarios_evento_id_seq', (SELECT MAX(id) FROM usuarios_evento));` restableciendo el contador de llaves primarias. |
| **BUG-03** | `NameError: name 'Decimal' is not defined` | `usuarios/views.py` (`evaluar_proyecto_view`) | Omisión del paquete `from decimal import Decimal` al calcular la suma de ponderaciones de rúbricas dinámicas. | Inclusión de `from decimal import Decimal` al inicio del archivo y conversión estricta de cadenas numéricas a `Decimal`. |
| **BUG-04** | `CommandError: the following arguments are required: --evento` | `espacios/management/commands/asignar_stands.py` | Pruebas unitarias invocaban `asignar_stands` sin especificar el ID del evento obligatorio en la nueva arquitectura multi-evento. | Actualización del test suite en `espacios/tests.py` pasando `evento=self.evento.id`. |

---

## 2. Infraestructura de Producción en Google Cloud Platform (Filas 51 a 56 del Cronograma)

### 2.1 Topología de Despliegue en GCP
El sistema opera sobre una arquitectura en capas alojada en una Máquina Virtual de Compute Engine con sistema operativo **Ubuntu Server 22.04 LTS**:

```
[ Cliente Web / Móvil ]
          │ (HTTPS - Puerto 443 con Certificado Let's Encrypt TLS 1.3)
          ▼
     [ Nginx Proxy ]  ─── Servir Archivos Estáticos Optimizados (/static/ vía WhiteNoise)
          │
          │ (Unix Domain Socket / HTTP Localhost:8000)
          ▼
   [ Gunicorn WSGI ]  ─── Workers asíncronos administrados por Systemd (conevent.service)
          │
          ▼
  [ Django Core App ] ─── Conexión persistente mediante psycopg2-binary
          │
          ▼
   [ PostgreSQL DB ]  ─── Base de datos relacional con respaldos transaccionales
```

### 2.2 Configuración del Servicio Systemd (`/etc/systemd/system/conevent.service`)
```ini
[Unit]
Description=Gunicorn Daemon for ConEvent (SIGEA)
After=network.target

[Service]
User=g2023171052
Group=www-data
WorkingDirectory=/home/g2023171052/conevent
ExecStart=/home/g2023171052/conevent/env/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          conevent.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2.3 Bloque de Servidor en Nginx (`/etc/nginx/sites-available/conevent`)
```nginx
server {
    server_name conevent.duckdns.org;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root /home/g2023171052/conevent;
    }
    location /media/ {
        root /home/g2023171052/conevent;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }

    listen 443 ssl; # Administrado por Certbot
    ssl_certificate /etc/letsencrypt/live/conevent.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/conevent.duckdns.org/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    listen 80;
    server_name conevent.duckdns.org;
    return 301 https://$host$request_uri; # Forzar redirección HTTPS
}
```

---

## 3. Matriz Completa de Cierre de Entregables (Filas 57 a 63 del Cronograma)

| ID Fila | Hito / Entregable de Cierre | Estado Documental | Estado Operativo | Dictamen de Cumplimiento |
|:---:|:---|:---:|:---:|:---|
| **57** | Integración Continua y Despliegue en Producción | Anterior: 0% | **100%** | **CUMPLIDO:** Plataforma en vivo en GCP bajo dominio `https://conevent.duckdns.org`. |
| **58** | Seguridad Perimetral y Cifrado HTTPS | Anterior: 0% | **100%** | **CUMPLIDO:** Certificado SSL/TLS Let's Encrypt activo con redirección forzada. |
| **59** | Pruebas Unitarias de Regresión | Anterior: 0% | **100%** | **CUMPLIDO:** Suite de pruebas en `espacios/tests.py` validando modelos, API y asignación. |
| **60** | Optimización de Estáticos y Media | Anterior: 0% | **100%** | **CUMPLIDO:** WhiteNoise + Nginx despachando bundles CSS/JS minificados sin sobrecarga en WSGI. |
| **61** | Desobstrucción y Calibración de Mapas | Anterior: 0% | **100%** | **CUMPLIDO:** Auditorio y Edificio K (PB y PA) calibrados a escala real con pasillos libres. |
| **62** | Documentación Técnica de Auditoría | Anterior: 0% | **100%** | **CUMPLIDO:** Generación de la suite completa de 5 documentos técnicos en `docs_auditoria/`. |
| **63** | Entrega y Aceptación Final del Sistema | Anterior: 0% | **100%** | **CUMPLIDO:** Sistema 100% probado, estabilizado y disponible para auditoría docente. |

---

## 4. Guía de Capturas Recomendadas para Auditoría

| No. | Elemento a Evidenciar | Procedimiento / Comando | Justificación Técnica |
|:---:|:----------------------|:-----------------------|:----------------------|
| **1** | Estado Activo del Servicio Gunicorn | SSH en GCP: `sudo systemctl status conevent` | Muestra el daemon Gunicorn activo (`active (running)`) gestionando los procesos de la aplicación. |
| **2** | Estado Activo del Servidor Web Nginx | SSH en GCP: `sudo systemctl status nginx` | Demuestra que el servidor web proxy inverso está operando correctamente en los puertos 80 y 443. |
| **3** | Consola de Google Cloud Platform | Panel de GCP $\rightarrow$ Compute Engine $\rightarrow$ Instancias de VM | Exhibe la máquina virtual ejecutándose con su IP externa asociada a DuckDNS. |
| **4** | Ejecución de Pruebas Automatizadas | Terminal: `python manage.py test espacios` | Certifica la aprobación de pruebas unitarias sobre recintos, plantas y asignación de stands. |
| **5** | Navegación Global en Producción | Navegador en `https://conevent.duckdns.org/` | Evidencia visual de la plataforma en pleno funcionamiento sobre Internet. |
