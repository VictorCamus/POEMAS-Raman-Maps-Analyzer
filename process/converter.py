"""Funcions de conversió d'unitats i de coordenades/píxels del programa."""

from math import floor
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

HC: NDArray[np.float32] = np.array(1239.84197, dtype=np.float32)  # Planck constant · c (eV·nm)
HC_CM: np.float32 = np.float32(1e7 / HC)  # 8065.54429 cm⁻¹/eV


def nm_to_raman(array: NDArray[np.float32], laser_nm: float) -> NDArray[np.float32]:
    """Converteix de nm a cm-1.

    Parameters
    ----------
    array: NDArray[np.float32]
        Vector de valors amb unitats nm.
    laser_nm: float
        Intensitat del làser emprat per a la il·luminació.

    Returns
    -------
    values: NDArray[np.float32]
        Valors convertits a cm-1.

    """
    return np.array(1e7 * (1 / laser_nm - 1 / array), dtype=np.float32)


def nm_to_energy(array: NDArray[np.float32]) -> NDArray[np.float32]:
    """Converteix de nm a eV.

    Parameters
    ----------
    array: NDArray[np.float32]
        Vector de valors amb unitats nm.

    Returns
    -------
    values: NDArray[np.float32]
        Valors convertits a eV.

    """
    return np.array(HC / array, dtype=np.float32)


def raman_to_nm(array: NDArray[np.float32], laser_nm: float) -> NDArray[np.float32]:
    """Converteix de cm-1 a nm.

    Parameters
    ----------
    array: NDArray[np.float32]
        Vector de valors amb unitats cm-1.
    laser_nm: float
        Intensitat del làser emprat per a la il·luminació.

    Returns
    -------
    values: NDArray[np.float32]
        Valors convertits a nm.

    """
    return np.array(1 / (1 / laser_nm - array / 1e7), dtype=np.float32)


def raman_to_energy(array: NDArray[np.float32], laser_nm: float) -> NDArray[np.float32]:
    """Converteix de cm-1 a eV.

    Parameters
    ----------
    array: NDArray[np.float32]
        Vector de valors amb unitats cm-1.
    laser_nm: float
        Intensitat del làser emprat per a la il·luminació.

    Returns
    -------
    values: NDArray[np.float32]
        Valors convertits a eV.

    """
    return np.array(HC / laser_nm - array / HC_CM, dtype=np.float32)


def energy_to_nm(array: NDArray[np.float32]) -> NDArray[np.float32]:
    """Converteix d'eV a nm.

    Parameters
    ----------
    array: NDArray[np.float32]
        Vector de valors amb unitats eV.

    Returns
    -------
    values: NDArray[np.float32]
        Valors convertits a nm.

    """
    return np.array(HC / array, dtype=np.float32)


def energy_to_raman(array: NDArray[np.float32], laser_nm: float) -> NDArray[np.float32]:
    """Converteix d'eV a cm-1.

    Parameters
    ----------
    array: NDArray[np.float32]
        Vector de valors amb unitats eV.
    laser_nm: float
        Intensitat del làser emprat per a la il·luminació.

    Returns
    -------
    values: NDArray[np.float32]
        Valors convertits a cm-1.

    """
    return np.array(HC_CM * (HC / laser_nm - array), dtype=np.float32)


def get_units(dim: int = 0, units: str = "", au: int = 0) -> str:
    """Càlcul d'unitats d'un mapa després de fer una combinació lineal d'operacions.

    Parameters
    ----------
    dim: int = 0
        Dimensions finals del mapa.
    units: str = "",
        Unitats base.
    au: int = 0
        Indica si hi ha unitats arbitràries. Si és diferent de zero, les unitats són arbitràries sempre.

    Returns
    -------
    new_units: str:
        Noves unitats corresponents.

    """
    superscript = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")

    if au != 0:
        return "a.u."

    if dim == 0:
        return ""

    if dim == 1:
        return units

    return f"{units}{str(dim).translate(superscript)}"


