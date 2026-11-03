"""Configuracions dels gràfics."""
from typing import TYPE_CHECKING, cast

import numpy as np
from matplotlib import ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import TABLEAU_COLORS
from matplotlib.figure import Figure

if TYPE_CHECKING:
    from tkinter import Toplevel
    from tkinter.ttk import Frame

    from matplotlib.axes import Axes
    from numpy.typing import NDArray

    from classes.protocols import TkCanvasProtocol


PLOT_COLORS: list[str] = [
            "red",
            "blue",
            "green",
            "orange",
            "yellow",
            "cyan",
            "magenta",
            "black",
            "white",
            "purple",
            "lime",
            "turquoise",
            "navy",
        ]

PEAK_COLORS = cast("list[str]", list(TABLEAU_COLORS.values())[1:])


def base_plot(xtitle: str = "", ytitle: str = "", dim: tuple[float, float] = (6, 4),
              font: str = "Consolas") -> tuple[Figure, Axes]:
    """Configuració estàndard dels gràfics.

    Parameters
    ----------
    xtitle: str = ""
        Títol de l'eix X.
    ytitle: str = ""
        Títol de l'eix Y.
    dim: tuple[float, float] = (6, 4)
        Dimensions de la figura.
    font: str = "Consolas"
        Tipografia dels objectes de la figura.

    Returns
    -------
    fig: Figure
        Objecte de la figura.
    ax: Axes
        Objecte dels eixos.

    """
    fig = Figure(figsize=dim, tight_layout=True)
    ax = fig.add_subplot(111)

    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(2))
    ax.tick_params(axis="x", which="minor", direction="in")
    ax.tick_params(axis="x", labelsize=18, direction="in")

    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
    ax.tick_params(axis="y", which="minor", direction="in")
    ax.tick_params(axis="y", labelsize=18, direction="in")

    ax.locator_params(axis="both", nbins=5)

    ax.set_xlabel(xtitle, fontsize=22, labelpad=10, fontname=font)
    ax.set_ylabel(ytitle, fontsize=22, labelpad=10, fontname=font)

    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(font)
        label.set_fontsize(12)

    ax.set_axisbelow(True)

    fig.tight_layout()

    return fig, ax


def get_verts(xdata: NDArray[np.float32], ydata: NDArray[np.float32], bkg: NDArray[np.float32]) -> NDArray[np.float32]:
    """Obté els polígons que simulen l'àrea pintada davall d'una corba.

    xdata: NDArray[np.float32]
        Dades del rang.
    ydata: NDArray[np.float32]
        Valors de la funció
    bkg: NDArray[np.float32])
        Valor del fons de la funció

    Returns
    -------
    verts: NDArray[np.float32]
        Vector de valors que conté la forma dels polígons.

    """
    return np.asarray(np.column_stack((np.r_[xdata, xdata[::-1]], np.r_[ydata + bkg, bkg[::-1]])), dtype=np.float32)


def create_canvas(figure: Figure, frame: Frame | Toplevel) -> TkCanvasProtocol:
    """Crea el canvas a partir d'una figura i el connecta al requadre visual corresponent.

    Parameters
    ----------
    figure: Figure
        Figura de Matplotlib
    frame: Frame
        Requadre de tkinter.ttk

    Returns
    -------
    canvas: TkCanvasProtocol
        Objecte canvas

    """
    return cast("TkCanvasProtocol", FigureCanvasTkAgg(figure, frame))
