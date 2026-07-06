import numpy as np
from classes import ChannelData

def load(file_list):
    channels = {}

    for file in file_list:
        _, tipus = file.stem.rsplit(' - ', 1)  # "sample - AFM" → "AFM"

        data = np.loadtxt(file, delimiter='\t')
        x, y, z = data[:, 0], data[:, 1], data[:, 2]

        Ny = sum(x == x[0]); Nx = len(x) // Ny

        shiftX = abs(x[1] - x[0]) * 1e6; shiftY = abs(y[Nx] - y[0]) * 1e6
        midaX = round(Nx * shiftX, 3); midaY = round(Ny * shiftY, 3)

        Z = np.flipud(z.reshape(Ny, Nx))

        lims_file = file.with_name(f'{tipus} - lims.txt')
        lims = np.loadtxt(lims_file) if lims_file.exists() else None

        channels[tipus] = ChannelData(tipus=tipus, name=tipus, Z=Z, lims=lims, mult=True)

    return channels, [Nx, Ny], (midaX, midaY)