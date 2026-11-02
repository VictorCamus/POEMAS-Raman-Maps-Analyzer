"""Registra els menús existents."""
from typing import TYPE_CHECKING

from .menu_corr import GestorCorr
from .menu_file import GestorFile
from .menu_images import GestorImages
from .menu_maps import GestorMaps
from .menu_profiles import GestorProfiles
from .menu_spec import GestorSpec
from .menu_stats import GestorStats

if TYPE_CHECKING:
    from POEMAS import Aplicacio as App

    from .base import BaseMenu

MENUS: dict[str, type[BaseMenu]] = {
    "Arxiu": GestorFile,
    "Imatges": GestorImages,
    "Correcció": GestorCorr,
    "Perfils": GestorProfiles,
    "Estadística": GestorStats,
    "Mapes": GestorMaps,
    "Espectre": GestorSpec,
}


class BuildMenu:
    """Classe que construeix el menú i en guarda les referències."""

    def __init__(self, app: App) -> None:
        """Afig els gestors al menú.

        Parameters
        ----------
        app: App
            Aplicació base del programa

        """
        for nom, cls in MENUS.items():
            gestor = cls(app)

            setattr(self, nom, gestor)
            gestor._add_menu(app.menu)

        app.root.config(menu=app.menu)
