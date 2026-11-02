"""Permet a Python localitzar la carpeta window com a part del projecte."""

from .builder import BaseWindow, FigureWindow, ImageWindow, MapWindow, SpecWindow
from .widgets import Widget

__all__ = [
    "BaseWindow",
    "FigureWindow",
    "ImageWindow",
    "MapWindow",
    "SpecWindow",
    "Widget",
]
