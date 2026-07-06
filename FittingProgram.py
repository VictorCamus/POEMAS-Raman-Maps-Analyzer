import numpy as np
from scipy.interpolate import CubicSpline
from pybaselines import Baseline
from scipy.signal import find_peaks, peak_widths
from math import floor, ceil  
from tkinter import filedialog
from pathlib import Path
from process.basics import find_nearest
from process.mathfuncs import FuncParams, linear_combination
from dataclasses import dataclass
from fileio.adapters import open_file
from lmfit import Parameters, minimize, fit_report
from time import perf_counter

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
        return result, result.success

    except (ValueError, RuntimeError) as e:
        ix,iy = coords
        print(f"Error ajustant el pic X={ix} Y={iy}: {e}")
        return None, False
        
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
        f.write(f"# Funcions: {', '.join(fit.PeakFuncs)}\n\n")

        header = ["Paràmetre", "Valor", "Mínim", "Màxim", "Expr", "Vary"]

        f.write(f"{header[0]:<12} {header[1]:<10} {header[2]:<10} {header[3]:<10} {header[4]:<15} {header[5]:<6}\n")

        for par in fit.params.values():
            f.write(f"{par.name:<12} {par.value:<10.6g} {par.min:<10.6g} {par.max:<10.6g}"
                f" {'' if par.expr is None else par.expr:<15} {str(par.vary):<6}\n")

def fit_function(file, fits, fonsSplineGlobal=False):
    print(f'Obrint {file.stem}')
    xdata, ydata, _, dims, _, units = open_file([file], file.suffix)
    N = dims[0]*dims[1]

    if fonsSplineGlobal:
        baseline_fitter = Baseline(x_data=xdata[units])
        bkgMatrix = []
        for i, intensity in enumerate(ydata):
            bkg, params = baseline_fitter.mixture_model(intensity)
            y = i // dims[1] + 1; x = i % dims[1] + 1
            bkgMatrix.append([x, y, *bkg])

    for fit in fits:
        t1 = perf_counter()
        xfit = xdata[fit.units]
        IdxInf, IdxSup = sorted(find_nearest(xfit, fit.rang))
        xfit = xfit[IdxInf:IdxSup]

        ruta = file.with_suffix('') / f'{fit.nom}'
        ruta.parent.mkdir(parents=True, exist_ok=True)
        write_init_params(ruta, fit)

        print(f'Fit {fit.nom}:\n')
        fit_files = {peak: write_header(f'{ruta}_{peak}', Info(fit.nom, peak, func, fit.units, fit.rang[0], fit.rang[1]))
                     for peak, func in zip(fit.PeakNames, fit.PeakFuncs)}

        for i, yfit in enumerate(ydata):
            if i%100 == 0: print(f"Ajustant espectre {i+1}/{N}...\n")
            if fonsSplineGlobal: yfit -= bkgMatrix[i][2:]

            yfit, canviat = spike_removal(yfit)
            yfit = yfit[IdxInf:IdxSup]

            iy = i // dims[1] + 1; ix = i % dims[1] + 1
            if ix == 1: params_actuals = fit.params.copy()

            if np.sum(yfit) <= fit.threshold: success = False
            else: result, success = ajust_pic(xfit, yfit, fit.funcio, (ix,iy), params_actuals)

            if success: params_actuals = result.params.copy()

            for peak, func in zip(fit.PeakNames, fit.PeakFuncs):
                pars = FuncParams[func]
                line = f"{ix:<4d} {iy:<4d}"

                if not success: line += f" {np.nan:<10}" * (2 * len(pars))
                else:
                    vals = []
                    errs = []

                    for par in pars:
                        p = params_actuals[f"{peak}_{par}"]
                        vals.append(p.value)
                        errs.append(np.nan if p.stderr is None else p.stderr)

                    line += "".join(f" {x:<10.3f}" for x in (vals + errs))

                fit_files[peak].write(f"{line}\n")

        for f in fit_files.values(): f.close()
        print(f"Temps total: {perf_counter()-t1:3f} s\n")

    if fonsSplineGlobal:
        ruta = file.with_suffix('') / "SplineGlobal"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        info = Info(file.stem, 'bkg_spline', 'bkg_spline', units, xdata[units][0], xdata[units][-1])
        write_bkg(f'{ruta}_bkg', info, bkgMatrix)

    print("Finalitzat correctament")

if __name__ == '__main__':
    params = Parameters()

    # Pic 1
    params.add('LE_FWHM', value=0.45, min=0, max=0.6)
    params.add('LE_A', value=500, min=10)

    # Pic 2

    params.add("FE_x0", value = 2.38, min = 2.37, max = 2.42)
    params.add("Delta", value=0.23, min=0.18, max=0.3)
    params.add('LE_x0', expr="FE_x0 - Delta")
    params.add("FE_FWHM", value=0.17, min=0, max=0.2)
    params.add('Aratio', value = 0.1, min = 0, max = 0.5)
    params.add("FE_A", expr = 'Aratio*LE_A')

    # Baseline
    params.add('bkg_C', value=100, min=0, max=300)

    fit1 = Ajust(
        nom = "PL-2peaksPEAPbI7", # Name of the fit
        PeakNames = ["LE", "FE", "bkg"], # Name of the peaks in the fit
        PeakFuncs = ['G', 'G', 'C'], # Functions for single peak representation
        units = 'eV', # Units: nm, eV, 1/cm
        rang = [1.8, 2.7], # Spectral range to fit
        params = params,
        threshold = 35000) # Limits for the fit parameters

    params = Parameters()

    # Pic 1
    params.add('LE_x0', value=2.2, min=1.9, max=2.4)
    params.add('LE_FWHM', value=0.45, min=0, max=2)
    params.add('LE_A', value=500, min=20)

    # Baseline
    params.add('bkg_C', value=100, min=0, max=300)

    fit2 = Ajust(
        nom = "PL-1peakPEAPbI7", # Name of the fit
        PeakNames = ["LE", "bkg"], # Name of the peaks in the fit
        PeakFuncs = ['G', 'C'], # Functions for single peak representation
        units = 'eV', # Units: nm, eV, 1/cm
        rang = [1.8, 2.7], # Spectral range to fit
        params = params,
        threshold = 35000) # Limits for the fit parameters

    #IMPORTANT: only fits added to this vector will be done:
    fits = [fit1, fit2]

    nomsFmapes = filedialog.askopenfilenames(filetypes = [("AIST", "*.aist"), ("TXT", "*.txt")])
    for nom in nomsFmapes: fit_function(Path(nom), fits, fonsSplineGlobal=False)