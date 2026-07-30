# app/pretexts.py — datos SEMILLA que se cargan en la BD en el primer arranque.
#
# Las plantillas usan placeholders literales que el motor de envío sustituye por objetivo:
#   {{url}}  {{pixel}}  {{email}}  {{first_name}}  {{last_name}}
# A partir del primer arranque se editan EN VIVO desde la pestaña "Plantillas"; esto
# es solo el contenido inicial.
import config


def _wrap(inner):
    return (
        '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0"></head>'
        '<body style="margin:0;background:#f4f5f7;font-family:Segoe UI,Arial,sans-serif;color:#2b2b2b;">'
        '<div style="max-width:600px;margin:24px auto;background:#fff;border-radius:8px;'
        'overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);">'
        '<div style="background:#1f3a5f;padding:18px 28px;">'
        '<span style="color:#fff;font-size:18px;font-weight:600;">IST Américas</span></div>'
        '<div style="padding:28px;line-height:1.6;font-size:15px;">' + inner + '</div>'
        '<div style="padding:16px 28px;background:#fafbfc;border-top:1px solid #eee;'
        'font-size:12px;color:#8a8a8a;">Este mensaje fue enviado automáticamente. No responder.</div>'
        '</div>'
        '<img src="{{pixel}}" width="1" height="1" style="display:none;"></body></html>'
    )


def _btn(label):
    return ('<div style="text-align:center;margin:26px 0;">'
            '<a href="{{url}}" style="background:#1f3a5f;color:#fff;text-decoration:none;'
            'padding:12px 28px;border-radius:6px;font-weight:600;display:inline-block;">'
            + label + '</a></div>')


DEFAULT_PROFILE = {
    "name": "SMTP local", "host": "localhost",
    "port": 25, "use_tls": 0, "username": None, "password": None,
    "from_name": config.DEFAULT_FROM_NAME, "from_email": config.DEFAULT_FROM_EMAIL,
}

DEFAULT_GROUP = "General"

DEFAULT_TEMPLATES = [
    {
        "name": "Alerta de seguridad",
        "subject": "Actividad inusual detectada en tu cuenta",
        "landing": "microsoft",
        "text": ("Estimado usuario,\n\n"
                 "El equipo de seguridad detectó un inicio de sesión inusual en tu cuenta:\n"
                 "  Usuario: {{email}}\n  Dispositivo: Windows - Edge\n  Ubicación: Moscú, Rusia\n\n"
                 "Si no reconoces este acceso, revisa y confirma la actividad:\n{{url}}\n\n"
                 "Equipo de Seguridad TI\nIST Américas"),
        "html": _wrap(
            '<p>Estimado usuario,</p>'
            '<p>El equipo de seguridad detectó un <b>inicio de sesión inusual</b> en tu cuenta:</p>'
            '<p style="background:#f6f8fa;border-left:3px solid #1f3a5f;padding:10px 14px;">'
            'Usuario: {{email}}<br>Dispositivo: Windows - Edge<br>Ubicación: Moscú, Rusia</p>'
            '<p>Si no reconoces este acceso, revisa y confirma la actividad de inmediato.</p>'
            + _btn("Revisar actividad") +
            '<p style="font-size:13px;color:#777;">Equipo de Seguridad TI · IST Américas</p>'),
    },
    {
        "name": "Documento RR.HH.",
        "subject": "Documento pendiente de revisión - RR.HH.",
        "landing": "sharepoint",
        "text": ("Buenas tardes,\n\n"
                 "El área de Recursos Humanos ha compartido un documento que requiere tu "
                 "revisión antes del cierre de mes:\n{{url}}\n\nGracias,\nRecursos Humanos\nIST Américas"),
        "html": _wrap(
            '<p>Buenas tardes,</p>'
            '<p>El área de <b>Recursos Humanos</b> ha compartido un documento que requiere tu '
            'revisión antes del cierre de mes.</p>'
            + _btn("Ver documento") +
            '<p style="font-size:13px;color:#777;">Recursos Humanos · IST Américas</p>'),
    },
    {
        "name": "Expiración de VPN",
        "subject": "Tu contraseña VPN vence pronto",
        "landing": "microsoft",
        "text": ("Estimado colaborador,\n\n"
                 "Tu contraseña de acceso VPN vence en 24 horas. Para evitar la interrupción "
                 "del servicio, actualízala en el portal corporativo:\n{{url}}\n\nSoporte TI\nIST Américas"),
        "html": _wrap(
            '<p>Estimado colaborador,</p>'
            '<p>Tu contraseña de acceso <b>VPN vence en 24 horas</b>. Para evitar la '
            'interrupción del servicio, actualízala a través del portal corporativo.</p>'
            + _btn("Actualizar contraseña") +
            '<p style="font-size:13px;color:#777;">Soporte TI · IST Américas</p>'),
    },
]
