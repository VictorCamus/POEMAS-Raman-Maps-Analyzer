"""Funcions de suavitzat de dades."""

from math import ceil, floor
from typing import TYPE_CHECKING

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.signal import find_peaks, peak_widths

if TYPE_CHECKING:
    from numpy.typing import NDArray


def spike_removal(y: NDArray[np.float32], width_threshold: float = 3, prominence_threshold: float = 1000,
                 moving_average_window: float = 10, width_param_rel: float = 0.8) -> tuple[NDArray[np.float32], bool]:
    """Detect and replace of spikes in the input spectrum signal with interpolated values.

    Based on the publication by N. Coca-Lopez "An intuitive approach for spike removal in Raman spectra
    based on peaks' prominence and width" https://doi.org/10.1016/j.aca.2024.342312

    Returns
    -------
    y_out: NDArray[np.float32]
        Resultat de les dades suavitzades.
    canviat: bool
        Indica si les dades s'han canviat.

    """
    canviat = False
    peaks, _ = find_peaks(y, prominence=prominence_threshold, width=[0, width_threshold])
    spikes = np.zeros(len(y), dtype=bool)
    widths, _, widths_left_end, widths_right_end = peak_widths(y, peaks, rel_height=width_param_rel)
    for _, ext_a, ext_b in zip(widths, widths_left_end, widths_right_end, strict=False):
        spikes[floor(ext_a) : ceil(ext_b)] = True
    y_out = y.copy()

    for i, spike in enumerate(spikes):
        if spike:
            window = np.arange(max(i - moving_average_window, 0), min(i + moving_average_window + 1,
                                                                   len(y)), dtype=np.intp)

            window_exclude_spikes = window[np.logical_not(spikes[window])]
            spline_interp = CubicSpline(window_exclude_spikes, y[window_exclude_spikes])
            y_out[i] = spline_interp(i)
            canviat = True
    return y_out, canviat
