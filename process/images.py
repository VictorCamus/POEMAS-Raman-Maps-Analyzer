"""Funcions relacionades en les transformacions de les imatges."""
import io
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import TYPE_CHECKING, Literal, cast

import numpy as np
from win32 import win32clipboard

if TYPE_CHECKING:
    from collections.abc import Callable

    from matplotlib.figure import Figure
    from numpy.typing import NDArray


def zoom(xydata: tuple[float, float], button: Literal["up", "down"],
        old_lims: tuple[tuple[float, float], tuple[float, float]],
        base_size: tuple[float, float], base_scale: float = 1.1) -> tuple[tuple[float, float], tuple[float, float]]:
    """Transforma els límits d'una figura per a simular zoom.

    Parameters
    ----------
    xydata: tuple[float, float]
        Punt sobre el que es fa el zoom
    button: Literal["up", "down"]
        Indica si el zoom s'augmenta o es disminueix
    old_lims: tuple[tuple[float, float], tuple[float, float]]
        Límits actuals de la figura
    base_size: tuple[float, float]
        Mida base de la matriu.
    base_scale: float = 1.1
        Ràtio d'augment del zoom

    Returns
    -------
    xlim, ylim: tuple[tuple[float, float], tuple[float, float]]
        Nous límits de la figura

    """
    xdata, ydata = xydata
    xlim, ylim = old_lims

    match button:
        case "up":
            scale_factor = 1 / base_scale
        case "down":
            scale_factor = base_scale

    xsize = (xlim[1] - xlim[0]) * scale_factor
    ysize = (ylim[1] - ylim[0]) * scale_factor

    relx = (xlim[1] - xdata) / (xlim[1] - xlim[0])
    rely = (ylim[1] - ydata) / (ylim[1] - ylim[0])

    xlow = xdata - xsize * (1 - relx)
    xhigh = xdata + xsize * relx
    ylow = ydata - ysize * (1 - rely)
    yhigh = ydata + ysize * rely

    if 0 < xlow < xhigh < base_size[0] and 0 < ylow < yhigh < base_size[1]:
        xlim = (xlow, xhigh)
        ylim = (ylow, yhigh)

    return xlim, ylim


def on_motion(xydata: tuple[float, float], old_lims: tuple[tuple[float, float], tuple[float, float]],
              base_size: tuple[float, float],
              press: tuple[float, float]) -> tuple[tuple[float, float], tuple[float, float]]:
    """Transforma els límits d'una figura per a simular un desplaçament.

    Parameters
    ----------
    xydata: tuple[float, float]
        Punt de direcció del desplaçament
    old_lims: tuple[tuple[float, float], tuple[float, float]]
        Límits actuals de la figura
    base_size: tuple[float, float]
        Mida base de la matriu, o figura completa, sense fer cap zoom.__annotations__
    press: tuple[float, float]
        Punt clicat per a després fer el desplaçament

    Returns
    -------
    xlim, ylim: tuple[tuple[float, float], tuple[float, float]]
        Nous límits de la figura

    """
    xlim, ylim = old_lims
    xdata, ydata = xydata
    dx = xdata - press[0]
    dy = ydata - press[1]

    new_xlim = (xlim[0] - dx, xlim[1] - dx)
    new_ylim = (ylim[0] - dy, ylim[1] - dy)

    if new_xlim[0] >= 0 and new_xlim[1] <= base_size[0]:
        xlim = new_xlim
    if new_ylim[0] >= 0 and new_ylim[1] <= base_size[1]:
        ylim = new_ylim

    return xlim, ylim


def rotate_coords(data: list[tuple[int, int]], dim: tuple[int, int],
          rot: Literal[0, 1, 2, 3] = 0, *, flip: bool = False) -> list[tuple[int, int]]:
    """Transforma les coordenades d'una matriu mitjançant rotacions i voltejaments.

    Parameters
    ----------
    data: list[tuple[int, int]]
        Conjunt de punts que es transformen
    dim: tuple[int, int]
        Dimensions de la matriu sobre la qual s'aplica la transformació
    rot: Literal[0, 1, 2, 3] = 0
        Classe de rotació que es fa
    flip: bool = False
        Indica si la imatge s'ha de voltejar

    Returns
    -------
    transformed: list[tuple[int, int]], tuple[int, int]
        Conjunt de punts transformats

    """
    xdim, ydim = dim

    transformed: list[tuple[int, int]] = []

    for element in data:
        x, y = element
        match rot:
            case 0:
                pass
            case 1:
                x, y = y, ydim - 1 - x
            case 2:
                x, y = xdim - 1 - x, ydim - 1 - y
            case 3:
                x, y = xdim - 1 - y, x

        if flip:
            x = xdim - 1 - x

        transformed.append((x, y))

    return transformed


def transform_matrix[T: np.uint16 | np.uint32 | np.float32 | np.bool_](matrix: NDArray[T],
                    rot: Literal[0, 1, 2, 3] = 0, *, flip: bool = True) -> NDArray[T]:
    """Transforma una matriu mitjançant rotació i voltejament.

    Parameters
    ----------
    matrix: NDArray[T]
        Matriu 2D
    rot: Literal[0, 1, 2, 3] = 0
        Classe de rotació que es fa
    flip: bool = False
        Indica si la imatge s'ha de voltejar

    Returns
    -------
    matrix: NDArray[T]
        Matriu transformada

    """
    if rot != 0:
        matrix = np.rot90(matrix, k=rot)
    if flip:
        matrix = np.flip(matrix, axis=1)

    return matrix


def copy_figure(figure: Figure) -> None:
    """Copia una figura de matplotlib.Figure.

    Parameters
    ----------
    figure: Figure
        Objecte de la figura.

    """
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", bbox_inches="tight", transparent=True)

    if sys.platform == "win32":
        _copy_figure_windows(buffer)
    elif sys.platform.startswith("linux"):
        _copy_figure_linux(buffer)
    else:
        msg = f"Clipboard d'imatges no implementat per a {sys.platform}"
        raise NotImplementedError(msg)


def _copy_figure_windows(buffer: io.BytesIO) -> None:
    png_data = buffer.getvalue()

    empty_clipboard = cast("Callable[[], None]", win32clipboard.EmptyClipboard)
    set_clipboard_data = cast("Callable[[int, bytes], int]", win32clipboard.SetClipboardData)
    close_clipboard = cast("Callable[[], None]", win32clipboard.CloseClipboard)

    cf_png = win32clipboard.RegisterClipboardFormat("PNG")

    win32clipboard.OpenClipboard()
    try:
        empty_clipboard()
        set_clipboard_data(cf_png, png_data)
    finally:
        close_clipboard()


def _copy_figure_linux(buffer: io.BytesIO) -> None:
    wl_copy = shutil.which("wl-copy")

    if wl_copy is None:
        msg = "No s'ha trobat wl-copy"
        raise FileNotFoundError(msg)

    subprocess.run([wl_copy, "--type", "image/png"], input=buffer.getvalue(), check=True)  # ruff: ignore[subprocess-without-shell-equals-true]
