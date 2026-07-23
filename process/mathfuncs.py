import numpy as np
from scipy.special import voigt_profile

def lorentz(x: float, x0: float, FWHM: float, A: float) -> float:
    return A / (1 + ((x - x0) / (FWHM / 2)) ** 2)

def gaussian(x: float, x0: float, FWHM: float, A: float) -> float:
    sigma = FWHM / (2 * np.sqrt(2 * np.log(2)))
    return A * np.exp(-((x - x0) / sigma) ** 2 / 2)

def voigt(x, x0, sigma, gamma, A):
    return A * voigt_profile(x - x0, sigma, gamma)

from scipy.stats import exponnorm

def EMG(x, x0, FWHM, A, tau):
    sigma = FWHM / (2 * np.sqrt(2 * np.log(2)))
    # tau : float. Constant exponencial (>0).
    K = tau / sigma

    return A * exponnorm.pdf(x, K=K, loc=x0, scale=sigma)

def constant(x: float, y0: float):
    return np.full_like(x, y0)

Functions = {'G': gaussian, 'L': lorentz, 'V': voigt, 'EMG': EMG, 'C': constant}

FuncParams = {
    'G': ('x0', 'FWHM', 'A'),
    'L': ('x0', 'FWHM', 'A'),
    'V': ('x0', 'sigma', 'gamma', 'A'),
    'EMG': ('x0', 'FWHM', 'A', 'tau'),
    'C': ('C',)
}

def linear_combination(names, funcs):
    func_list = [Functions[f] for f in funcs]
    pars_list = [FuncParams[f] for f in funcs]

    def model(x, params):
        y = np.zeros_like(x, dtype=float)
        pv = params.valuesdict()

        for name, func, pars in zip(names, func_list, pars_list):
            p = [pv[f"{name}_{par}"] for par in pars]
            y += func(x, *p)

        return y

    return model