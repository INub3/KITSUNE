# 狐 Kitsune — Simulación de Phishing para Concientización

Plataforma de simulación de phishing para **ejercicios de concientización autorizados**. Envía
desde correo propio autenticado (SPF/DKIM/DMARC), trackea apertura/clic/interacción y se
administra desde una consola web local — todo con captura de interacción **sin almacenamiento de
credenciales**.

> **Uso autorizado únicamente.** Esta infraestructura se despliega exclusivamente para engagements
> con alcance y ventana de tiempo autorizados por escrito. Mantener todo dentro del scope firmado y
> conservar configuración y base de datos para el reporte de decommissioning.

---

## Documentación

La guía de replicación está dividida en dos documentos dentro de [`docs/`](docs/):

| Documento | Contenido |
|-----------|-----------|
| **[docs/infraestructura-correo.md](docs/infraestructura-correo.md)** | Montaje del servidor de correo: DNS, rDNS, TLS/Certbot, **OpenDKIM**, **Postfix** y validación de SPF/DKIM/DMARC (Fases 0–5). |
| **[docs/plataforma.md](docs/plataforma.md)** | La consola Kitsune: estructura, pestañas, características, despliegue (systemd/Nginx/túnel SSH), aging, ejecución de campañas y decommissioning (Fases 6–9). |

Orden recomendado: primero **infraestructura de correo**, luego **plataforma**.

---

## Guía rápida

### 1. Instalar y arrancar la consola

```bash
git clone <repo> /opt/kitsune      # o cualquier directorio (rutas independientes)
cd /opt/kitsune
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 run.py                     # consola en http://127.0.0.1:5000
```

En el primer arranque se crea `data/kitsune.db` con un perfil SMTP local y 3 plantillas base.

`python3 run.py` es **bloqueante** (corre en primer plano y muere al cerrar la sesión): sirve para
probar. Para operar, déjalo como servicio.

### 1b. Correr como servicio (systemd, recomendado)

Arranca solo, reinicia si se cae y usa gunicorn (`-w 1`: el envío de campañas corre en un hilo del
worker, un solo worker evita duplicar lanzamientos).

`/etc/systemd/system/kitsune.service`:

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
systemctl enable --now kitsune      # arranca ahora y en cada boot
journalctl -u kitsune -f           # ver logs en vivo
```

Alternativa efímera (una sola sesión): `tmux new -s kitsune` y adentro `python3 run.py`
(`Ctrl-b d` para desconectar), o `nohup python3 run.py > kitsune.log 2>&1 &`.

Detalles en [docs/plataforma.md → Despliegue](docs/plataforma.md#fase-6--despliegue).

### 2. Acceder por túnel SSH

```bash
# Desde la máquina del operador
ssh -L 8080:127.0.0.1:5000 root@10.10.0.1
# Abrir http://localhost:8080/dashboard
```

Las rutas de administración **no** se exponen en Nginx: solo se llegan por el túnel.

### 3. Lanzar una campaña (en la consola)

1. **Perfiles de envío** — confirma el SMTP (localhost:25) y usa "Probar envío".
2. **Usuarios** — crea un grupo e importa objetivos (CSV con header `email`).
3. **Plantillas** — ajusta el pretexto y su landing (preview en vivo).
4. **Phishing** — crea la campaña (perfil + plantilla + grupo + Base URL) y **Lánzala**.
5. **Dashboard** — seguimiento en tiempo real y export CSV.

> Para enviar a objetivos reales necesitas el correo autenticado y con aging: ver
> [docs/infraestructura-correo.md](docs/infraestructura-correo.md) y la
> [Fase 7 — Aging](docs/plataforma.md#fase-7--aging-y-warm-up).

### Configuración rápida (variables de entorno)

Todo `config.py` admite override con prefijo `KITSUNE_`:

```bash
export KITSUNE_PORT=5000
export KITSUNE_BASE_URL="https://dominio.com"
export KITSUNE_DATA_DIR="/opt/kitsune/data"
export KITSUNE_SECRET="cambia-esta-clave"
```

