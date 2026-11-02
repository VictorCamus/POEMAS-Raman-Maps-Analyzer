"""Lector de fitxers .txt amb format LabSpec."""

from tkinter import messagebox
from typing import TYPE_CHECKING, cast

import numpy as np

import process.converter as conv
from classes.data import ChannelData, GeometryData, ObjectData, SpecData

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

    from classes.protocols import FileDataDict, SpecUnits


def _read(filepath: Path) -> tuple[NDArray[np.float32], float, SpecUnits]:
    laser: float | None = None
    xunits: SpecUnits | None = None

    with filepath.open(encoding="ANSI") as f:
        is_laser = True
        for linia in f:
            if linia.startswith("#Laser") and is_laser:
                valor = linia.split("=", 1)[-1].strip()
                laser = float(valor[:3])
                is_laser = False

            elif linia.startswith("#AxisUnit[1]="):
                valor = linia.split("=", 1)[1].strip()

                if valor not in {"eV", "nm", "1/cm"}:
                    msg = f"No s'ha pogut llegir {valor} com a unitats de l'espectre"
                    messagebox.showerror("Fitxer Raman amb metadades incompletes", msg)

                    raise ValueError(msg)

                xunits = cast("SpecUnits", valor)

    if laser is None:
        msg = "No s'ha trobat la longitud d'ona làser"
        messagebox.showerror("Fitxer Raman amb metadades incompletes", msg)

        raise ValueError(msg)

    if xunits is None:
        msg = "No s'ha trobat la unitats dels espectres"
        messagebox.showerror("Fitxer Raman amb metadades incompletes", msg)

        raise ValueError(msg)

    dades = np.genfromtxt(filepath, delimiter="\t", dtype=np.float32)

    return dades, laser, xunits


def load(filepath: Path) -> FileDataDict:
    """Carrega, llig i converteix les dades d'un fitxer .xyz a FileDataDict.

    Parameters
    ----------
    filepath: Path
        Camí del fitxer

    Returns
    -------
    dict: FileDataDict
        Dades preparades per a ser treballades pel programa.

    """
    dades, laser, xunits = _read(filepath)

    q = dades[0, 2:]
    y = np.unique(dades[1:, 0])
    x = np.unique(dades[1:, 1])

    dim = len(x), len(y)
    rawdata: NDArray[np.float32] = dades[1:, 2:]

    shape = rawdata.shape
    spec_length: int = int(shape[1])

    spectra = rawdata.astype(np.uint16) if np.nanmax(rawdata) <= np.iinfo(np.uint16).max else rawdata.astype(np.uint32)
    spectra = spectra.reshape(dim[1], dim[0], spec_length)
    spectra = np.flip(spectra, axis=0).copy()

    mida = (x[1] - x[0]) * dim[0], (y[1] - y[0]) * dim[1]

    xdata: dict[str, NDArray[np.float32]] = {}
    channels: dict[str, ChannelData] = {}

    match xunits:
        case "nm":
            xdata["nm"] = q
            xdata["eV"] = conv.nm_to_energy(q)
            xdata["1/cm"] = conv.nm_to_raman(q, laser)

        case "eV":
            xdata["nm"] = conv.energy_to_nm(q)
            xdata["eV"] = q
            xdata["1/cm"] = conv.energy_to_raman(q, laser)

        case "1/cm":
            xdata["nm"] = conv.raman_to_nm(q, laser)
            xdata["eV"] = conv.raman_to_energy(q, laser)
            xdata["1/cm"] = q

    z = np.nansum(spectra, axis=2, dtype=float)

    channels["Spectra"] = ChannelData(name="SpecData", data=z, units="cts",
                          spectra=SpecData(xdata=xdata, raw_ydata=spectra, units=xunits, laser=laser))

    return {"channel": channels, "geometry": GeometryData(dim=dim, base_size=mida), "objects": ObjectData()}
