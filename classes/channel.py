import numpy as np
from dataclasses import dataclass

from process.basics import truncar_significatives
from CCD.correction import ccd_correct

@dataclass
class ChannelData:  # Crea canals per a cada tipus de mapa dins d'un fitxer.
    name: str
    Z: object = None
    units: str = None
    lims: list[float] = None
    xdata: dict = None
    spectra: object = None
    spectra_lims: list[float] = None
    color: Colors = None

    def __post_init__(self):
        if self.color is None: self.color = Colors(self.name)
        self.ax_title =f'{self.name} ({self.units})' if self.units else f'{self.name}'

        if self.Z is None and self.spectra is not None:
            self.spectra = ccd_correct(self.xdata['nm'], self.spectra)
            self.Z = np.nansum(self.spectra, axis = 2)
            self.spectra_lims = [self.xdata['nm'][0], self.xdata['nm'][-1]]

        if self.lims is None: self.lims, self.Z = self.set_lims(self.Z, self.name)

    @staticmethod
    def set_lims(z, name):
        if name == 'Grain':
            return z, np.array([0, 1])

        vmin, vmax = np.percentile(z, [0.2, 99.8])

        # 3. Estructura match-case per a la lògica segons el tipus
        if name == 'Height':
            z -= vmin
            vmax -= vmin
            vmin = 0.0

        # 4. Truncament de valors
        vmin = truncar_significatives(vmin, 2, cap_a='avall')
        vmax = truncar_significatives(vmax, 2, cap_a='amunt')

        # 5. Seguretat per evitar límits idèntics
        if vmin == vmax:
            vmin -= 5
            vmax += 5

        return np.array([vmin, vmax]), z

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
        return (self.limInf, self.limSup)