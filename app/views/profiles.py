# app/views/profiles.py — perfiles de envío SMTP (múltiples, guardables).
from flask import Blueprint, render_template, request, redirect, flash
import config
from app.db import query, execute
from app import mailer

bp = Blueprint("profiles", __name__)


@bp.route("/profiles")
def index():
    profiles = query("SELECT * FROM profiles ORDER BY name")
    new = request.args.get("new") == "1"
    sel = request.args.get("id", "")
    current = None if new else (query("SELECT * FROM profiles WHERE id=?", (sel,), one=True)
                                or (profiles[0] if profiles else None))
    return render_template("console/profiles.html", active_tab="profiles",
                           profiles=profiles, current=current, new=new,
                           defaults={"from_name": config.DEFAULT_FROM_NAME,
                                     "from_email": config.DEFAULT_FROM_EMAIL})


@bp.route("/profiles/save", methods=["POST"])
def save():
    f = request.form
    pid = f.get("id", "").strip()
    vals = (f.get("name", "").strip(), f.get("host", "localhost").strip(),
            int(f.get("port") or 25), 1 if f.get("use_tls") else 0,
            f.get("username", "").strip() or None, f.get("password", "").strip() or None,
            f.get("from_name", "").strip(), f.get("from_email", "").strip())
    if not vals[0] or not vals[7]:
        flash("Nombre y correo de origen son obligatorios.", "err")
        return redirect("/profiles")
    if pid:
        execute("""UPDATE profiles SET name=?,host=?,port=?,use_tls=?,username=?,password=?,
                   from_name=?,from_email=? WHERE id=?""", vals + (pid,))
        flash("Perfil actualizado.", "ok")
    else:
        pid = execute("""INSERT INTO profiles(name,host,port,use_tls,username,password,from_name,from_email)
                         VALUES(?,?,?,?,?,?,?,?)""", vals)
        flash("Perfil creado.", "ok")
    return redirect(f"/profiles?id={pid}")


@bp.route("/profiles/<int:pid>/delete", methods=["POST"])
def delete(pid):
    execute("DELETE FROM profiles WHERE id=?", (pid,))
    flash("Perfil eliminado.", "ok")
    return redirect("/profiles")


@bp.route("/profiles/<int:pid>/test", methods=["POST"])
def test(pid):
    profile = query("SELECT * FROM profiles WHERE id=?", (pid,), one=True)
    to = request.form.get("to", "").strip()
    if not profile or not to:
        flash("Falta el destinatario de prueba.", "err")
    else:
        ok, detail = mailer.send_test(profile, to)
        flash(detail, "ok" if ok else "err")
    return redirect(f"/profiles?id={pid}")
