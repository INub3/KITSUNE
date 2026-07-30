# Infraestructura de correo — Postfix · OpenDKIM · SPF/DKIM/DMARC

Montaje del servidor de correo propio y autenticado sobre el que Kitsune envía. Cubre desde el
DNS hasta la validación de que SPF/DKIM/DMARC pasan de forma consistente. Al terminar esta guía,
el VPS puede enviar correo firmado; la operación de campañas se documenta en
[la guía de la plataforma](plataforma.md).

> **Uso autorizado únicamente.** Desplegar solo para engagements con alcance y ventana de tiempo
> autorizados por escrito.

Variables de ejemplo (sustituir por las del engagement):

- Dominio: `dominio.com`
- IP pública: `10.10.0.1`
- Host de correo: `mail.dominio.com`

---

## Índice

1. [Arquitectura](#arquitectura)
2. [Requisitos previos](#requisitos-previos)
3. [Fase 0 — DNS](#fase-0--dns)
4. [Fase 1 — Base del sistema](#fase-1--base-del-sistema)
5. [Fase 2 — Sitio benigno + TLS](#fase-2--sitio-benigno--tls)
6. [Fase 3 — DKIM (OpenDKIM)](#fase-3--dkim-opendkim)
7. [Fase 4 — Postfix](#fase-4--postfix)
8. [Fase 5 — Validación de autenticación](#fase-5--validación-de-autenticación)
9. [Troubleshooting de correo](#troubleshooting-de-correo)

---

## Arquitectura

```
                      Internet
                         │
          ┌──────────────┴───────────────┐
          │        VPS Debian 12         │
          │                              │
   :25 ───┤ Postfix ──milter──► OpenDKIM │  Envío firmado (SPF/DKIM/DMARC)
          │    │                         │
  :443 ───┤ Nginx (TLS) ──proxy──► Flask │  Tracking: /pixel /c /l /s /aviso
          │                    (Gunicorn)│  (localhost:5000)
          │                        │     │
          │                     SQLite   │  data/kitsune.db
          │                              │
  consola ┤ SOLO vía túnel SSH ──────────┤  Dashboard + admin (no expuesto)
          └──────────────────────────────┘
```

| Componente | Rol |
|------------|-----|
| Postfix | MTA de envío |
| OpenDKIM | Firma DKIM vía milter |
| Nginx | TLS + proxy de endpoints de tracking |
| Flask + Gunicorn | Backend de tracking y consola (ver [plataforma](plataforma.md)) |
| SQLite | Persistencia de eventos |
| Certbot | Certificado Let's Encrypt |

---

## Requisitos previos

- VPS con Debian 12+ e IP pública.
- Acceso a configurar **rDNS/PTR** en el panel del proveedor del VPS (crítico).
- Dominio registrado con control de DNS (aquí: Namecheap BasicDNS).
- Dominio con **aging** de 30–90 días antes de enviar a objetivos reales
  (ver [Aging y warm-up](plataforma.md#fase-7--aging-y-warm-up)).

---

## Fase 0 — DNS

Configurar en el panel DNS del dominio. En Namecheap → **Advanced DNS**; el campo Host usa
la parte relativa (`@` para el apex, `mail` para el subdominio), sin FQDN.

| Tipo | Host | Valor | Notas |
|------|------|-------|-------|
| A | `mail` | `10.10.0.1` | |
| MX | `@` | `mail.dominio.com` | Priority 10. Apunta a hostname, nunca a IP |
| TXT | `@` | `v=spf1 mx -all` | SPF |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@dominio.com` | Arranca en `p=none` |
| TXT | `mail._domainkey` | *(se genera en Fase 3)* | DKIM |

En Namecheap, cambiar **Mail Settings → Custom MX** antes de añadir el MX. No incluir comillas
en los TXT (el panel las agrega solo).

**PTR / rDNS** — se configura en el panel del proveedor del VPS, no en el DNS del dominio:

```
10.10.0.1  →  mail.dominio.com
```

Verificación (los cuatro deben resolver antes de continuar):

```bash
dig +short A   mail.dominio.com          # 10.10.0.1
dig +short MX  dominio.com               # 10 mail.dominio.com.
dig +short TXT dominio.com               # "v=spf1 mx -all"
dig +short TXT _dmarc.dominio.com        # "v=DMARC1; p=none..."
dig +short -x  10.10.0.1                 # mail.dominio.com.  (FCrDNS)
```

---

## Fase 1 — Base del sistema

```bash
hostnamectl set-hostname mail.dominio.com
```

Editar `/etc/hosts` y asegurar una línea propia (cada entrada en su renglón, terminada en salto):

```
127.0.0.1       localhost
127.0.1.1       server1.lstamericas.com server1
10.10.0.1  mail.dominio.com mail
```

```bash
hostname -f                     # debe devolver mail.dominio.com
apt update && apt upgrade -y
apt install -y postfix dovecot-imapd dovecot-lmtpd opendkim opendkim-tools \
               certbot python3-certbot-nginx nginx swaks
```

En el prompt de Postfix: **Internet Site**; System mail name = `dominio.com` (apex, no el subdominio).

---

## Fase 2 — Sitio benigno + TLS

Landing benigna (también sirve al aging: nunca dejar el dominio parkeado):

```bash
mkdir -p /var/www/html
cat > /var/www/html/index.html <<'EOF'
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>Soporte Clave — Consultoría TI</title></head>
<body><h1>Soporte Clave</h1><p>Sitio corporativo en mantenimiento.</p></body></html>
EOF
```

Vhost de Nginx:

```bash
cat > /etc/nginx/sites-available/soporteclave <<'EOF'
server {
    listen 80;
    server_name dominio.com www.dominio.com mail.dominio.com;
    root /var/www/html;
    index index.html;
    location / { try_files $uri $uri/ =404; }
}
EOF
ln -sf /etc/nginx/sites-available/soporteclave /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

Certificado (si ya existe uno para el apex, añadir `--expand`):

```bash
certbot --nginx \
  -d dominio.com -d www.dominio.com -d mail.dominio.com \
  --agree-tos -m admin@dominio.com -n --redirect --expand

curl -I https://dominio.com          # 200 + TLS válido
certbot certificates                       # anotar la ruta del cert con los 3 nombres
```

Ruta resultante (para Postfix en Fase 4):

```
/etc/letsencrypt/live/dominio.com/fullchain.pem
/etc/letsencrypt/live/dominio.com/privkey.pem
```

---

## Fase 3 — DKIM (OpenDKIM)

Generar la llave:

```bash
mkdir -p /etc/dkimkeys
opendkim-genkey -b 2048 -s mail -d dominio.com -D /etc/dkimkeys
chown -R opendkim:opendkim /etc/dkimkeys
chmod 700 /etc/dkimkeys
chmod 600 /etc/dkimkeys/mail.private
```

`/etc/opendkim.conf`:

```
Syslog                  yes
UMask                   002
Canonicalization        relaxed/simple
Mode                    sv
SubDomains              no
Socket                  inet:8891@localhost
PidFile                 /run/opendkim/opendkim.pid
OversignHeaders         From
KeyTable                /etc/opendkim/KeyTable
SigningTable            /etc/opendkim/SigningTable
InternalHosts           /etc/opendkim/TrustedHosts
RequireSafeKeys         false
LogWhy                  yes
```

Tablas — **la SigningTable usa formato de dominio simple, NO wildcard `*@`**
(el wildcard requiere modo `refile:` y falla silenciosamente sin él):

```bash
mkdir -p /etc/opendkim
echo "mail._domainkey.dominio.com dominio.com:mail:/etc/dkimkeys/mail.private" \
     > /etc/opendkim/KeyTable
echo "dominio.com mail._domainkey.dominio.com" \
     > /etc/opendkim/SigningTable
printf "127.0.0.1\nlocalhost\n10.10.0.1\n" \
     > /etc/opendkim/TrustedHosts
systemctl restart opendkim && systemctl enable opendkim
```

Publicar el TXT del DKIM en el DNS. Ver la llave pública:

```bash
cat /etc/dkimkeys/mail.txt
```

En Namecheap → TXT Record → Host `mail._domainkey` → Value = los fragmentos entre paréntesis
**unidos en una sola línea, sin comillas ni espacios en el punto de unión** (`...s5C` + `Seem...`
→ `...s5CSeem...`).

Verificar:

```bash
dig +short TXT mail._domainkey.dominio.com @1.1.1.1
opendkim-testkey -d dominio.com -s mail -vvv     # debe terminar en "key OK"
```

`key not secure` es cosmético (falta DNSSEC); lo relevante es el `key OK`.

---

## Fase 4 — Postfix

Editar `/etc/postfix/main.cf` (ajustar existentes, añadir faltantes):

```
myhostname = mail.dominio.com
mydomain = dominio.com
myorigin = $mydomain
inet_interfaces = all
inet_protocols = ipv4
mydestination = $myhostname, localhost.$mydomain, localhost, $mydomain

# TLS
smtpd_tls_cert_file = /etc/letsencrypt/live/dominio.com/fullchain.pem
smtpd_tls_key_file  = /etc/letsencrypt/live/dominio.com/privkey.pem
smtpd_tls_security_level = may
smtp_tls_security_level  = may
smtpd_tls_protocols = !SSLv2, !SSLv3, !TLSv1, !TLSv1.1

# DKIM milter
milter_default_action = accept
milter_protocol = 6
smtpd_milters = inet:localhost:8891
non_smtpd_milters = inet:localhost:8891
```

```bash
systemctl restart postfix opendkim
postconf myhostname mydomain myorigin
ss -tlnp | grep -E ':25|:8891'      # master en :25, opendkim en :8891
```

---

## Fase 5 — Validación de autenticación

Enviar por SMTP local (usar `swaks`, no `sendmail` — el envío como root por pickup no dispara
el milter correctamente):

```bash
swaks --to TU_CUENTA@gmail.com \
      --from soporte@dominio.com \
      --server 127.0.0.1:25 \
      --header "Subject: Test de autenticacion" \
      --body "Prueba SPF/DKIM/DMARC."
```

En Gmail → **Mostrar original**, confirmar los tres:

```
SPF:   PASS
DKIM:  PASS   (header.i=@dominio.com header.s=mail)
DMARC: PASS
```

Score de reputación: enviar a la dirección que da <https://www.mail-tester.com> y apuntar a ≥ 9/10.

Prueba de consistencia (los 5 deben devolver `250 queued`, ninguno `451`):

```bash
for i in 1 2 3 4 5; do
  swaks --to TU_CUENTA@gmail.com --from soporte@dominio.com \
        --server 127.0.0.1:25 --header "Subject: Consistencia $i" \
        --body "Prueba $i." 2>&1 | grep -E "queued|451"
  sleep 30
done
```

No avanzar a campaña hasta que la firma sea consistente al 100%. Con esto listo, continúa en
[la guía de la plataforma](plataforma.md).

---

## Troubleshooting de correo

| Síntoma | Causa | Solución |
|---------|-------|----------|
| `hostname -f` devuelve valores pegados | `/etc/hosts` sin salto de línea final; el `echo` concatenó | Editar y dejar cada entrada en su renglón |
| MX rechazado / no resuelve | MX apuntando a IP | El MX apunta a hostname (`mail.dominio`), que resuelve a IP por el registro A |
| `certbot` aborta en modo `-n` | Cert previo con parte de los dominios | Añadir `--expand` |
| DKIM no firma, `no signing table match` | SigningTable con wildcard `*@` sin modo `refile:` | Usar formato simple: `dominio  mail._domainkey.dominio` |
| DKIM no firma, `key data is not secure` | Chequeo de seguridad de la llave | `RequireSafeKeys false` en `opendkim.conf` |
| `sendmail` local no firma | El envío por pickup como root no dispara el milter | Enviar por SMTP a `127.0.0.1:25` (swaks / smtplib) |
| `451 Service unavailable` | Milter falla al cargar la llave | Revisar log de opendkim; corregir permisos/RequireSafeKeys |
| Score bajo en mail-tester por IP | IP compartida con reputación ajena | Reforzar warm-up y categorización; considerar IP dedicada |

### Logs útiles

```bash
journalctl -t opendkim --no-pager -n 30 --since "5 minutes ago"
journalctl -t postfix/cleanup --no-pager -n 30
```
