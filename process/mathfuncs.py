"""Funcions matemàtiques estàndard emprades principalment per al càlcul d'ajusts."""
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import brentq
from scipy.special import erfc, erfcx, voigt_profile
from scipy.stats import exponnorm

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

    from classes.protocols import ParametersProtocol

# ============================================================
# Pics
# ============================================================

type FuncParams = Mapping[str, float]


def _gaussian(x: NDArray[np.float32], params: FuncParams) -> NDArray[np.float32]:
    x0 = params["x0"]
    sigma = params["sigma"]
    amp = params["amp"]

    return np.array(amp * np.exp(-(((x - x0) / sigma) ** 2) / 2), dtype=np.float32)


def _lorentz(x: NDArray[np.float32], params: FuncParams) -> NDArray[np.float32]:
    x0 = params["x0"]
    gamma = params["gamma"]
    amp = params["amp"]

    return np.array(amp / (1 + ((x - x0) / gamma) ** 2), dtype=np.float32)


def _voigt(x: NDArray[np.float32], params: FuncParams) -> NDArray[np.float32]:
    x0 = params["x0"]
    sigma = params["sigma"]
    gamma = params["gamma"]
    area = params["area"]

    return np.array(area * voigt_profile(x - x0, sigma, gamma), dtype=np.float32)


def _emg(x: NDArray[np.float32], params: FuncParams) -> NDArray[np.float32]:
    mean_g = params["mean_g"]
    sigma = params["sigma"]
    area = params["area"]
    k = params["k"]

    return np.array(area * exponnorm.pdf(x, K=k, loc=mean_g, scale=sigma), dtype=np.float32)


# ============================================================
# Llavors
# ============================================================


def _voigt_init(params: FuncParams) -> dict[str, float]:
    x0 = params["x0"]
    sigma = params["sigma"]
    gamma = params["gamma"]
    amp = params["amp"]

    area = amp * sigma * np.sqrt(2 * np.pi) / erfcx(gamma / (sigma * np.sqrt(2)))

    return {"x0": x0, "sigma": sigma, "gamma": gamma, "area": area}


def _emg_init(params: FuncParams) -> dict[str, float]:
    x0 = params["x0"]
    sigma = params["sigma"]
    amp = params["amp"]
    tau = params["tau"]

    k = tau / sigma
    mean_g = x0 + sigma * np.sqrt(2) * _erfcxinv(k * np.sqrt(2 / np.pi)) - sigma / k

    area = np.sqrt(2 * np.pi) * sigma * amp * np.exp(1 / 2 * ((mean_g - x0) / sigma) ** 2)

    return {"mean_g": mean_g, "sigma": sigma, "area": area, "k": k}


# ============================================================
# Fons
# ============================================================


def _exp_decay(x: NDArray[np.float32], params: FuncParams) -> NDArray[np.float32]:
    amp = params["amp"]
    tau = params["tau"]

    return np.array(amp * float(np.exp(-x / tau)), dtype=np.float32)


def _poly0(x: NDArray[np.float32], params: FuncParams) -> NDArray[np.float32]:
    a0 = params["a0"]

    return np.full_like(x, a0)


def _poly1(x: NDArray[np.float32], params: FuncParams) -> NDArray[np.float32]:
    a0 = params["a0"]
    a1 = params["a1"]

    return a0 + a1 * x


def _poly2(x: NDArray[np.float32], params: FuncParams) -> NDArray[np.float32]:
    a0 = params["a0"]
    a1 = params["a1"]
    a2 = params["a2"]

    return a0 + a1 * x + a2 * (x**2)


# ============================================================
# Paràmetres dels pics només derivables numèricament
# ============================================================


def _emg_fwhm_scalar(params: FuncParams) -> float:
    sigma = params["sigma"]
    tau = params["tau"]

    if not np.isfinite(sigma) or not np.isfinite(tau):
        return np.nan
    if sigma <= 0 or tau <= 0:
        return np.nan

    k = tau / sigma

    t0 = 1 / k - np.sqrt(2) * _erfcxinv(k * np.sqrt(2 / np.pi))

    if not np.isfinite(t0):
        return np.nan

    def profile(t: float) -> float:
        z = (1 / k - t) / np.sqrt(2)
        return float(np.exp(1 / (2 * k**2) - t / k) * erfc(z))

    half = profile(t0) / 2

    left = brentq(lambda t: profile(t) - half, -20, t0)
    right = brentq(lambda t: profile(t) - half, t0, t0 + 20 * k + 20)

    return sigma * float(right - left)


def _emg_area(p: Mapping[str, NDArray[np.float32]]) -> NDArray[np.float32]:
    k = p["tau"] / p["sigma"]
    mean_g = p["x0"] + p["sigma"] * np.sqrt(2) * _erfcxinv(k * np.sqrt(2 / np.pi)) - p["sigma"] / k

    area = np.sqrt(2 * np.pi) * p["sigma"] * p["amp"] * np.exp(0.5 * ((mean_g - p["x0"]) / p["sigma"]) ** 2)
    return np.asarray(area, dtype=np.float32)


# ============================================================
# Funcions especials
# ============================================================


def _erfcxinv(y: float | NDArray[np.float32]) -> float | NDArray[np.float32]:
    """Inverse of erfcx(x).

    Accepts scalars or NumPy arrays.
    Invalid values (NaN, inf or <= 0) return NaN.
    """  # ruff: ignore[docstring-missing-returns]
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
            1 / (np.sqrt(np.pi) * ym),
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


# ============================================================
# Classes de les funcions i paràmetres
# ============================================================


