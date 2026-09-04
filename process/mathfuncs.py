import numpy as np
from scipy.special import voigt_profile, erfcx
from scipy.stats import exponnorm
from scipy.optimize import brentq

def lorentz(x: float, x0: float, gamma: float, A: float) -> float:
    return A / (1 + ((x - x0) / gamma ) ** 2)

def gaussian(x: float, x0: float, sigma: float, A: float) -> float:
    return A * np.exp(-((x - x0) / sigma) ** 2 / 2)

def voigt(x, x0, sigma, gamma, area):
    return area * voigt_profile(x - x0, sigma, gamma)

def voigt_init(x0, sigma, gamma, A):
    area = A * sigma * np.sqrt(2 * np.pi) / erfcx(gamma / (sigma * np.sqrt(2)))
    params = {'x0': x0, 'sigma': sigma, 'gamma': gamma, 'area': area}

    return params

def EMG(x, mean_g, sigma, area, K):
    return area * exponnorm.pdf(x, K=K, loc=mean_g, scale=sigma)

def EMG_init(x0, sigma, A, tau):
    K = tau / sigma
    mean_g = x0 + sigma * np.sqrt(2) * erfcxinv(K * np.sqrt(2 / np.pi)) - sigma / K

    area = np.sqrt(2 * np.pi) * sigma * A * np.exp(1/2 * ((mean_g - x0)/ sigma) ** 2)
    params = {'mean_g': mean_g, 'sigma': sigma, 'area': area, 'K': K}

    return params

def erfcxinv(y):
    if y <= 0:
        raise ValueError("erfcxinv requires y > 0")

    f = lambda x: erfcx(x) - y

    if y > 1:
        a, b = -1.0, 0.0

        while f(a) < 0:
            a *= 2

    elif y < 1:
        a, b = 0.0, 1.0

        while f(b) > 0:
            b *= 2

    else:
        return 0.0

    return brentq(f, a, b)

def exp_decay(x, A, tau):
    return A * np.exp (-x / tau)

def poly0(x: float, a0: float):
    return np.full_like(x, a0)

def poly1(x, a0, a1):
    return a0 + a1 * x

def poly2(x, a0, a1, a2):
    return a0 + a1 * x + a2 * (x ** 2)

Functions = {'Gaussiana': gaussian, 'Lorentziana': lorentz, 'Voigt': voigt, 'EMG': EMG,
             'Exp. Decay': exp_decay, 'Poly0': poly0, 'Poly1': poly1, 'Poly2': poly2}

FuncParams = {
    'Gaussiana': ('x0', 'sigma', 'A'),
    'Lorentziana': ('x0', 'gamma', 'A'),
    'Voigt': ('x0', 'sigma', 'gamma', 'A'),
    'EMG': ('x0', 'sigma', 'tau', 'A'),
    'Exp. Decay': ('tau', 'A'),
    'Poly0': ('a0',),
    'Poly1': ('a0', 'a1'),
    'Poly2': ('a0', 'a1', 'a2'),
}

INIT_PARAMS = {'EMG': EMG_init, 'Voigt': voigt_init}

DEFAULT_PARAMS = {
    'x0':    {'value': 0.0,    'min': -np.inf, 'max': np.inf, 'vary': True, 'color': 'viridis', 'dim': 1},
    'sigma': {'value': 1.0,    'min': 0.0,     'max': np.inf, 'vary': True, 'color': 'cividis', 'dim': 1},
    'gamma': {'value': 1.0,    'min': 0.0,     'max': np.inf, 'vary': True, 'color': 'inferno', 'dim': 1},
    'FWHM':  {'value': 1.0,    'min': 0.0,     'max': np.inf, 'vary': True, 'color': 'cividis', 'dim': 1},
    'A':     {'value': 1000.0, 'min': 0.0,     'max': np.inf, 'vary': True, 'color': 'hot',     'dim': 0},
    'tau':   {'value': 10,     'min': 0.0,     'max': np.inf, 'vary': True, 'color': 'Reds',    'dim': 1},
    'a0':    {'value': 0.0,    'min': 0.0,     'max': np.inf, 'vary': True, 'color': 'gray',    'dim': 0},
    'a1':    {'value': 0.0,    'min': -np.inf, 'max': np.inf, 'vary': True, 'color': 'Blues',   'dim': -1},
    'a2':    {'value': 0.0,    'min': -np.inf, 'max': np.inf, 'vary': True, 'color': 'Oranges', 'dim': -2}
}

def get_units(dim, units):
    super = {-1: '⁻¹', '2': '²', 3: '³'}

    if dim == 0: return 'cts'
    if dim == 1: return units

    return f'{units}{super[dim]}'

def linear_combination(names, funcs):
    func_list = [Functions[f] for f in funcs]
    pars_list = [FuncParams[f] for f in funcs]

    def model(x, params):
        y = np.zeros_like(x, dtype=float)
        pv = params.valuesdict()

        for name, func_name, func, pars in zip(
            names, funcs, func_list, pars_list
        ):
            p = {
                par: pv[f'{name}_{par}']
                for par in pars
            }

            if func_name in INIT_PARAMS:
                p = INIT_PARAMS[func_name](**p)

            y += func(x, **p)

        return y

    return model