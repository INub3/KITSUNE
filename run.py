#!/usr/bin/env python3
# run.py — arranca la consola web local de Kitsune.
#   python3 run.py
# Sirve en KITSUNE_HOST:KITSUNE_PORT (127.0.0.1:5000 por defecto).
# Exponer SOLO por túnel SSH; Nginx no debe proxear las rutas de administración.
from app import create_app
import config

app = create_app()

if __name__ == "__main__":
    print(f"Kitsune · consola en http://{config.HOST}:{config.PORT}  (solo túnel SSH)")
    app.run(host=config.HOST, port=config.PORT, debug=False)
