"""Funcions que calculen desplaçaments entre matrius de dades que representen la mateixa mesura."""

from tkinter import Toplevel
from typing import TYPE_CHECKING

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.signal import fftconvolve

from drawing.plots import base_plot, create_canvas

if TYPE_CHECKING:
    from numpy.typing import NDArray


def cross_correlation_shift(img1: NDArray[np.float32], img2: NDArray[np.float32], sigma_hp: float | None = 20,
                            *, use_window: bool = False, plot: bool = False) -> tuple[int, int]:
    """Corregeix el desplaçament horitzontal fila a fila.

    Parameters
    ----------
    img1: NDArray[np.float32]
        Matriu de dades de referència.
    img2: NDArray[np.float32]
        Matriu de dades problema.
    sigma_hp: float | None = 20
        Pes del filtre gaussià
    use_window: bool = False
        Indica si es fa hanning.
    plot: bool = False
        Indica si es vol graficar la matriu de correlació que determina el desplaçament òptim

    Returns
    -------
    dx, dy: tuple[int, int]
        Desplaçament de les imatges en píxels

    """
    f1 = img1.astype(float).copy()
    f2 = img2.astype(float).copy()

    # ---- HIGH PASS ----
    if sigma_hp is not None and sigma_hp > 0:
        f1 -= gaussian_filter(f1, sigma_hp)
        f2 -= gaussian_filter(f2, sigma_hp)

    # ---- WINDOWING (només si mateixa mida) ----
    same_size = f1.shape == f2.shape

    if use_window and same_size:
        wy = np.hanning(f1.shape[0])
        wx = np.hanning(f1.shape[1])
        window = np.outer(wy, wx)
        f1 *= window
        f2 *= window

    # ---- CORRELACIÓ DE FASE O FFT CONVOLUCIÓ ---- ¡
    if same_size:  # CAS 1 — mateixa mida → correlació de fase (ràpida i neta)
        f1 = np.fft.fft2(f1)
        f2 = np.fft.fft2(f2)

        r = f1 * np.conj(f2)
        r /= np.abs(r) + 1e-12

        corr = np.fft.ifft2(r)
        corr = np.abs(corr)

        max_pos = np.unravel_index(np.argmax(corr), corr.shape)
        dy, dx = max_pos

        if dy > corr.shape[0] // 2:
            dy -= corr.shape[0]
        if dx > corr.shape[1] // 2:
            dx -= corr.shape[1]

    else:
        # CAS 2 — mides diferents → FFT convolució (més lenta i sorollosa però funciona)
        corr = fftconvolve(f1, f2[::-1, ::-1], mode="full")

        max_pos = np.unravel_index(np.argmax(corr), corr.shape)
        dy = max_pos[0] - (f2.shape[0] - 1)
        dx = max_pos[1] - (f2.shape[1] - 1)

    if plot:
        fig, ax = base_plot(dim=(4, 4))
        ax.imshow(corr, cmap="viridis")

        win = Toplevel()
        win.title("Correlació de fase")

        canvas = create_canvas(fig, frame=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    return int(dx), int(dy)


MAX_R1 = 10


def line_by_line_drift_correction(img: NDArray[np.float32], max_shift: int = 20)\
                                  -> tuple[NDArray[np.float32], NDArray[np.intp]]:
    """Corregeix el desplaçament horitzontal fila a fila.

    Parameters
    ----------
    img: NDArray[np.float32]
        Matriu de dades que es corregeix.
    max_shift: int = 20
        Màxim desplaçament permés

    Returns
    -------
    corrected: NDArray[np.float32]
        Imatge corregida
    shifts: NDArray[np.float32]
        Desplaçaments de cada línia

    """
    h, w = img.shape
    corrected = np.full_like(img, np.nan)
    shifts = np.zeros(h, dtype=int)

    ref_row = img[0].astype(float)
    corrected[0] = ref_row

    for y in range(1, h):
        row = img[y].astype(float)

        best_shift = 0
        best_score = -np.inf

        for dx in range(-max_shift, max_shift + 1):
            if dx < 0:
                r1 = ref_row[:dx]
                r2 = row[-dx:]
            elif dx > 0:
                r1 = ref_row[dx:]
                r2 = row[:-dx]
            else:
                r1 = ref_row
                r2 = row

            if len(r1) < MAX_R1:
                continue

            score = np.sum((r1 - r1.mean()) * (r2 - r2.mean()))

            if score > best_score:
                best_score = score
                best_shift = dx

        shifts[y] = best_shift

        new_row = np.full(w, np.nan)

        if best_shift < 0:
            new_row[:best_shift] = row[-best_shift:]
        elif best_shift > 0:
            new_row[best_shift:] = row[:-best_shift]
        else:
            new_row[:] = row

        corrected[y] = new_row
        ref_row = corrected[y]

    return corrected, shifts
