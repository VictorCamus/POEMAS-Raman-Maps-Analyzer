import h5py
from classes import ChannelData

def load(file_list):
    file = file_list[0]
    with h5py.File(file , "r") as f:
        return read(f)

def read(f):
    Nx, Ny = f.attrs["Nx"], f.attrs["Ny"]
    midaX, midaY = f.attrs["midaX"], f.attrs["midaY"]

    channels = {}

    for tipus in f["channels"]:
        cg = f["channels"][tipus]

        Z = cg["Z"][:]
        lims = cg["lims"][:] if "lims" in cg else None

        channels[tipus] = ChannelData(tipus=tipus, name=cg.attrs["name"], Z=Z, lims=lims, mult=cg.attrs["mult"])
    
    return channels, (Nx, Ny), (midaX, midaY)