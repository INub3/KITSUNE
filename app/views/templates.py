# app/views/templates.py — plantillas de correo, editables en vivo + preview.
from flask import Blueprint, render_template, request, redirect, flash
import config
from app.db import query, execute
from app import mailer

bp = Blueprint("templates", __name__)

SAMPLE = dict(url="#", pixel="", email="usuario@cliente.com",
              first_name="Ana", last_name="García")


@bp.route("/templates")
def index():
    items = query("SELECT * FROM templates ORDER BY name")
    new = request.args.get("new") == "1"
    sel = request.args.get("id", "")
    current = None if new else (query("SELECT * FROM templates WHERE id=?", (sel,), one=True)
                                or (items[0] if items else None))
    return render_template("console/templates.html", active_tab="templates",
                           items=items, current=current, new=new, landings=config.LANDINGS)


@bp.route("/templates/save", methods=["POST"])
def save():
    f = request.form
    tid = f.get("id", "").strip()
    vals = (f.get("name", "").strip(), f.get("subject", "").strip(),
            f.get("landing", "microsoft").strip(), f.get("html", ""), f.get("text", ""))
    if not vals[0] or not vals[1]:
        flash("Nombre y asunto son obligatorios.", "err")
        return redirect("/templates")
    if tid:
        execute("UPDATE templates SET name=?,subject=?,landing=?,html=?,text=? WHERE id=?", vals + (tid,))
        flash("Plantilla actualizada.", "ok")
    else:
        tid = execute("INSERT INTO templates(name,subject,landing,html,text) VALUES(?,?,?,?,?)", vals)
        flash("Plantilla creada.", "ok")
    return redirect(f"/templates?id={tid}")


@bp.route("/templates/<int:tid>/delete", methods=["POST"])
def delete(tid):
    execute("DELETE FROM templates WHERE id=?", (tid,))
    flash("Plantilla eliminada.", "ok")
    return redirect("/templates")


@bp.route("/templates/<int:tid>/preview")
def preview(tid):
    t = query("SELECT * FROM templates WHERE id=?", (tid,), one=True)
    if not t:
        return "Sin datos", 404
    return mailer.render(t["html"], **SAMPLE)


@bp.route("/templates/preview", methods=["POST"])
def preview_live():
    # Preview del HTML tal como está en el editor (sin guardar).
    return mailer.render(request.form.get("html", ""), **SAMPLE)
