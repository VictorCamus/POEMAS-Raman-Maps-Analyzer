"""Funcions bàsiques generals i específiques del programa."""
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, getcontext
from typing import TYPE_CHECKING, Literal

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


def truncar_significatives(x: float, n: int, cap_a: Literal["amunt", "avall"] = "amunt") -> float:
    """Trunca un número cap amunt o avall amb tantes xifres significatives com s'indique.

    Returns
    -------
    truncat: float
        Valor final truncat.

    """
    if x == 0:
        return 0.0

    getcontext().prec = 50

    x_dec = Decimal(str(x))
    exponent = int(x_dec.copy_abs().log10().to_integral(rounding=ROUND_FLOOR))

    factor = Decimal(10) ** (exponent - n + 1)

    match cap_a:
        case "avall":
            truncat = (x_dec / factor).to_integral(rounding=ROUND_FLOOR) * factor
        case "amunt":
            truncat = (x_dec / factor).to_integral(rounding=ROUND_CEILING) * factor

    return float(truncat)


def find_nearest(array: NDArray[np.float32], values: float | list[float | int] | tuple[float | int, ...]
                | NDArray[np.float32]) -> tuple[int, ...]:
    """Càlculs dels índexos d'una llista numpy que s'acosten més a un valor concret.

    Troba l'índex o tupla d'índexos concrets d'un np.array corresponents als valors que s'acosten més
    a un cert valor o llista de valors.

    Parameters
    ----------
    array:
        Llista que conté el valor, l'índex del qual es busca
    values:
        Valors que es busquen

    Returns
    -------
    idx: tuple
        Tupla dels índexos que compleixen

    """
    values = np.atleast_1d(np.asarray(values, dtype=np.float32))

    return tuple(int(np.argmin(np.abs(array - value))) for value in values)


def set_lims(name: str, z: NDArray[np.float32]) -> tuple[list[float], NDArray[np.float32]]:
    """Càlcul de límits estàndard del programa.

    Els límits dels valors del mapa corresponent es calculen i es trunquen degudament. Com a criteri,
    es consideren els percentils 0.2 i 99.8 com a límits inferior i superior, respectivament, per a
    evitar el pes excessiu de valors extrems possibles.

    Parameters
    ----------
    name: str
        Nom de la classe d'arxiu en què es treballa
    z: NDArray[np.float32]
        Matriu de valors del mapa

    Returns
    -------
    lims: list[float]
        Valors inferior i superior.
    z: NDArray[np.float32]
        Nou valor del mapa en cas de ser un mapa de topografia.

    """
    if name == "Grain":
        return [0, 1], z

    vmin, vmax = np.nanpercentile(z, [0.2, 99.8])

    if name == "Height":
        z -= vmin
        vmax -= vmin
        vmin = 0

    # Truncament de valors
    vmin = truncar_significatives(x=vmin, n=3, cap_a="avall")
    vmax = truncar_significatives(x=vmax, n=3, cap_a="amunt")

    if vmin == vmax:  # Correcció per a evitar límits idèntics
        vmin -= 5
        vmax += 5

    return [vmin, vmax], z


def get_line(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    """Càlcul de la recta aproximada entre dos punts d'una graella.

    Torna una llista de tuples de punts 2D que es corresponen als valors que en una graella d'enters
    s'acostarien més a una recta, des de p1 fins a p2.

    Parameters
    ----------
    start: list[int]
        Punt extrem inicial de la recta.
    end: list[int]
        Punt extrem final de la recta.

    Returns
    -------
    points: list[tuple[int, int]]
        Llista de punts.

    """
    x1, y1 = start
    x2, y2 = end

    points: list[tuple[int, int]] = []
    issteep = abs(y2 - y1) > abs(x2 - x1)
    if issteep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2
    rev = False
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
        rev = True
    deltax = x2 - x1
    deltay = abs(y2 - y1)
    error = int(deltax / 2)
    y = y1

    ystep = 1 if y1 < y2 else -1

    for x in range(x1, x2 + 1):
        if issteep:
            points.append((y, x))
        else:
            points.append((x, y))
        error -= deltay
        if error < 0:
            y += ystep
            error += deltax
    # Reverse the list if the coordinates were reversed
    if rev:
        points.reverse()

    return points
