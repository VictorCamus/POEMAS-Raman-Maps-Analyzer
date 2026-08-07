from dataclasses import dataclass, field
from typing import Dict
import numpy as np

from drawing.arrows import FletxaEstatica
from process.converter import pixel_to_coords

@dataclass
class ObjectData:
    profiles: Dict[int, ProfileData] = field(default_factory=dict)
    mask: object = None

@dataclass
class ProfileData:
    line: list[tuple[int, int]] | None = None
    length: float | None = None

    @property
    def lims(self):
        return self.line[0], self.line[-1]

    def rotate(self, N, rotation, flip):
        Nx, Ny = N
        transformed = []

        for x, y in self.line:
            match rotation:
                case 0: pass
                case 1: x, y = y, Ny - 1 - x
                case 2: x, y = Nx - 1 - x, Ny - 1 - y
                case 3: x, y = Nx - 1 - y, x

            if flip: x = Nx - 1 - x

            transformed.append((x, y))

        self.line = transformed

@dataclass
class ProfilePlot:
    profiles: dict[int, ProfileData]
    ax: object
    geometry: object

    def __post_init__(self):
        self.colors = ('r', 'b', 'g', 'orange', 'y', 'cyan', 'pink', 'k')
        self.create_arrows()

    def create_arrows(self):
        self.arrow = {num: self.add_arrow(num, prof.lims) for num, prof in self.profiles.items()}

    def add_arrow(self, num, lims):
        start, end = pixel_to_coords(lims, self.geometry.N, self.geometry.midaBase)
        return FletxaEstatica(self.ax, start, end, self.geometry.midaBase, num + 1, self.colors[num % 8])

    def update(self):
        for num, prof in self.profiles.items():
            if num not in self.arrow:
                self.arrow[num] = self.add_arrow(num, prof.lims)
            else:
                start, end = pixel_to_coords(prof.lims, self.geometry.N, self.geometry.midaBase)
                self.arrow[num].update(start, end)

    def elimina(self):
        for arrow in self.arrow.values(): arrow.elimina()
        self.arrow.clear()

    def plot(self, num, ax, data):
        prof = self.profiles[num]

        coords = np.asarray(prof.line)
        x_vals = coords[:, 0]
        y_vals = coords[:, 1]

        dades = data[y_vals, x_vals]
        zmin, zmax = dades.min(), dades.max()
        diff = (zmax - zmin) / 15
        line = np.linspace(0, prof.length, len(dades))

        profile, = ax.plot(line, dades, color=self.colors[num % 8])
        ax.set_xlim(0, prof.length)
        ylims = (round(zmin - diff, 0), round(zmax + diff, 0))
        ax.set_ylim(*ylims)

        return line, dades, profile