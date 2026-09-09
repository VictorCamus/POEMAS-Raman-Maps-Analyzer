import numpy as np
from numpy.typing import NDArray
from dataclasses import dataclass, field
from typing import Dict

from classes.fits import FitResult
from process.basics import set_lims, find_nearest

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
    raw_ydata: np.ndarray = None
    bkgdata: np.ndarray = None
    units: str = None
    lims: list[float] = None
    CCD: np.ndarray = None
    bkg_active: bool = True
    CCD_active: bool = False
    coords: tuple[int] = (0, 0)
    fits: Dict[str, FitResult] = field(default_factory = dict)

    @property
    def x(self):
        return self.xdata[self.units]

    @property
    def y(self):
        return self.ydata[*self.coords].astype(np.float32)

    @property
    def bkg(self):
        if self.bkgdata is None: return np.zeros_like(self.y)

        return self.bkgdata[*self.coords].astype(np.float32)

    @property
    def xrange(self):
        left_index, right_index = sorted(find_nearest(self.x, self.lims))

        return slice(left_index, right_index)

    @property
    def ydata(self):
        ydata = self.raw_ydata.astype(np.float32)

        if self.bkgdata is None: bkg = 0
        else: bkg = self.bkgdata.astype(np.float32)

        if self.CCD_active: ydata = (ydata - bkg) / self.CCD + bkg

        return ydata

    def __post_init__(self):
        if self.lims is None: self.lims = [round(min(self.x), 3), round(max(self.x), 3)]
        if self.CCD is None:
            with open('process/CCD.csv', encoding='utf-8') as f:
                data = np.loadtxt((line.replace(',', '.') for line in f), delimiter=' ', usecols=(0, 1))

            left = data[0, 1]; right = data[-1, 1]
            self.CCD = np.asarray(np.interp(self.xdata['nm'], data[:, 0], data[:, 1], left= left, right=right), dtype=float)

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