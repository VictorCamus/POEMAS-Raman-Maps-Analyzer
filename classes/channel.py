import numpy as np
from numpy.typing import NDArray
from dataclasses import dataclass, field

from process.basics import truncar_significatives
from CCD.correction import ccd_correct

@dataclass
class ChannelData:  # Crea canals per a cada tipus de mapa dins d'un fitxer.
    name: str
    Z: np.ndarray | None = None
    units: str = None
    lims: NDArray[np.floating] | None = None
    xdata: dict = field(default_factory = dict)
    spectra: np.ndarray = None
    spectra_lims: list[float] = None
    color: Colors = None

    def __post_init__(self):
        if self.color is None: self.color = Colors(self.name)

        if self.Z is None and self.spectra is not None:
            self.spectra = ccd_correct(self.xdata['nm'], self.spectra)
            self.Z = np.nansum(self.spectra, axis = 2)
            self.spectra_lims = [round(self.xdata['nm'][0], 3), round(self.xdata['nm'][-1], 3)]

        if self.lims is None: self.update_lims()

    @property
    def ax_title(self):
        return f'{self.name} ({self.units})' if self.units else f'{self.name}'

    def update_lims(self):
        if self.name == 'Grain':
            self.lims = np.array([0, 1])
            return

        vmin, vmax = np.percentile(self.Z, [0.2, 99.8])

        # 3. Estructura match-case per a la lògica segons el tipus
        if self.name == 'Height':
            self.Z -= vmin
            vmax -= vmin
            vmin = 0.0

        # 4. Truncament de valors
        vmin = truncar_significatives(vmin, 2, cap_a='avall')
        vmax = truncar_significatives(vmax, 2, cap_a='amunt')

        # 5. Correcció per evitar límits idèntics
        if vmin == vmax:
            vmin -= 5
            vmax += 5

        self.lims = np.array([vmin, vmax])

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