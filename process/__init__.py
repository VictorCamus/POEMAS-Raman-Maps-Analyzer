from pathlib import Path
import importlib

__all__ = []

carpeta = Path(__file__).parent

for file in carpeta.glob("*.py"):
    if file.stem == "__init__":
        continue

    nom = file.stem

    module = importlib.import_module(f"{__name__}.{nom}")

    globals()[nom] = module
    __all__.append(nom)
