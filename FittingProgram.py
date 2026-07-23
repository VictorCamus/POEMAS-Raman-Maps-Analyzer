import numpy as np
from scipy.interpolate import CubicSpline
from pybaselines import Baseline
from scipy.signal import find_peaks, peak_widths
from math import floor, ceil  
from tkinter import filedialog
from pathlib import Path
from process.mathfuncs import FuncParams, linear_combination
from dataclasses import dataclass
from fileio.adapters import open_file
from lmfit import Parameters, minimize
from time import perf_counter
from drawing.plots import base_plot
from process.basics import find_nearest
from window.builder import BaseFigureWindow
import matplotlib.pyplot as plt

@dataclass
class Ajust:
    nom: str
    PeakNames: list
    PeakFuncs: list
    units: str
    rang: tuple
    params: Parameters
    threshold: float = 0

    def __post_init__(self):
        self.funcio = linear_combination(self.PeakNames, self.PeakFuncs)

@dataclass
class Info:
    nom: str
    pic: str
    func: str
    units: str
    inici: float
    final: float

def residual(params, x, y, model):
    return model(x, params) - y

def spike_removal(y, width_threshold=3, prominence_threshold = 1000, moving_average_window=10, width_param_rel=0.8):                    
    # Detects and replaces spikes in the input spectrum signal with interpolated values.
    # Based on the publication by N. Coca-Lopez "An intuitive approach for spike removal in Raman spectra 
    # based on peaks’ prominence and width" https://doi.org/10.1016/j.aca.2024.342312
    canviat = False
    peaks, _ = find_peaks(y, prominence=prominence_threshold, width=[0, width_threshold])
    spikes = np.zeros(len(y), dtype=bool)
    widths, _, widths_left_end, widths_right_end = peak_widths(y, peaks, rel_height=width_param_rel)
    for width, ext_a, ext_b in zip(widths, widths_left_end, widths_right_end):
        spikes[floor(ext_a):ceil(ext_b)] = True
    y_out = y.copy()

    for i, spike in enumerate(spikes):
        if spike:
            window = np.arange(max(i - moving_average_window, 0), min(i + moving_average_window + 1, len(y)))
            window_exclude_spikes = window[spikes[window] == False]
            spline_interp = CubicSpline(window_exclude_spikes, y[window_exclude_spikes])
            y_out[i] = spline_interp(i)
            canviat = True
    return y_out, canviat

def ajust_pic(x, y, func, coords, params):
    try:
        result = minimize(residual, params, args=(x, y, func), method="least_squares", diff_step=1e-4, max_nfev = 500)
        return result, test_ajust(result, y, func(x, result.params))

    except (ValueError, RuntimeError) as e:
        ix,iy = coords
        print(f"Error ajustant el pic X={ix} Y={iy}: {e}")
        return None, (False, None)

def test_ajust(result, y, fit):

    if not result.success:
        return False, np.nan

    ss_res = np.sum((y - fit) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)

    r2 = 1 - ss_res / ss_tot

    if r2 < 0.5:
        return False, r2

    for p in result.params.values():
        if p.stderr is None:
            return False, np.nan

    return True, r2

def write_header(ruta, info):
    f = open(f"{ruta}.txt", "w", encoding="utf-8", newline="")

    f.write(f"#Nom: {info.nom}\n")
    f.write(f"#Pic: {info.pic}\n")
    f.write(f"#Funció: {info.func}\n")
    f.write(f"#Unitats: {info.units}\n")
    f.write(f"#Inici: {info.inici}\n")
    f.write(f"#Final: {info.final}\n\n")

    pars = FuncParams[info.func]
    f.write(f"{'# x':<4} {'y':<4}")

    for par in pars: f.write(f" {par:<10}")
    for par in pars: f.write(f" {'err_' + par:<10}")

    f.write("\n")

    return f

def write_bkg(ruta, info, data):
    with open(f'{ruta}.txt', 'w', encoding='utf-8', newline='') as f:
        f.write(f"#Nom: {info.nom}\n")
        f.write(f"#Funció: {info.func}\n")
        f.write(f"#Unitats: {info.units}\n")
        f.write(f'#Inici: {info.inici}\n')
        f.write(f'#Final: {info.final}\n\n')
        header = ["f'{x:", "y"] + ["Background intensity"]
        np.savetxt(f, data, delimiter = '\t', fmt = '%-10.3f', header = '\t'.join(header))

