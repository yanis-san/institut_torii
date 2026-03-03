import os
import sys

# Ajouter le projet au PYTHONPATH
sys.path.insert(0, os.path.dirname(__file__))

# Définir les settings (Production)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

# Charger l'application WSGI
from config.wsgi import application
