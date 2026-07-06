import numpy as np
import math as math
from tkinter import Toplevel
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.ndimage import gaussian_filter
from scipy.signal import fftconvolve
from drawing.plots import base_plot

def cross_correlation_shift(img1, img2, sigma_hp=20, use_window=True, plot=False):
    f1 = img1.astype(float).copy()
    f2 = img2.astype(float).copy()

    # ---- HIGH PASS ----
    if sigma_hp is not None and sigma_hp > 0:
        f1 -= gaussian_filter(f1, sigma_hp)
        f2 -= gaussian_filter(f2, sigma_hp)

    # ---- WINDOWING (només si mateixa mida) ----
    same_size = (f1.shape == f2.shape)

    if use_window and same_size:
        wy = np.hanning(f1.shape[0])
        wx = np.hanning(f1.shape[1])
        window = np.outer(wy, wx)
        f1 *= window
        f2 *= window

    # ---- CORRELACIÓ DE FASE O FFT CONVOLUCIÓ ---- ¡
    if same_size: # CAS 1 — mateixa mida → correlació de fase (ràpida i neta)
        F1 = np.fft.fft2(f1)
        F2 = np.fft.fft2(f2)

        R = F1 * np.conj(F2)
        R /= np.abs(R) + 1e-12

        corr = np.fft.ifft2(R)
        corr = np.abs(corr)

        max_pos = np.unravel_index(np.argmax(corr), corr.shape)
        dy, dx = max_pos

        if dy > corr.shape[0] // 2:
            dy -= corr.shape[0]
        if dx > corr.shape[1] // 2:
            dx -= corr.shape[1]
            
    else:
        # CAS 2 — mides diferents → FFT convolució (més lenta i sorollosa però funciona)
        corr = fftconvolve(f1, f2[::-1, ::-1], mode='full')

        max_pos = np.unravel_index(np.argmax(corr), corr.shape)
        dy = max_pos[0] - (f2.shape[0] - 1)
        dx = max_pos[1] - (f2.shape[1] - 1)

    if plot:
        fig, ax = base_plot(dim=(4,4))
        ax.imshow(corr, cmap='viridis')

        win = Toplevel()
        win.title("Correlació de fase")

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    return int(dx), int(dy)

def line_by_line_drift_correction(img, max_shift=20): # Corregeix drift horitzontal fila a fila. Retorna imatge corregida + shifts per fila.
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

            if len(r1) < 10:
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

def apply_crop(file, ix0, ix1, iy0, iy1): # Funció que aplica el crop a un fitxer donat els índexs de crop. Actualitza les dades i el render de tots els canals del fitxer.
    Nx, Ny = file.N
    Lx, Ly = file.midaBase

    px, py = Lx / Nx, Ly / Ny

    new_Nx, new_Ny = ix1 - ix0, iy1 - iy0
    file.N = [new_Nx, new_Ny]
    file.midaBase = (new_Nx * px, new_Ny * py)

    file.crop = True

    # actualitzar canals sense múltiples redraws
    for ch in file.channel.values(): ch.Z = ch.Z[iy0:iy1, ix0:ix1]
    
    file.zoom.xylims = ((0, file.midaBase[0]), (0, file.midaBase[1]))
    file.redraw()