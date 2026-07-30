# app/views/dashboard.py — panel de resultados (solo túnel SSH).
import io, csv
from flask import Blueprint, render_template, request, Response
from app.db import query

bp = Blueprint("dashboard", __name__)


def _breakdown(rows, key):
    agg = {}
    for r in rows:
        a = agg.setdefault(r[key] or "—", {"total": 0, "opened": 0, "clicked": 0, "submitted": 0})
        a["total"] += 1
        if r["opened_at"]:    a["opened"] += 1
        if r["clicked_at"]:   a["clicked"] += 1
        if r["submitted_at"]: a["submitted"] += 1
    return dict(sorted(agg.items(), key=lambda kv: kv[1]["total"], reverse=True))


@bp.route("/dashboard")
def index():
    campaigns = query("SELECT id, name, status FROM campaigns ORDER BY created_at DESC")
    sel = request.args.get("campaign", "").strip()

    if sel:
        rows = query("""SELECT email, pretext, landing, sent_at, opened_at, clicked_at,
                        submitted_at, ip, user_agent FROM results WHERE campaign_id=?
                        ORDER BY COALESCE(submitted_at,clicked_at,opened_at,sent_at) DESC""", (sel,))
    else:
        rows = query("""SELECT email, pretext, landing, sent_at, opened_at, clicked_at,
                        submitted_at, ip, user_agent FROM results
                        ORDER BY COALESCE(submitted_at,clicked_at,opened_at,sent_at) DESC""")

    total     = len(rows)
    opened    = sum(1 for r in rows if r["opened_at"])
    clicked   = sum(1 for r in rows if r["clicked_at"])
    submitted = sum(1 for r in rows if r["submitted_at"])
    pct = lambda n: round(100 * n / total, 1) if total else 0.0
    stats = {"total": total, "opened": opened, "clicked": clicked, "submitted": submitted,
             "pending": total - opened,
             "open_rate": pct(opened), "click_rate": pct(clicked), "submit_rate": pct(submitted)}

    return render_template("console/dashboard.html", active_tab="dashboard", rows=rows, stats=stats,
                           by_pretext=_breakdown(rows, "pretext"),
                           by_landing=_breakdown(rows, "landing"),
                           campaigns=campaigns, selected=sel)


@bp.route("/dashboard/export.csv")
def export_csv():
    sel = request.args.get("campaign", "").strip()
    cols = ["token", "campaign_id", "email", "pretext", "landing", "sent_at",
            "opened_at", "clicked_at", "submitted_at", "ip", "user_agent"]
    if sel:
        rows = query(f"SELECT {','.join(cols)} FROM results WHERE campaign_id=? ORDER BY sent_at DESC", (sel,))
    else:
        rows = query(f"SELECT {','.join(cols)} FROM results ORDER BY sent_at DESC")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for r in rows:
        w.writerow([r[c] for c in cols])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=kitsune_report.csv"})
