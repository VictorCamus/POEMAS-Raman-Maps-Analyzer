"""Funcions que nivellen i corregeixen matrius segons el mètode triat."""

from typing import TYPE_CHECKING, cast

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import ArrayLike, NDArray


def level_plane(z: NDArray[np.float32], dim: tuple[int, int]) -> NDArray[np.float32]:
    """Es nivella la imatge mitjançant la substracció d'un pla ajustat.

    El pla s'ajusta a la matriu z i es centra sobre la imatge abans d'extraure-se'n.

    Parameters
    ----------
    z: NDArray[np.float32]
        Matriu de dades.
    dim: tuple[int, int]
        Dimensions de la imatge.

    Returns
    -------
    NDArray[np.float32]
        Matriu nivellada.

    """
    xdim, ydim = dim
    _, bx, by = _fit_plane(z, dim)
    c2 = -0.5 * (bx * xdim + by * ydim)

    y, x = np.indices((ydim, xdim))
    plane = c2 + bx * x + by * y

    return z - plane


PRECISION = 1e-4


def level_facet(z: NDArray[np.float32], dim: tuple[int, int], max_iter: int = 50) -> NDArray[np.float32]:
    """Es nivella la imatge mitjançant estimació iterativa fins a obtindre la cara dominant.

    A cada iteració, els vectors normals a la superfície es calculen, i finalment s'extrau el pla
    definit pel vector normal dominant.

    Parameters
    ----------
    z: NDArray[np.float32]
        Matriu de dades.
    dim: tuple[int, int]
        Dimensions de la imatge.
    max_iter: int = 50
        Nombre màxim d'iteracions.

    Returns
    -------
    NDArray[np.float32]
        Imatge nivellada.

    """
    for _ in range(max_iter):
        nx, ny, nz = _compute_normals(z)
        n_dom = _dominant_normal(nx, ny, nz)

        plane = _normal_to_plane(n_dom, dim)
        new_data = z - plane

        # 5. criteri convergència
        if np.linalg.norm(n_dom - np.array([0, 0, 1])) < PRECISION:
            break

        z = new_data

    return z


def linematch_median(z: NDArray[np.float32], ydim: int) -> NDArray[np.float32]:
    """Es corregeixen els canvis de línia bruscos a partir del valor mitjà de cada fila.

    Parameters
    ----------
    z: NDArray[np.float32]
        Matriu de dades.
    ydim: list[int]
        Dimensió Y de la matriu.

    Returns
    -------
    NDArray[np.float32]
        Imatge nivellada.

    """
    return _apply_row_shifts(z, ydim, np.median(z, axis=1))


def linematch_median_diff(z: NDArray[np.float32], ydim: int) -> NDArray[np.float32]:
    """Es corregeixen els canvis de línia bruscos a partir de la diferències de medianes entre files.

    El desplaçament relatiu entre files consecutives es calcula de la diferència de medianes punt a
    punt. Finalment, la seqüència final de desplaçament es corregeix mitjançant l'extracció del millor
    ajust lineal de les components.

    Parameters
    ----------
    z: NDArray[np.float32]
        Matriu de dades.
    ydim: list[int]
        Dimensió Y de la matriu.

    Returns
    -------
    NDArray[np.float32]
        Imatge nivellada.

    """
    shifts = np.zeros(ydim)

    for i in range(ydim - 1):
        diff = z[i + 1] - z[i]
        median = np.median(diff)
        shifts[i + 1] = shifts[i] + median

    # eliminar pendent global (slope_level_row_shifts)
    x = np.arange(ydim)
    p = np.polyfit(x, shifts, 1)
    shifts -= (p[0] * x + p[1])

    return _apply_row_shifts(z, ydim, shifts)


THRESHOLD_VALUE = 9


