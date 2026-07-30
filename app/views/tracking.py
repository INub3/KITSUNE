# app/views/tracking.py — endpoints PÚBLICOS (proxeados por Nginx en :443).
# Registran actividad de los objetivos. NUNCA se capturan credenciales.
import base64
from flask import Blueprint, request, redirect, render_template, abort
import config
from app.db import get_db

bp = Blueprint("tracking", __name__)

PIXEL_GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")


def _client_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.headers.get("X-Real-IP", request.remote_addr)


@bp.route("/pixel")
def pixel():
    token = request.args.get("id", "")
    con = get_db()
    con.execute("UPDATE results SET opened_at=datetime('now') WHERE token=? AND opened_at IS NULL", (token,))
    con.commit(); con.close()
    return PIXEL_GIF, 200, {"Content-Type": "image/gif", "Cache-Control": "no-store"}


@bp.route("/c/<token>")
def click(token):
    con = get_db()
    row = con.execute("SELECT landing FROM results WHERE token=?", (token,)).fetchone()
    con.execute("""UPDATE results SET clicked_at=datetime('now'), ip=?, user_agent=?
                   WHERE token=? AND clicked_at IS NULL""",
                (_client_ip(), request.headers.get("User-Agent", ""), token))
    con.commit(); con.close()
    landing = row["landing"] if row and row["landing"] in config.LANDINGS else "microsoft"
    return redirect(f"/l/{landing}?id={token}")


@bp.route("/l/<page>")
def landing(page):
    if page not in config.LANDINGS:
        abort(404)
    token = request.args.get("id", "")
    # El correo ya se conoce por el token; se pasa solo para prerellenar la vista.
    con = get_db()
    row = con.execute("SELECT email FROM results WHERE token=?", (token,)).fetchone()
    con.close()
    email = row["email"] if row else ""
    return render_template(f"landings/{page}.html", token=token, email=email, prefill=email)


@bp.route("/s/<token>", methods=["POST"])
def submit(token):
    # Solo se registra la interacción. No se leen request.form / credenciales.
    con = get_db()
    row = con.execute("SELECT c.base_url FROM results r JOIN campaigns c ON c.id=r.campaign_id "
                      "WHERE r.token=?", (token,)).fetchone()
    con.execute("""UPDATE results SET submitted_at=datetime('now'), ip=?, user_agent=?
                   WHERE token=? AND submitted_at IS NULL""",
                (_client_ip(), request.headers.get("User-Agent", ""), token))
    con.commit(); con.close()
    base = row["base_url"] if row else config.DEFAULT_BASE_URL
    return redirect(config.redirect_after(base))


@bp.route("/aviso")
def aviso():
    return render_template("landings/awareness.html")
