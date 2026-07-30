#!/usr/bin/env python3
# send.py — CLI opcional para operar campañas sin la consola web.
#   python3 send.py list            → lista campañas y su estado
#   python3 send.py run <id>        → ejecuta una campaña de forma SÍNCRONA
#
# La consola web (run.py) es la vía principal; este CLI es para automatización.
import argparse
from app.db import query, init_db
from app.mailer import run_campaign


def cmd_list():
    init_db()
    rows = query("SELECT id, name, status FROM campaigns ORDER BY created_at DESC")
    if not rows:
        print("Sin campañas. Crea una desde la consola web (pestaña Phishing).")
        return
    for r in rows:
        print(f"[{r['id']:>3}] {r['name']:<32} ({r['status']})")


def cmd_run(cid):
    init_db()
    c = query("SELECT * FROM campaigns WHERE id=?", (cid,), one=True)
    if not c:
        print(f"Campaña {cid} no existe.")
        return
    n = query("SELECT COUNT(*) c FROM targets WHERE group_id=?", (c["group_id"],), one=True)["c"]
    print(f"Ejecutando campaña [{cid}] «{c['name']}» · {n} objetivos (delay aleatorio)...")
    run_campaign(cid)
    print("Hecho. Revisa el dashboard.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="CLI de campañas Kitsune.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list", help="lista campañas")
    r = sub.add_parser("run", help="ejecuta una campaña síncronamente")
    r.add_argument("id", type=int)
    args = ap.parse_args()
    if args.cmd == "run":
        cmd_run(args.id)
    else:
        cmd_list()
