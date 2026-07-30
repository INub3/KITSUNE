# config.py — configuración base de Kitsune.
#
# Todo es INDEPENDIENTE de la ruta de instalación: las rutas de datos se calculan
# a partir de la ubicación de este archivo, así el proyecto corre desde cualquier
# directorio. Cualquier valor admite override por variable de entorno (prefijo KITSUNE_).
import os

# Raíz del proyecto = carpeta donde vive este archivo.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("KITSUNE_DATA_DIR", os.path.join(BASE_DIR, "data"))
DB       = os.environ.get("KITSUNE_DB", os.path.join(DATA_DIR, "kitsune.db"))

# Clave de sesión (flash messages). Cámbiala en producción vía KITSUNE_SECRET.
SECRET_KEY = os.environ.get("KITSUNE_SECRET", "kitsune-dev-secret-change-me")

# Servicio web local de la consola (admin) — exponer SOLO por túnel SSH.
HOST = os.environ.get("KITSUNE_HOST", "127.0.0.1")
PORT = int(os.environ.get("KITSUNE_PORT", "5000"))

# Valores por defecto para nuevos perfiles / campañas.
DEFAULT_BASE_URL   = os.environ.get("KITSUNE_BASE_URL",   "https://soporteclave.com")
DEFAULT_FROM_EMAIL = os.environ.get("KITSUNE_FROM_EMAIL", "soporte@soporteclave.com")
DEFAULT_FROM_NAME  = os.environ.get("KITSUNE_FROM_NAME",  "Soporte TI")
DELAY_MIN = int(os.environ.get("KITSUNE_DELAY_MIN", "45"))
DELAY_MAX = int(os.environ.get("KITSUNE_DELAY_MAX", "120"))

# Landings disponibles (archivos en app/templates/<name>.html servidos a los objetivos).
LANDINGS = ("teams", "microsoft", "google", "sharepoint", "zoom")

def redirect_after(base_url):
    """Página de concientización a la que se redirige tras interactuar."""
    return f"{base_url.rstrip('/')}/aviso"
