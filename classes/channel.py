import numpy as np
from numpy.typing import NDArray
from dataclasses import dataclass, field
from typing import Dict

from classes.fits import FitResult
from process.basics import set_lims, find_nearest
from CCD.correction import ccd_correct

@dataclass
class ChannelData:  # Crea canals per a cada tipus de mapa dins d'un fitxer.
    name: str
    Z: np.ndarray | None = None
    units: str = None
    lims: NDArray[np.floating] | None = None
    color: Colors = None
    spectra: SpecData = None

    def __post_init__(self):
        if self.color is None: self.color = Colors(self.name)

        if self.Z is None and self.spectra.ydata is not None:
            self.Z = np.nansum(self.spectra.ydata, axis = 2, dtype=float)

        if self.lims is None: self.update_lims()


    @property
    def ax_title(self):
        return f'{self.name} ({self.units})' if self.units else f'{self.name}'

    def update_lims(self):
        self.lims, self.Z = set_lims(self.name, self.Z)

@dataclass
class SpecData:
    xdata: Dict[str, np.ndarray] = field(default_factory = dict)
    ydata: np.ndarray = None
    bkgdata: np.ndarray = None
    units: str = None
    lims: list[float] = None
    coords: tuple[int] = (0, 0)
    fits: Dict[str, FitResult] = field(default_factory = dict)

    @property
    def x(self):
        return self.xdata[self.units]

    @property
    def y(self):
        return self.ydata[*self.coords]

    @property
    def bkg(self):
        return self.bkgdata[*self.coords]

    @property
    def xrange(self):
        left_index, right_index = sorted(find_nearest(self.x, self.lims))

        return slice(left_index, right_index)

    def __post_init__(self):
        # self.spectra = ccd_correct(self.xdata, self.spectra)

        if self.lims is None: self.lims = [round(self.x[0], 3), round(self.x[-1], 3)]
        if self.bkgdata is None: self.bkgdata = np.zeros_like(self.ydata)

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