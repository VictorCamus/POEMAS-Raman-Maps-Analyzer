from pathlib import Path
import importlib

from .base import REGISTRE_GESTORS

def _upload_modules(): # Carrega els mòduls de la carpeta actual que comencen per "menu" i els importa
    carpeta = Path(__file__).parent

    for file in carpeta.glob("menu*.py"):
        if file.name == "__init__.py": continue

        nom_modul = file.stem  # sense .py
        importlib.import_module(f"{__package__}.{nom_modul}")
        
class BuildMenu:
    def __init__(self, app):
        _upload_modules()
        for cls in sorted(REGISTRE_GESTORS, key=lambda c: getattr(c, "ordre", 100)):
            nom = cls.__name__.replace("Gestor", "").lower()

            gestor = cls(app,     
                get_current=lambda: app.current_file,
                set_current=lambda value: setattr(app, "current_file", value)
            )

            setattr(self, nom, gestor)
            gestor.registrar_menu(app.menu)

        app.root.config(menu=app.menu)