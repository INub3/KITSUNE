# app/mailer.py — motor de envío: sustitución de placeholders, SMTP por perfil y
# ejecución de la campaña en un hilo de fondo.
import smtplib, uuid, random, time, threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid

from app.db import query, execute


def render(s, **ctx):
    """Sustitución simple y segura de placeholders {{clave}} (no ejecuta Jinja)."""
    for k, v in ctx.items():
        s = s.replace("{{" + k + "}}", v if v is not None else "")
    return s


def connect(profile):
    smtp = smtplib.SMTP(profile["host"], profile["port"], timeout=30)
    if profile["use_tls"]:
        smtp.starttls()
    if profile["username"]:
        smtp.login(profile["username"], profile["password"] or "")
    return smtp


def build_message(profile, template, base_url, target, token):
    click = f"{base_url.rstrip('/')}/c/{token}"
    pixel = f"{base_url.rstrip('/')}/pixel?id={token}"
    ctx = dict(url=click, pixel=pixel, email=target["email"],
               first_name=target["first_name"] or "", last_name=target["last_name"] or "")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = render(template["subject"], **ctx)
    msg["From"] = formataddr((profile["from_name"], profile["from_email"]))
    msg["To"] = target["email"]
    msg["Message-ID"] = make_msgid(domain=profile["from_email"].split("@")[-1])
    msg.attach(MIMEText(render(template["text"], **ctx), "plain", "utf-8"))
    msg.attach(MIMEText(render(template["html"], **ctx), "html", "utf-8"))
    return msg


def send_test(profile, to_email):
    """Envía un correo de prueba para validar el perfil SMTP. Devuelve (ok, detalle)."""
    try:
        smtp = connect(profile)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Kitsune · prueba de perfil de envío"
        msg["From"] = formataddr((profile["from_name"], profile["from_email"]))
        msg["To"] = to_email
        msg.attach(MIMEText("Perfil de envío operativo. SPF/DKIM/DMARC deberían validar.",
                            "plain", "utf-8"))
        smtp.sendmail(profile["from_email"], to_email, msg.as_string())
        smtp.quit()
        return True, "Correo de prueba enviado."
    except Exception as e:
        return False, f"{e.__class__.__name__}: {e}"


def run_campaign(campaign_id):
    c = query("SELECT * FROM campaigns WHERE id=?", (campaign_id,), one=True)
    if not c:
        return
    profile  = query("SELECT * FROM profiles  WHERE id=?", (c["profile_id"],),  one=True)
    template = query("SELECT * FROM templates WHERE id=?", (c["template_id"],), one=True)
    targets  = query("SELECT * FROM targets   WHERE group_id=?", (c["group_id"],))
    if not (profile and template and targets):
        execute("UPDATE campaigns SET status='error' WHERE id=?", (campaign_id,))
        return

    execute("UPDATE campaigns SET status='running', launched_at=datetime('now') WHERE id=?",
            (campaign_id,))
    try:
        smtp = connect(profile)
    except Exception:
        execute("UPDATE campaigns SET status='error' WHERE id=?", (campaign_id,))
        return

    n = len(targets)
    for i, t in enumerate(targets):
        token = uuid.uuid4().hex
        # Fila de resultado ANTES de enviar; si falla, se elimina.
        execute("""INSERT INTO results(token,campaign_id,email,pretext,landing,sent_at)
                   VALUES(?,?,?,?,?,datetime('now'))""",
                (token, campaign_id, t["email"], template["name"], template["landing"]))
        try:
            msg = build_message(profile, template, c["base_url"], t, token)
            try:
                smtp.sendmail(profile["from_email"], t["email"], msg.as_string())
            except smtplib.SMTPServerDisconnected:
                smtp = connect(profile)
                smtp.sendmail(profile["from_email"], t["email"], msg.as_string())
        except Exception:
            execute("DELETE FROM results WHERE token=?", (token,))
        if i < n - 1:
            time.sleep(random.randint(c["delay_min"], c["delay_max"]))

    try:
        smtp.quit()
    except Exception:
        pass
    execute("UPDATE campaigns SET status='done' WHERE id=?", (campaign_id,))


def launch_async(campaign_id):
    """Lanza la campaña en un hilo demonio para no bloquear la petición web."""
    threading.Thread(target=run_campaign, args=(campaign_id,), daemon=True).start()
