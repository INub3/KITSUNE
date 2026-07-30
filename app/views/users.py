# app/views/users.py — objetivos ("usuarios") organizados en grupos.
import csv, io
from flask import Blueprint, render_template, request, redirect, flash
from app.db import query, execute

bp = Blueprint("users", __name__)


@bp.route("/users")
def index():
    groups = query("""SELECT g.*, (SELECT COUNT(*) FROM targets t WHERE t.group_id=g.id) n
                      FROM groups g ORDER BY g.name""")
    sel = request.args.get("group", "")
    current = query("SELECT * FROM groups WHERE id=?", (sel,), one=True) or (groups[0] if groups else None)
    targets = query("SELECT * FROM targets WHERE group_id=? ORDER BY email", (current["id"],)) if current else []
    return render_template("console/users.html", active_tab="users",
                           groups=groups, current=current, targets=targets)


@bp.route("/users/group/save", methods=["POST"])
def group_save():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Nombre de grupo requerido.", "err")
        return redirect("/users")
    try:
        gid = execute("INSERT INTO groups(name) VALUES(?)", (name,))
        flash("Grupo creado.", "ok")
        return redirect(f"/users?group={gid}")
    except Exception:
        flash("Ese grupo ya existe.", "err")
        return redirect("/users")


@bp.route("/users/group/<int:gid>/delete", methods=["POST"])
def group_delete(gid):
    execute("DELETE FROM groups WHERE id=?", (gid,))
    flash("Grupo eliminado.", "ok")
    return redirect("/users")


@bp.route("/users/<int:gid>/add", methods=["POST"])
def add_target(gid):
    f = request.form
    email = f.get("email", "").strip()
    if not email or "@" not in email:
        flash("Correo inválido.", "err")
        return redirect(f"/users?group={gid}")
    try:
        execute("""INSERT INTO targets(group_id,email,first_name,last_name,position)
                   VALUES(?,?,?,?,?)""",
                (gid, email, f.get("first_name", "").strip(),
                 f.get("last_name", "").strip(), f.get("position", "").strip()))
        flash("Objetivo agregado.", "ok")
    except Exception:
        flash("Ese correo ya está en el grupo.", "err")
    return redirect(f"/users?group={gid}")


@bp.route("/users/<int:gid>/import", methods=["POST"])
def import_csv(gid):
    # Pega CSV con header 'email' (opcional first_name,last_name,position).
    raw = request.form.get("csv", "")
    added = skipped = 0
    reader = csv.DictReader(io.StringIO(raw))
    for row in reader:
        email = (row.get("email") or "").strip()
        if not email or "@" not in email:
            skipped += 1; continue
        try:
            execute("""INSERT INTO targets(group_id,email,first_name,last_name,position)
                       VALUES(?,?,?,?,?)""",
                    (gid, email, (row.get("first_name") or "").strip(),
                     (row.get("last_name") or "").strip(), (row.get("position") or "").strip()))
            added += 1
        except Exception:
            skipped += 1
    flash(f"Importados {added}, omitidos {skipped}.", "ok")
    return redirect(f"/users?group={gid}")


@bp.route("/users/target/<int:tid>/delete", methods=["POST"])
def target_delete(tid):
    row = query("SELECT group_id FROM targets WHERE id=?", (tid,), one=True)
    execute("DELETE FROM targets WHERE id=?", (tid,))
    gid = row["group_id"] if row else ""
    return redirect(f"/users?group={gid}")