def coords_to_pixel(coords: list[tuple[float, float]], dim: tuple[int, int],
                    base_size: tuple[float, float]) -> list[tuple[int, int]]:
    """Torna els píxels corresponents a una llista de coordenades 2D.

    Parameters
    ----------
    coords: list[tuple[float, float]]
        Llista de coordenades
    dim: tuple[int, int]
        Dimensions de la matriu
    base_size: tuple[float, float]
        Mida base de la matriu

    Returns
    -------
    pixels: list[tuple[int, int]]
        Llista amb el píxels corresponents.

    """
    xdim, ydim = dim
    xsize, ysize = base_size

    return [(floor(x * xdim / xsize), floor(y * ydim / ysize)) for x, y in coords]


def pixel_to_coords(pixels: list[tuple[int, int]], dim: tuple[int, int],
                    base_size: tuple[float, float]) -> list[tuple[float, float]]:
    """Torna les coordenades 2D corresponents a una llista de píxels.

    Parameters
    ----------
    pixels: list[tuple[float, float]]
        Llista de coordenades
    dim: tuple[int, int]
        Dimensions de la matriu
    base_size: tuple[float, float]
        Mida base de la matriu

    Returns
    -------
    pixels: list[tuple[int, int]]
        Llista amb el píxels corresponents.

    """
    xdim, ydim = dim
    xsize, ysize = base_size

    return [((x + 0.5) * xsize / xdim, (y + 0.5) * ysize / ydim) for x, y in pixels]


def pixel_center(points: list[tuple[float, float]], dim: tuple[int, int],
                base_size: tuple[float, float]) -> list[tuple[float, float]]:
    """Torna les coordenades centrals d'un conjunt de píxels.

    Procés de càlcul:
        1. S'obtenen les coordenades d'un mapa.
        2. S'obté el píxel corresponent.
        3. Es tornen les coordenades del centre del píxel.

    Parameters
    ----------
    points: list[tuple[float, float]]
        Conjunt de coordenades.
    dim: tuple[int, int],
        Dimensions de la matriu.
    base_size: tuple[float, float]
        Mida base de la matriu.

    Returns
    -------
    pixels: list[tuple[float, float]]
        Coordenades centrades si les inicials corresponen a punts de dins de la imatge.

    """
    pixels = coords_to_pixel(points, dim, base_size)

    return pixel_to_coords(pixels, dim, base_size)


def combine_dimensions(left: tuple[int, int], operator: str, right: tuple[int, int]) -> tuple[int, int]:
    """Calcula la dimensió final del paràmetre resultant en fer una operació aritmètica.

    Parameters
    ----------
    left: tuple[int, int]
        Dimensions del paràmetre esquerre.
    operator: str
        Operador aritmètic triat
    right: tuple[int, int]
        Dimensions del paràmetre dret

    Returns
    -------
    dim, au: tuple[int, int]
        Noves dimensions del paràmetre resultant. Si au != 0, seran unitats arbitràries.

    Raises
    ------
    ValueError
        Si l'operador donat és incorrecte

    """
    left_dim, left_audim = left
    right_dim, right_audim = right

    if operator in {"+", "-"}:
        if left != right:
            msg = f"No es poden combinar dimensions {left} i {right} amb '{operator}'."
            raise ValueError(msg)
        return left

    if operator == "*":
        return left_dim + right_dim, left_audim + right_audim

    if operator == "/":
        return left_dim - right_dim, left_audim - right_audim

    msg = f"Operador no vàlid: {operator}"
    raise ValueError(msg)


def apply_operator(left: NDArray[np.float32], operator: str, right: NDArray[np.float32]) -> NDArray[np.float32]:
    """Calcula el resultat final d'una operació aritmètica simple entre dos vectors de dades.

    Parameters
    ----------
    left: NDArray[np.float32]
        Dades a l'esquerra
    operator: str
        Operació aritmètica
    right: NDArray[np.float32]
        Dades a la dreta

    Returns
    -------
    result: NDArray[np.float32]
        Vector de dades resultant

    Raises
    ------
    ValueError
        Si l'operador donat no és cap de les operacions aritmètiques bàsiques (+, -, *, /)

    """
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        match operator:
            case "+":
                result = left + right
            case "-":
                result = left - right
            case "*":
                result = left * right
            case "/":
                result = left / right
            case _:
                msg = f"Operador no vàlid: {operator}"
                raise ValueError(msg)

    # Convertim infinits i altres resultats no finits a NaN.
    result = np.asarray(result, dtype=np.float32)
    result[~np.isfinite(result)] = np.nan
    return result
