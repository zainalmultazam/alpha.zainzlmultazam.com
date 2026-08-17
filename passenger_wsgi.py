import os
import sys

app_root = os.path.dirname(os.path.abspath(__file__))
if app_root not in sys.path:
    sys.path.insert(0, app_root)

venv_site_packages = "/home/pedulyco/virtualenv/public_html/alpha.zainalmultazam.com/3.11/lib/python3.11/site-packages"
if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)

from a2wsgi import ASGIMiddleware
from app.main import app

application = ASGIMiddleware(app)
