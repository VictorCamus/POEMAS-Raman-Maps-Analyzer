import numpy as np
from scipy.special import voigt_profile, erfc, erfcx
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

def _EMG_fwhm_scalar(sigma, tau):
    if not np.isfinite(sigma) or not np.isfinite(tau): return np.nan
    if sigma <= 0 or tau <= 0: return np.nanç

    K = tau / sigma

    t0 = (1 / K - np.sqrt(2) * erfcxinv(K * np.sqrt(2 / np.pi)))

    if not np.isfinite(t0): return np.nan

    def profile(t):
        z = (1 / K - t) / np.sqrt(2)
        return np.exp(1 / (2 * K ** 2) - t / K) * erfc(z)

    half = profile(t0) / 2

    left = brentq(lambda t: profile(t) - half, -20, t0)
    right = brentq(lambda t: profile(t) - half, t0, t0 + 20 * K + 20)

    return sigma * (right - left)

def EMG_fwhm(p):
    sigma = np.asarray(p['sigma'], dtype=float)
    tau = np.asarray(p['tau'], dtype=float)

    fwhm = np.vectorize(_EMG_fwhm_scalar)(sigma, tau)

    return fwhm

def EMG_area(p):
    K = p['tau'] / p['sigma']

    mean_g = (p['x0'] + p['sigma'] * np.sqrt(2)
        * erfcxinv(K * np.sqrt(2 / np.pi)) - p['sigma'] / K)

    return (np.sqrt(2 * np.pi) * p['sigma'] * p['A']
        * np.exp(0.5 * ((mean_g - p['x0']) / p['sigma'])**2))

def erfcxinv(y):
    """
    Inverse of erfcx(x).

    Accepts scalars or NumPy arrays.
    Invalid values (NaN, inf or <= 0) return NaN.
    """

    scalar = np.ndim(y) == 0
    y = np.asarray(y, dtype=float)

    x = np.full_like(y, np.nan)

    valid = np.isfinite(y) & (y > 0)

    if not np.any(valid):
        return float(x) if scalar else x

    # ------------------------------------------------------------
    # y >= 1  ->  x <= 0
    # ------------------------------------------------------------

    mask = valid & (y >= 1)

    if np.any(mask):
        ym = y[mask]

        lo = np.full_like(ym, -1.0)
        hi = np.zeros_like(ym)

        while np.any(erfcx(lo) < ym):
            test = erfcx(lo) < ym
            lo[test] *= 2

        for _ in range(60):
            mid = (lo + hi) / 2
            value = erfcx(mid)

            lower = value >= ym

            lo = np.where(lower, mid, lo)
            hi = np.where(lower, hi, mid)

        x[mask] = (lo + hi) / 2

    # ------------------------------------------------------------
    # 0 < y < 1  ->  x > 0
    # ------------------------------------------------------------

    mask = valid & (y < 1)

    if np.any(mask):
        ym = y[mask]

        hi = np.maximum(
            1.0,
            1 / (np.sqrt(np.pi) * ym)
        )

        lo = hi / 2

        while np.any(erfcx(lo) < ym):
            test = erfcx(lo) < ym
            lo[test] /= 2

        for _ in range(60):
            mid = (lo + hi) / 2
            value = erfcx(mid)

            lower = value >= ym

            lo = np.where(lower, mid, lo)
            hi = np.where(lower, hi, mid)

        x[mask] = (lo + hi) / 2

    return float(x) if scalar else x

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

DerivedParams = {
    'Gaussiana': {'FWHM': lambda p: 2 * np.sqrt(2 * np.log(2)) * p['sigma'],
                  'Àrea': lambda p: np.sqrt(2 * np.pi) * p['sigma'] * p['A']},

    'Lorentziana': {'FWHM': lambda p: 2 * p['gamma'],
                    'Àrea': lambda p: np.pi * p['gamma'] * p['A']},

    'Voigt': {'FWHM': lambda p: (0.5346 * (2 * p['gamma'])
             + np.sqrt(0.2166 * (2 * p['gamma'])**2 + (2 * np.sqrt(2 * np.log(2)) * p['sigma'])**2)),
             'Àrea': lambda p: (p['A'] * p['sigma'] * np.sqrt(2 * np.pi)
             / erfcx(p['gamma'] / (p['sigma'] * np.sqrt(2))))},

    'EMG': {'FWHM': lambda p: EMG_fwhm(p),
            'Àrea': lambda p: EMG_area(p)}}

INIT_PARAMS = {'EMG': EMG_init, 'Voigt': voigt_init}

DEFAULT_PARAMS = {
    'x0':    {'value': 0.0,    'min': -np.inf, 'max': np.inf, 'vary': True, 'color': 'viridis', 'dim': 1},
    'sigma': {'value': 1.0,    'min': 0.0,     'max': np.inf, 'vary': True, 'color': 'magma', 'dim': 1},
    'gamma': {'value': 1.0,    'min': 0.0,     'max': np.inf, 'vary': True, 'color': 'plasma', 'dim': 1},
    'A':     {'value': 1000.0, 'min': 0.0,     'max': np.inf, 'vary': True, 'color': 'hot',     'dim': 0},
    'tau':   {'value': 10,     'min': 0.0,     'max': np.inf, 'vary': True, 'color': 'reds',    'dim': 1},
    'a0':    {'value': 0.0,    'min': 0.0,     'max': np.inf, 'vary': True, 'color': 'gray',    'dim': 0},
    'a1':    {'value': 0.0,    'min': -np.inf, 'max': np.inf, 'vary': True, 'color': 'blues',   'dim': -1},
    'a2':    {'value': 0.0,    'min': -np.inf, 'max': np.inf, 'vary': True, 'color': 'oranges', 'dim': -2},
    'FWHM':  {'color': 'cividis', 'dim': 1},
    'Àrea':  {'color': 'inferno', 'dim': 1}
}

def get_units(dim: int, units: str) -> str:
    if dim == 0:
        return ""

    if dim == 1:
        return units

    superscript = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")

    return f"{units}{str(dim).translate(superscript)}"

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