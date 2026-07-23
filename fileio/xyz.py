from numpy import loadtxt, flipud
from classes import ChannelData

def load(file_list, fileclass):
    channels = {}

    for file in file_list:
        _, tipus = file.stem.rsplit(' - ', 1)  # "sample - AFM" → "AFM"

        data = loadtxt(file, delimiter='\t')
        x, y, z = data[:, 0], data[:, 1], data[:, 2]

        Ny = sum(x == x[0]); Nx = len(x) // Ny

        shiftX = abs(x[1] - x[0]) * 1e6; shiftY = abs(y[Nx] - y[0]) * 1e6
        mida = round(Nx * shiftX, 3), round(Ny * shiftY, 3)

        Z = flipud(z.reshape(Ny, Nx))
        N = Nx, Ny

        lims_file = file.with_name(f'{tipus} - lims.txt')
        lims = loadtxt(lims_file) if lims_file.exists() else None

        channels[tipus] = ChannelData(name=tipus, Z=Z, lims=lims)

    data = {'channel': channels, 'N': N, '_midaBase': mida}
    return fileclass(**data)