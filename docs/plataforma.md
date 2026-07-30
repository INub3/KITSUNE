# Plataforma Kitsune — setup, uso y características

Kitsune es una **consola web local** (servicio Flask) desde la que se administra todo el
engagement: perfiles de envío, plantillas, objetivos y campañas, más el dashboard de resultados.
Se opera **solo por túnel SSH**.

Requiere un servidor de correo autenticado ya montado — ver
[la guía de infraestructura de correo](infraestructura-correo.md).

> **Uso autorizado únicamente.** Conservar configuración y base de datos para el reporte de
> decommissioning.

---

## Índice

1. [Estructura del proyecto](#estructura-del-proyecto)
2. [La consola (pestañas)](#la-consola-pestañas)
3. [Características](#características)
4. [Fase 6 — Despliegue](#fase-6--despliegue)
5. [Fase 7 — Aging y warm-up](#fase-7--aging-y-warm-up)
6. [Fase 8 — Ejecución de campaña](#fase-8--ejecución-de-campaña)
7. [Fase 9 — Decommissioning](#fase-9--decommissioning)
8. [Troubleshooting de la plataforma](#troubleshooting-de-la-plataforma)

---

## Estructura del proyecto

Las rutas son **independientes del directorio de instalación** (se calculan desde la ubicación
del proyecto), así que puede clonarse en cualquier carpeta — `/opt/kitsune` es solo la
convención sugerida.

```
kitsune/
├── run.py                  # arranca la consola web  (python3 run.py)
├── send.py                 # CLI opcional de campañas (list / run <id>)
├── config.py               # rutas + defaults, todo override por env KITSUNE_*
├── requirements.txt
├── .gitignore
├── docs/                   # esta documentación
├── data/                   # runtime (gitignored): kitsune.db
└── app/
    ├── __init__.py         # fábrica create_app()
    ├── app.py              # objeto WSGI (gunicorn app.app:app)
    ├── db.py               # esquema SQLite + helpers + semillas
    ├── mailer.py           # motor de envío (hilo de fondo por campaña)
    ├── pretexts.py         # datos semilla (perfil/plantillas por defecto)
    ├── static/
    │   └── kitsune.css      # estética compartida (santuario de Inari)
    ├── views/              # blueprints
    │   ├── tracking.py      # /pixel /c /l /s /aviso  (PÚBLICO, proxeado)
    │   ├── dashboard.py     # /dashboard  + export CSV
    │   ├── profiles.py      # perfiles de envío
    │   ├── templates.py     # plantillas de correo
    │   ├── users.py         # objetivos / grupos
    │   └── campaigns.py     # creación y lanzamiento de campañas
    └── templates/
        ├── console/            # UI del OPERADOR (consola)
        │   ├── base.html        # layout con barra lateral
        │   ├── dashboard.html
        │   └── profiles.html · templates.html · users.html · campaigns.html
        └── landings/           # páginas que ve el OBJETIVO (phishing)
            ├── awareness.html   # "esto fue un simulacro" (/aviso)
            └── teams.html · microsoft.html · google.html · sharepoint.html · zoom.html
```

> Las plantillas de la **consola** (`console/`) y las **páginas de phishing** que ve el objetivo
> (`landings/`) están separadas por carpeta. Los `render_template` apuntan a `console/<pág>` y
> `landings/<pág>` respectivamente.

---

## La consola (pestañas)

| Pestaña | Qué hace |
|---------|----------|
| **Dashboard** | Embudo *kitsunebi*, tasas, desglose por pretexto/landing, medidor *kyūbi*, filtro por campaña y export CSV. |
| **Phishing** | Crea una campaña combinando perfil + plantilla + grupo + base URL + delays; la lanza (envío en segundo plano). |
| **Plantillas** | Crea/edita plantillas de correo **en vivo** con preview; placeholders `{{url}} {{pixel}} {{email}} {{first_name}}`. |
| **Perfiles de envío** | SMTP local o relay: host/IP, puerto, STARTTLS, auth opcional, From. **Múltiples perfiles** + envío de prueba. |
| **Usuarios** | Objetivos organizados en grupos; alta individual o import CSV. |

Todo es **master–detail en página** (lista + editor), sin ventanas flotantes.

---

## Características

- **Datos en SQLite** (`data/kitsune.db`): perfiles, plantillas, grupos, objetivos, campañas y
  resultados. En el primer arranque se siembra un perfil local y las 3 plantillas base.
- **Landings** (`teams`, `microsoft`, `google`, `sharepoint`, `zoom`): cada plantilla apunta a una.
- **Delay aleatorio** por correo (configurable por campaña) para evitar correlación en el SOC.
- **Tracking**: apertura (pixel), clic (`/c/<token>`), interacción (`/s/<token>`).
- **Sin credenciales**: los inputs de las landings no tienen atributo `name`; el submit hace POST
  solo del token. Ninguna contraseña ni ubicación sale del navegador. El backend solo marca la interacción.
- **Página de concientización** (`/aviso`): destino tras la interacción; explica que fue un simulacro.
- **Configuración por entorno**: cualquier valor de `config.py` admite override `KITSUNE_*`
  (`KITSUNE_PORT`, `KITSUNE_DATA_DIR`, `KITSUNE_BASE_URL`, ...).

---

## Fase 6 — Despliegue

```bash
git clone <repo> /opt/kitsune      # o cualquier directorio
cd /opt/kitsune
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Arranque directo (desarrollo / operación simple)
python3 run.py                     # sirve en 127.0.0.1:5000

chown -R www-data:www-data /opt/kitsune
chmod -R 775 /opt/kitsune/data
nginx -t && systemctl reload nginx
```

### Endpoints de tracking en Nginx

Dentro del bloque `server { listen 443 ... }` de `/etc/nginx/sites-available/soporteclave`
(el vhost 443 lo genera Certbot en la [guía de correo](infraestructura-correo.md#fase-2--sitio-benigno--tls)):

```nginx
location = /pixel { proxy_pass http://127.0.0.1:5000; proxy_set_header X-Real-IP $remote_addr; proxy_set_header Host $host; }
location = /aviso { proxy_pass http://127.0.0.1:5000; proxy_set_header X-Real-IP $remote_addr; proxy_set_header Host $host; }
location /c/      { proxy_pass http://127.0.0.1:5000; proxy_set_header X-Real-IP $remote_addr; proxy_set_header Host $host; }
location /l/      { proxy_pass http://127.0.0.1:5000; proxy_set_header X-Real-IP $remote_addr; proxy_set_header Host $host; }
location /s/      { proxy_pass http://127.0.0.1:5000; proxy_set_header X-Real-IP $remote_addr; proxy_set_header Host $host; }
```

**No** proxear las rutas de administración (`/dashboard`, `/campaigns`, `/templates`,
`/profiles`, `/users`, `/static`): solo se alcanzan por túnel SSH.

### Servicio systemd

`/etc/systemd/system/kitsune.service` — usar **`-w 1`**: el envío de campañas corre en un hilo de
fondo dentro del worker, así que un solo worker evita duplicar lanzamientos.

```ini
[Unit]
Description=Kitsune · consola de simulación de phishing
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/kitsune
Environment=KITSUNE_SECRET=cambia-esta-clave
ExecStart=/opt/kitsune/venv/bin/gunicorn -w 1 -b 127.0.0.1:5000 --timeout 120 app.app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now kitsune
```

### Acceso a la consola (túnel SSH)

```bash
# Desde la máquina del operador
ssh -L 8080:127.0.0.1:5000 root@10.10.0.1
# Abrir http://localhost:8080/dashboard
```

---

## Fase 7 — Aging y warm-up

**No lanzar la campaña a objetivos reales sobre un dominio recién levantado.** Durante 30–90
días (mínimo 30; 60–90 para clientes con seguridad madura):

- Mantener el sitio benigno vivo con HTTPS válido. Nunca parkeado.
- Tráfico legítimo de bajo volumen incremental (correos entre buzones propios, alguna
  suscripción). Nunca pasar de 0 a un blast.
- **Categorización web**: enviar el dominio a categorización benigna (Business / Technology) en
  Cisco Talos/Umbrella, Palo Alto, Symantec/Broadcom, Forcepoint, McAfee. Si el cliente usa
  Umbrella, esto es determinante.
- Monitorear los reportes DMARC que lleguen a `dmarc@dominio.com`.

Alternativa: dominio expirado con historia y categorización previas (auditar antes en VirusTotal,
Wayback Machine y blocklists — un historial envenenado es peor que uno nuevo).

---

## Fase 8 — Ejecución de campaña

Todo se hace desde la consola (túnel SSH → `http://localhost:8080`):

1. **Perfiles de envío** → verifica/crea el perfil SMTP (localhost:25 para el Postfix local) y usa
   "Probar envío" para confirmar SPF/DKIM/DMARC contra una cuenta propia.
2. **Usuarios** → crea un grupo e importa los objetivos (CSV con header `email`, opcional
   `first_name,last_name,position`).
3. **Plantillas** → ajusta el pretexto y su landing; previsualiza en vivo.
4. **Phishing** → crea la campaña (perfil + plantilla + grupo + base URL + delays) y **Lánzala**.
   El envío corre en segundo plano con delay aleatorio por correo.
5. **Dashboard** → seguimiento en tiempo real y export CSV.

Alternativa por CLI (automatización):

```bash
cd /opt/kitsune && source venv/bin/activate
python3 send.py list        # lista campañas y su estado
python3 send.py run 3       # ejecuta la campaña 3 de forma síncrona
```

Buenas prácticas:

- **Un dominio por campaña** para no cruzar reputación.
- Comenzar de pretextos sutiles a más agresivos.
- Monitorear resultados en tiempo real vía el dashboard (túnel SSH).

Formato del CSV de import (pestaña Usuarios):

```csv
email,first_name,last_name,position
usuario1@cliente.com,Ana,García,Finanzas
usuario2@cliente.com,Luis,Pérez,TI
```

---

## Fase 9 — Decommissioning

Al cerrar la campaña:

1. Exportar/archivar `data/kitsune.db` (o el CSV del dashboard) y toda la configuración para el reporte.
2. Detener y deshabilitar servicios: `systemctl disable --now kitsune postfix opendkim nginx`.
3. Dar de baja el dominio y liberar/reasignar la IP para no dejar infraestructura huérfana con
   reputación ligada al cliente.
4. Documentar en el reporte: arquitectura, tablas de configuración, cronología de la campaña,
   resultados agregados y plan de decommissioning.

---

## Troubleshooting de la plataforma

| Síntoma | Causa | Solución |
|---------|-------|----------|
| `readonly database` | `www-data` sin permisos sobre `kitsune.db` | `chown www-data` + `chmod 664` sobre el archivo y `775` el directorio `data/` |
| Links `http://` caen en spam | Gateways penalizan HTTP en correo | Usar `https://` en el Base URL de la campaña (cert ya emitido) |
| La campaña queda en `error` | Perfil/plantilla/grupo faltante o SMTP inalcanzable | Revisar el perfil de envío y que el grupo tenga objetivos; ver logs |
| Cambios no se reflejan / doble envío | Varios workers de gunicorn | Usar `-w 1` (el envío corre en un hilo del worker) |

### Logs útiles

```bash
journalctl -u kitsune --no-pager -n 50
```
