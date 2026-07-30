# app/views/campaigns.py — creación y lanzamiento de campañas (pestaña Phishing).
from flask import Blueprint, render_template, request, redirect, flash
import config
from app.db import query, execute
from app import mailer

bp = Blueprint("campaigns", __name__)


@bp.route("/campaigns")
def index():
    campaigns = query("""SELECT c.*, p.name profile_name, t.name template_name, g.name group_name,
                         (SELECT COUNT(*) FROM results r WHERE r.campaign_id=c.id) sent,
                         (SELECT COUNT(*) FROM results r WHERE r.campaign_id=c.id AND r.submitted_at) subs
                         FROM campaigns c
                         LEFT JOIN profiles  p ON p.id=c.profile_id
                         LEFT JOIN templates t ON t.id=c.template_id
                         LEFT JOIN groups    g ON g.id=c.group_id
                         ORDER BY c.created_at DESC""")
    return render_template("console/campaigns.html", active_tab="campaigns",
                           campaigns=campaigns,
                           profiles=query("SELECT id,name FROM profiles ORDER BY name"),
                           templates=query("SELECT id,name FROM templates ORDER BY name"),
                           groups=query("""SELECT g.id,g.name,
                                           (SELECT COUNT(*) FROM targets t WHERE t.group_id=g.id) n
                                           FROM groups g ORDER BY g.name"""),
                           default_base=config.DEFAULT_BASE_URL,
                           dmin=config.DELAY_MIN, dmax=config.DELAY_MAX)


@bp.route("/campaigns/save", methods=["POST"])
def save():
    f = request.form
    name = f.get("name", "").strip()
    if not (name and f.get("profile_id") and f.get("template_id") and f.get("group_id")):
        flash("Nombre, perfil, plantilla y grupo son obligatorios.", "err")
        return redirect("/campaigns")
    cid = execute("""INSERT INTO campaigns(name,profile_id,template_id,group_id,base_url,delay_min,delay_max)
                     VALUES(?,?,?,?,?,?,?)""",
                  (name, f.get("profile_id"), f.get("template_id"), f.get("group_id"),
                   f.get("base_url", config.DEFAULT_BASE_URL).strip() or config.DEFAULT_BASE_URL,
                   int(f.get("delay_min") or config.DELAY_MIN),
                   int(f.get("delay_max") or config.DELAY_MAX)))
    flash("Campaña creada como borrador. Revisa y lánzala.", "ok")
    return redirect("/campaigns")


@bp.route("/campaigns/<int:cid>/launch", methods=["POST"])
def launch(cid):
    c = query("SELECT * FROM campaigns WHERE id=?", (cid,), one=True)
    if not c:
        flash("Campaña no encontrada.", "err")
        return redirect("/campaigns")
    if c["status"] == "running":
        flash("La campaña ya está en ejecución.", "err")
        return redirect("/campaigns")
    n = query("SELECT COUNT(*) c FROM targets WHERE group_id=?", (c["group_id"],), one=True)["c"]
    if not n:
        flash("El grupo no tiene objetivos.", "err")
        return redirect("/campaigns")
    mailer.launch_async(cid)
    flash(f"Campaña lanzada · {n} objetivos en cola (con delay aleatorio).", "ok")
    return redirect("/campaigns")


@bp.route("/campaigns/<int:cid>/delete", methods=["POST"])
def delete(cid):
    execute("DELETE FROM campaigns WHERE id=?", (cid,))
    flash("Campaña eliminada (con sus resultados).", "ok")
    return redirect("/campaigns")