def write_init_params(ruta, fit):
    with open(f"{ruta}__init_params.txt", "w", encoding="utf-8") as f:
        f.write(f"# Ajust: {fit.nom}\n")
        f.write(f"# Pics: {', '.join(fit.PeakNames.values())}\n")
        f.write(f"# Funcions: {', '.join(fit.PeakFuncs)}\n\n")

        header = ["Paràmetre", "Valor", "Mínim", "Màxim", "Expr", "Vary"]

        f.write(f"{header[0]:<12} {header[1]:<10} {header[2]:<10} {header[3]:<10} {header[4]:<15} {header[5]:<6}\n")

        for par in fit.params.values():
            f.write(f"{par.name:<12} {par.value:<10.6g} {par.min:<10.6g} {par.max:<10.6g}"
                f" {'' if par.expr is None else par.expr:<15} {str(par.vary):<6}\n")

def fit_function(file, fits, fonsSplineGlobal=False):
    print(f'Obrint {file.stem}')
    channel, N, mida, units, laser = open_file([file], file.suffix)
    spectra = channel['Spectra'].spectra
    xdata = channel['Spectra'].xdata
    Nx, Ny = N
    Ntotal = Nx*Ny

    if fonsSplineGlobal:
        baseline_fitter = Baseline(x_data=xdata[units])
        bkgMatrix = []
        for i, ydata in enumerate(spectra):
            bkg, params = baseline_fitter.mixture_model(ydata)
            y = i // Nx + 1; x = i % Nx + 1
            bkgMatrix.append([x, y, *bkg])
    
    for fit in fits:
        r2 = []
        t1 = perf_counter()
        xfit = xdata[fit.units]
        IdxInf, IdxSup = sorted(find_nearest(xfit, fit.rang))
        xfit = xfit[IdxInf:IdxSup]

        ruta = file.with_suffix('') / f'{fit.nom}'
        ruta.parent.mkdir(parents=True, exist_ok=True)
        write_init_params(ruta, fit)

        print(f'Fit {fit.nom}:\n')
        fit_files = {peak: write_header(f'{ruta}_{peak}', Info(fit.nom, peak, func, fit.units, fit.rang[0], fit.rang[1]))
                     for peak, func in zip(fit.PeakNames.values(), fit.PeakFuncs)}

        for i, ydata in enumerate(spectra):
            if i%100 == 0: print(f"Ajustant espectre {i+1}/{Ntotal}...\n")
            if fonsSplineGlobal: ydata -= bkgMatrix[i][2:]
            # ydata, canviat = spike_removal(ydata)
            yfit = ydata[IdxInf:IdxSup]
            iy = i // Nx + 1; ix = i % Nx + 1
            if ix == 1: params_actuals = fit.params.copy()

            if np.sum(yfit) <= fit.threshold: success = False, np.nan
            else: result, success = ajust_pic(xfit, yfit, fit.funcio, (ix,iy), params_actuals)

            if success[0]: params_actuals = result.params.copy()
            r2.append(success[1])
            for (peak_num, peak_name), func in zip(fit.PeakNames.items(), fit.PeakFuncs):
                pars = FuncParams[func]
                line = f"{ix:<4d} {iy:<4d}"

                if not success[0]: line += f" {np.nan:<10}" * (2 * len(pars))
                else:
                    vals = []
                    errs = []

                    for par in pars:
                        p = params_actuals[f"{peak_num}_{par}"]
                        vals.append(p.value)
                        errs.append(np.nan if p.stderr is None else p.stderr)

                    line += "".join(f" {x:<10.3f}" for x in (vals + errs))

                fit_files[peak_name].write(f"{line}\n")

        r2 = np.array(r2)
        r2 = r2[np.isfinite(r2)]
        values, bins = np.histogram(r2, bins = 50)
        bins = (bins[1:] + bins[:-1])/2
        r2 = np.asarray(r2)
        r2 = r2[np.isfinite(r2)]

        values, bins = np.histogram(r2, bins=50)

        bins = (bins[:-1] + bins[1:]) / 2

        plt.bar(bins, values, width=bins[1] - bins[0], align='center')
        plt.show()

        for f in fit_files.values(): f.close()
        print(f"Temps total: {perf_counter()-t1:3f} s\n")

    if fonsSplineGlobal:
        ruta = file.with_suffix('') / "SplineGlobal"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        info = Info(file.stem, 'bkg_spline', 'bkg_spline', units, xdata[units][0], xdata[units][-1])
        write_bkg(f'{ruta}_bkg', info, bkgMatrix)

    print("Finalitzat correctament")