@dataclass(frozen=True, slots=True)
class DefaultFunction:
    """Controla i conté les característiques predeterminades d'una funció."""

    model: Callable[[NDArray[np.float32], dict[str, float]], NDArray[np.float32]]
    params: tuple[str, ...]
    is_bkg: bool = False
    prepare_params: Callable[[FuncParams], dict[str, float]] | None = None
    derived_params: dict[str, DerivedParameter] | None = None

    def evaluate(self, xdata: NDArray[np.float32], params: dict[str, float]) -> NDArray[np.float32]:
        """Avalua el model amb els paràmetres indicats i transforma els paràmetres si és necessari.

        Parameters
        ----------
        xdata: NDArray[np.float32]
            Rang de dades sobre el que s'avalua la funció
        params: dict[str, float]
            Paràmetres de la funció

        Returns
        -------
        result: NDArray[np.float32]
            Vector de valors del model en el rang donat

        Raises
        ------
        KeyError
            Si els paràmetres donats no es corresponen amb els de la funció.

        """
        if set(params.keys()) != set(self.params):
            msg = f"Els paràmetres donats {tuple(params.keys())} no són compatibles amb els de la funció {self.params}."
            raise KeyError(msg)

        if self.prepare_params is not None:
            params = self.prepare_params(params)

        return self.model(xdata, params)


@dataclass
class DefaultParameter:
    """Classe que s'encarrega de tipejar el diccionari de paràmetres per defecte."""

    value: float = 0
    min: float = -np.inf
    max: float = np.inf
    vary: bool = True
    color: str = "AFM"
    dim: int = 1


type DerivedParameter = Callable[[Mapping[str, NDArray[np.float32]]], NDArray[np.float32]]

DEFAULT_FUNCS: Mapping[str, DefaultFunction] = {
    "Gaussiana": DefaultFunction(
        model=_gaussian,
        params=("x0", "sigma", "amp"),
        derived_params={
        "FWHM": lambda p: np.asarray(2 * np.sqrt(2 * np.log(2)) * p["sigma"], dtype=np.float32),
        "Àrea": lambda p: np.asarray(np.sqrt(2 * np.pi) * p["sigma"] * p["amp"], dtype=np.float32),
    }),
    "Lorentziana": DefaultFunction(
        model=_lorentz,
        params=("x0", "gamma", "amp"),
        derived_params={
        "FWHM": lambda p: np.asarray(2 * p["gamma"], dtype=np.float32),
        "Àrea": lambda p: np.asarray(np.pi * p["gamma"] * p["amp"], dtype=np.float32),
    }),
    "Voigt": DefaultFunction(
        model=_voigt,
        params=("x0", "sigma", "gamma", "amp"),
        prepare_params=_voigt_init,
        derived_params={
        "FWHM": lambda p: np.asarray(
            0.5346 * (2 * p["gamma"])
            + np.sqrt(
                0.2166 * (2 * p["gamma"]) ** 2 + (2 * np.sqrt(2 * np.log(2)) * p["sigma"]) ** 2,
            ), dtype=np.float32),
        "Àrea": lambda p: np.asarray(p["amp"] * p["sigma"] *
                np.sqrt(2 * np.pi) / erfcx(p["gamma"] / (p["sigma"] * np.sqrt(2))), dtype=np.float32),
    }),
    "EMG": DefaultFunction(
        model=_emg,
        params=("x0", "sigma", "tau", "amp"),
        prepare_params=_emg_init,
        derived_params={
            "FWHM": lambda p: np.asarray(np.vectorize(_emg_fwhm_scalar)(p),
            dtype=np.float32),
            "Àrea": _emg_area}),
    "Exp. Decay": DefaultFunction(
        model=_exp_decay,
        params=("tau", "amp"),
        is_bkg=True),
    "Poly0": DefaultFunction(
        model=_poly0,
        params=("a0",),
        is_bkg=True),
    "Poly1": DefaultFunction(
        model=_poly1,
        params=("a0", "a1"),
        is_bkg=True),
    "Poly2": DefaultFunction(
        model=_poly2,
        params=("a0", "a1", "a2"),
        is_bkg=True),
}

DEFAULT_PARAMS: dict[str, DefaultParameter] = {
    "x0": DefaultParameter(color="viridis"),
    "sigma": DefaultParameter(value=1.0, min=0.0, color="magma"),
    "gamma": DefaultParameter(value=1.0, min=0.0, color="plasma"),
    "amp": DefaultParameter(value=1000.0, min=0.0, color="hot", dim=0),
    "tau": DefaultParameter(value=0.2, min=0.0, color="reds"),
    "a0": DefaultParameter(min=0.0, color="gray", dim=0),
    "a1": DefaultParameter(color="blues", dim=0),
    "a2": DefaultParameter(color="oranges", dim=0),
    "FWHM": DefaultParameter(color="cividis"),
    "Àrea": DefaultParameter(color="inferno", dim=0),
}


# ============================================================
# Diccionaris amb els paràmetres possibles
# ============================================================


def linear_combination(funcs: dict[str, DefaultFunction]) ->\
                       Callable[[NDArray[np.float32], ParametersProtocol], NDArray[np.float32]]:
    """Retorna el model resultant de fer la combinació lineal de diferents funcions, bé picades o de fons.

    Parameters
    ----------
    funcs: dict[str, DefaultFunction]
        Diccionari amb les funcions i referències corresponents.

    Returns
    -------
    model: Callable[[NDArray[np.float32], ParametersProtocol], NDArray[np.float32]]
        Model resultant

    """
    def model(x:  NDArray[np.float32], params: ParametersProtocol) -> NDArray[np.float32]:
        y = np.zeros_like(x, dtype=np.float32)

        for ref, func in funcs.items():
            p = {par: params[f"{ref}_{par}"].value for par in func.params}
            y += func.evaluate(x, p)

        return y

    return model
