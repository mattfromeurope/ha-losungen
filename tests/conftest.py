"""Gemeinsame pytest-Konfiguration für alle Tests.

conftest.py wird von pytest automatisch vor den Tests geladen. Hier wird das
Repository-Root in sys.path eingetragen, damit `import custom_components...`
funktioniert (custom_components hat keine __init__.py, Python behandelt es als
sogenanntes Namespace-Package).
"""

import sys
from pathlib import Path

# Elternverzeichnis des tests/-Ordners = Repository-Root auf die Import-Pfad-Liste.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