class FitSpec(BaseFigureWindow):
    def __init__(self, gestor, xdata, ydata):
        self.fig, self.ax = base_plot()
        self.x = xdata
        self.y = ydata

        self.plot = self.ax.plot(self.x, self.y, color = 'r')
        self.fig.canvas.draw()
        plt.show()

if __name__ == '__main__':

    params = Parameters()

    # Pic 1
    params.add("P1_x0", value = 1.26, min = 1.2, max = 1.35)
    params.add("P1_FWHM", value=0.1, min=0, max=0.5)
    params.add("P1_A", value=1000, min=5)

    params.add("delta_x0", value = 0.2, min = 0)

    params.add("P2_x0", expr = 'P1_x0 + delta_x0')
    # Pic 2
    params.add("P2_x0", value = 1.25, min = 1.2, max = 1.35)
    params.add("P2_FWHM", value=0.1, min=0, max=0.5)
    params.add("P2_A", value=200, min=5)

    # Baseline
    params.add("bkg_C", value=100, min=0, max=5000)

    PeakNames = {'P1': "BG", 'P2': "Defect", "bkg": "bkg"}

    fitPL = Ajust(
        nom = "PL-InSe", # Name of the fit
        PeakNames = PeakNames, # Name of the peaks in the fit
        PeakFuncs = ['G', 'G', 'C'], # Functions for single peak representation
        units = 'eV', # Units: nm, eV, 1/cm
        rang = [1.2, 1.5], # Spectral range to fit
        params = params,
        threshold = 3000) # Limits for the fit parameters

    params = Parameters()

    # Pic 1
    params.add("P1_x0", value = 115, min = 105, max = 125)
    params.add("P1_FWHM", value=4, min=0.1, max=20)
    params.add("P1_A", value=500, min=5)

    # Pic 2
    params.add("P2_x0", value = 177, min = 170, max = 185)
    params.add("P2_FWHM", value=6, min=0.1, max=20)
    params.add("P2_A", value=500, min=5)

    # Pic 3
    # params.add("P3_x0", value = 199, min = 190, max = 210)
    # params.add("P3_FWHM", value=6, min=0.1, max=20)
    # params.add("P3_A", value=500, min=10)

    # Pic 4
    params.add("P4_x0", value = 226, min = 215, max = 240)
    params.add("P4_FWHM", value=6, min=0.1, max=20)
    params.add("P4_A", value=500, min=5)

    # Baseline
    params.add("bkg_C", value=100, min=0, max=300)

    # 'P3': "A₁ (Γ₁¹)",
    PeakNames = {'P1': "A₁ (Γ₁²)", 'P2': "E (Γ₁²)", 'P4': "A₁ (Γ₁³)",
                 "bkg": "bkg"}

    fit1 = Ajust(
        nom = "RAMAN-InSe", # Name of the fit
        PeakNames = PeakNames, # Name of the peaks in the fit
        PeakFuncs = ['L', 'L', 'L', 'C'], # Functions for single peak representation
        units = '1/cm', # Units: nm, eV, 1/cm
        rang = [50, 350], # Spectral range to fit
        params = params,
        threshold = 3000) # Limits for the fit parameters

    params = Parameters()

    # Silici
    params.add("P1_x0", value = 520, min = 510, max = 530)
    params.add("P1_FWHM", value=2, min=0.5, max=20)
    params.add("P1_A", value=1500, min=50)

    params.add("bkg_C", value=100, min=0, max=300)

    PeakNames = {'P1': "Si TO", "bkg": "bkg"}

    fit2 = Ajust(
        nom = "RAMAN-Si", # Name of the fit
        PeakNames = PeakNames, # Name of the peaks in the fit
        PeakFuncs = ['G', 'C'], # Functions for single peak representation
        units = '1/cm', # Units: nm, eV, 1/cm
        rang = [510, 530], # Spectral range to fit
        params = params,
        threshold = 500) # Limits for the fit parameters

    fits = [fitPL]
    nomsFmapes = filedialog.askopenfilenames(filetypes = [("AIST", "*.aist"), ("TXT", "*.txt")])
    for nom in nomsFmapes: fit_function(Path(nom), fits, fonsSplineGlobal=False)