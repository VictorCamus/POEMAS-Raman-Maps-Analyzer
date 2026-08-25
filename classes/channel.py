import numpy as np
from numpy.typing import NDArray
from dataclasses import dataclass, field
from typing import Dict

from classes.fits import FitResult
from process.basics import set_lims
from CCD.correction import ccd_correct

@dataclass
class ChannelData:  # Crea canals per a cada tipus de mapa dins d'un fitxer.
    name: str
    Z: np.ndarray | None = None
    units: str = None
    lims: NDArray[np.floating] | None = None
    xdata: Dict[str, np.ndarray] = field(default_factory = dict)
    spectra: np.ndarray = None
    spec_bkg: np.ndarray = None
    spectra_lims: list[float] = None
    spec_units: str = None
    fits: Dict[str, FitResult] = field(default_factory = dict)
    color: Colors = None

    def __post_init__(self):
        if self.color is None: self.color = Colors(self.name)

        if self.Z is None and self.spectra is not None:
            self.spectra = ccd_correct(self.xdata['nm'], self.spectra)
            self.spec_bkg = np.zeros_like(self.spectra)

            self.Z = np.nansum(self.spectra, axis = 2, dtype=float)
            self.spectra_lims = [round(self.xdata[self.units][0], 3), round(self.xdata[self.units][-1], 3)]

        self.spec_units = 'cts'
        if self.lims is None: self.update_lims()

    @property
    def ax_title(self):
        return f'{self.name} ({self.units})' if self.units else f'{self.name}'

    def update_lims(self):
        self.lims, self.Z = set_lims(self.name, self.Z)

@dataclass
class Colors:
    cmap_c: str  # Color.
    cmap_r: bool = False  # Normal o revertit.
    scale: str = 'w'
    limInf: str = 'w'
    limSup: str = 'k'

    @property
    def cmap(self):
        return f'{self.cmap_c}_r' if self.cmap_r else self.cmap_c

    @property
    def lims(self):
        return self.limInf, self.limSup