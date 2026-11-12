"""Funcions relacionades amb els càlculs estadístics i gràfics d'histogrames i boxplot."""

from typing import TYPE_CHECKING, cast

import numpy as np
from matplotlib.ticker import AutoLocator, ScalarFormatter

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.collections import FillBetweenPolyCollection
    from matplotlib.patches import Patch
    from numpy.typing import NDArray


def hist(ax: Axes, data: NDArray[np.float32], lims: list[float], xlabel: str = "",
         nbins: int = 80, color: str = "blue")\
         -> tuple[FillBetweenPolyCollection, tuple[NDArray[np.float32], NDArray[np.float32]], tuple[float, float]]:
    """Representa un histograma sobre un eix de Matplotlib.

    Calcula l'histograma de les dades dins dels límits indicats i el representa mitjançant
    'fill_between', amb els intervals de l'histograma centrats en els seus corresponents valors.

    Parameters
    ----------
    ax: Axes
        Eix de Matplotlib.
    data: NDArray[np.float32]
        Matriu de dades que es representaran.
    lims: list[float]
        Límits inferior i superior de l'interval representat.
    xlabel: str
        Etiqueta de l'eix X.
    nbins: int
        Nombre d'intervals de l'histograma.
    color: str
        Color de l'histograma.

    Returns
    -------
    bars: FillBetweenPolyCollection
        La col·lecció de Matplotlib associada a 'fill_between'.
    bins, values:
        Tupla amb els vectors dels bins i dels valors de l'histograma.
    bin_min, bin_max:
        Una tupla amb el valor mínim i màxim dels bins.

    """
    vmin, vmax = lims
    ample = (vmax - vmin) / nbins

    bins, values = _make_histogram(data, nbins, lims=(vmin, vmax))
    bin_min = float(np.min(bins))
    bin_max = float(np.max(bins))

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel="")
    ax.set_yticks([])
    bars = ax.fill_between(bins, values, step="mid", alpha=1, color=color)
    ax.axis((float(bin_min - ample / 2), float(bin_max + ample / 2), float(0), float(np.max(values) * 1.1)))
    ax.xaxis.set_major_locator(AutoLocator())
    ax.xaxis.set_major_formatter(ScalarFormatter())

    return bars, (bins, values), (bin_min, bin_max)


def boxplot(ax: Axes, data: NDArray[np.float32], lims: list[float], name: str,
            ylabel: str = "", color: str = "blue") -> dict[str, list[Patch]]:
    """Representa un diagrama de caixa sobre un eix de Matplotlib.

    El diagrama mostra la distribució de les dades dins dels límits indicats.
    Els valors atípics no es representen i els bigots es calculen entre els percentils 5 i 95.
    També es mostra la mitjana mitjançant una línia.

    Parameters
    ----------
    ax: Axes
        Eix de Matplotlib.
    data: NDArray[np.float32]
        Matriu de dades que es representaran.
    lims: list[float]
        Límits inferior i superior de l'interval representat.
    name: str
        Etiqueta associada al diagrama de caixa en l'eix X.
    ylabel: str
        Etiqueta de l'eix Y.
    color: str
        Color utilitzat per a omplir la caixa.

    Returns
    -------
    boxplot: dict[str, list[Patch]]
        Diccionari amb els diferents elements gràfics de 'Axes.boxplot`.

    """
    vmin, vmax = lims
    ax.set_xlabel("")
    ax.set_ylabel(ylabel)
    ax.set_xticklabels([])
    ax.set_xlim((0.5, 1.5))
    ax.set_ylim((vmin, vmax))

    boxplot = cast("dict[str, list[Patch]]",
        ax.boxplot(
            x=data,
            patch_artist=True,
            tick_labels=[name],
            sym="",
            meanline=True,
            showmeans=True,
            whis=(5, 95),
            boxprops={"facecolor": color},
            medianprops={"color": "black"},
            meanprops={"color": "black"},
        ),
    )

    ax.yaxis.set_major_locator(AutoLocator())

    return boxplot


def remove_boxplot(boxplot: dict[str, list[Patch]]) -> None:
    """S'eliminen el objectes del boxplot del gràfic corresponent.

    Parameters
    ----------
    boxplot: dict[str, list[Patch]]
        Diccionari que conté els elements del boxplot.

    """
    for element in boxplot.values():
        for patch in element:
            patch.remove()


def get_r2(y: NDArray[np.float32], yfit: NDArray[np.float32]) -> float:
    """Calcula la correlació r2 entre un conjunt de dades i l'ajust corresponent.

    Parameters
    ----------
    y: NDArray[np.float32]
        Conjunt de dades
    yfit: NDArray[np.float32]
        Dades de l'ajust

    Returns
    -------
    r2: float
        Paràmetre de correlació

    """
    ss_res = float(np.sum((y - yfit) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))

    return 1 - ss_res / ss_tot


def _make_histogram(z: NDArray[np.float32], nbins: int, lims: tuple[float, float])\
                   -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    """Càlcul dels valors típics d'un histograma.

    Parameters
    ----------
    z: NDArray[np.float32]
        La matriu sobre què es calcula l'histograma.
    nbins: int
        Nombre d'intervals de l'histograma
    lims: tuple[float, float]
        Límits de l'histograma

    Returns
    -------
    bins -> NDArray[np.float32]:
        Valors centrats dels intervals
    values -> NDArray[np.float32]:
        Valor de cada interval

    """
    z = z[np.isfinite(z)]

    init_values, init_bins = np.histogram(z, range=lims, bins=nbins)
    values = np.array(init_values, dtype=np.float32)
    bins = np.array((init_bins[:-1] + init_bins[1:]) / 2, dtype=np.float32)
    values /= np.sum(values)

    return bins, np.array(values, dtype=np.float32)