def linematch_modus(z: NDArray[np.float32], ydim: int) -> NDArray[np.float32]:
    """Es corregeixen els canvis de línia bruscos a partir d'estimar l'altura dominant.

    Per a cada fila, els punts s'ordenen amb l'objectiu de buscar el segment més estret
    amb la major densitat de dades i obtindre'n la mitjana que s'usa com a desplaçament
    entre files.

    Parameters
    ----------
    z: NDArray[np.float32]
        Matriu de dades.
    ydim: list[int]
        Dimensió Y de la matriu.

    Returns
    -------
    NDArray[np.float32]
        Imatge nivellada.

    """
    shifts = np.zeros(ydim)

    for i in range(ydim):
        row = np.sort(z[i])

        n = len(row)
        if n < THRESHOLD_VALUE:
            shifts[i] = np.median(row)
        else:
            seglen = int(np.sqrt(n))
            best_width = np.inf
            best_j = 0

            for j in range(n - seglen):
                width = row[j + seglen] - row[j]
                if width < best_width:
                    best_width = width
                    best_j = j

            segment = row[best_j + seglen // 3 : best_j + 2 * seglen // 3]
            shifts[i] = np.mean(segment)

    return _apply_row_shifts(z, ydim, shifts)


def linematch_match(z: NDArray[np.float32], dim: tuple[int, int]) -> NDArray[np.float32]:
    """Es corregeixen els canvis bruscos de línies a partir de comparar coincidències entre files adjacents.

    La correcció entre cada parell de files consecutives s'estima a partir de la diferència entre els
    gradients horitzontals. Estes diferències s'empren per a computar els pesos, i el pes vertical de
    les files amb major canvi s'acumula entre files.

    Parameters
    ----------
    z: NDArray[np.float32]
        Matriu de dades.
    dim: tuple[int, int]
        Dimensions de la matriu.

    Returns
    -------
    NDArray[np.float32]
        Imatge nivellada.

    """
    xdim, ydim = dim
    shifts = np.zeros(ydim, dtype=np.float32)

    for i in range(1, ydim):
        a = z[i - 1]
        b = z[i]

        # gradient difference
        diff = (a[1:] - a[:-1]) - (b[1:] - b[:-1])
        q = np.mean(np.abs(diff), dtype=np.float32)

        if q == 0:
            shifts[i] = shifts[i - 1]
            continue

        # weights
        w = cast("NDArray[np.float32]", np.exp(-(diff**2) / (2 * q)))

        # correction
        lam = (a[0] - b[0]) * w[0]
        for j in range(1, xdim - 1):
            lam += (a[j] - b[j]) * (w[j - 1] + w[j])
        lam += (a[-1] - b[-1]) * w[-1]

        lam /= 2 * np.sum(w)

        shifts[i] = shifts[i - 1] - lam

    return _apply_row_shifts(z, ydim, shifts)


def _apply_row_shifts(z: NDArray[np.float32], ydim: int, shifts: ArrayLike) -> NDArray[np.float32]:
    shifts = np.array(shifts, dtype=np.float32)
    shifts -= np.mean(shifts)  # zero_level_row_shifts
    for i in range(ydim):
        z[i, :] -= shifts[i]

    return z


def _compute_normals(z: NDArray[np.float32]) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.float32]]:
    dzdy, dzdx = np.gradient(z)
    nx = -dzdx
    ny = -dzdy
    nz = np.ones_like(z)

    norm = np.sqrt(nx**2 + ny**2 + nz**2)
    nx /= norm
    ny /= norm
    nz /= norm

    return nx.astype(np.float32), ny.astype(np.float32), nz.astype(np.float32)


def _dominant_normal(nx: NDArray[np.float32], ny: NDArray[np.float32], nz: NDArray[np.float32],
                    sigma: float = 0.3) -> NDArray[np.float32]:
    n = np.stack([nx.ravel(), ny.ravel(), nz.ravel()], axis=1)

    mean = np.mean(n, axis=0)
    mean /= np.linalg.norm(mean)

    dots = n @ mean
    weights = np.exp((dots - 1) / (sigma**2))

    w = weights[:, None]
    n_weighted = np.sum(w * n, axis=0)
    n_weighted /= np.linalg.norm(n_weighted)

    return n_weighted


def _fit_plane(data: NDArray[np.float32], dim: tuple[int, int]) -> tuple[float, float, float]:
    y, x = np.indices(dim[::-1])

    z = data.flatten()
    x = x.flatten()
    y = y.flatten()

    # Matriu de disseny
    a = np.c_[np.ones_like(x), x, y]

    # Ajust per mínims quadrats
    coeffs, *_ = np.linalg.lstsq(a, z, rcond=None)
    c, bx, by = coeffs

    return float(c), float(bx), float(by)


def _normal_to_plane(nvec: NDArray[np.float32], dim: tuple[int, int]) -> NDArray[np.float32]:
    xdim, ydim = dim
    y, x = np.mgrid[:ydim, :xdim]

    nx0, ny0, nz0 = nvec

    c = 0.0
    bx = -nx0 / nz0
    by = -ny0 / nz0

    return np.array(c + bx * x + by * y, dtype=np.float32)
