from pathlib import Path
import importlib

from .base import REGISTRE_GESTORS

class BuildMenu:
    def __init__(self, app):
        carpeta = Path(__file__).parent

        for file in sorted(carpeta.glob("menu*.py")):
            importlib.import_module(f"{__package__}.{file.stem}")

        for cls in sorted(REGISTRE_GESTORS, key=lambda c: getattr(c, "ordre", 100)):
            nom = cls.__name__.replace("Gestor", "").lower()

            gestor = cls(app)

            setattr(self, nom, gestor)
            gestor.registrar_menu(app.menu)

        app.root.config(menu=app.menu)