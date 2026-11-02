"""Lector de fitxer .wsxm."""

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from classes.data import ChannelData, GeometryData, ObjectData

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from classes.protocols import FileDataDict

MAGIC1a = b"WSxM file copyright Nanotec Electronica"
MAGIC1b = b"WSxM file copyright WSxM solutions"
MAGIC2 = b"WSxM Image file"
HEADER_END = b"[Header end]\r\n"
SIZE_HEADER = b"Image header size:"


def _read_newline(data: bytes, idx: int) -> int | None:
    if data[idx : idx + 1] == b"\n":
        return idx + 1
    if data[idx : idx + 2] == b"\r\n":
        return idx + 2

    return None


def _check_magic(data: bytes) -> int | None:
    if data.startswith(MAGIC1a):
        ref_idx = len(MAGIC1a)
    elif data.startswith(MAGIC1b):
        ref_idx = len(MAGIC1b)
    else:
        return None

    idx = _read_newline(data, ref_idx)
    if idx is None:
        return None

    if not data[idx:].startswith(MAGIC2):
        return None

    idx += len(MAGIC2)

    return _read_newline(data, idx)


def _find_header_end(data: bytes) -> int:
    pos = data.find(HEADER_END)
    if pos == -1:
        msg = "No s'ha trobat [Header end]"
        raise ValueError(msg)
    return pos + len(HEADER_END)


def _parse_header(header_bytes: bytes) -> dict[str, str]:
    text = header_bytes.decode("latin-1")
    lines = text.splitlines()

    meta: dict[str, str] = {}
    section = None

    for element in lines:
        line = element.strip()
        if not line:
            continue

        if line.startswith("[") and line.endswith("]"):
            section = line.strip("[]")
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            full_key = f"{section}::{key}" if section else key
            meta[full_key] = value

    return meta


def _get_lateral_size(meta: dict[str, str]) -> tuple[float, float]:
    def _parse_value(s: str) -> float:
        parts = s.split()
        value = float(parts[0])
        unit = parts[1] if len(parts) > 1 else "m"
        factors = {"m": 1e6, "mm": 1e3, "um": 1, "μm": 1, "nm": 1e-3}

        return value * factors.get(unit, 1)

    x_amp = meta.get("Control::X Amplitude")
    y_amp = meta.get("Control::Y Amplitude")

    if x_amp is None or y_amp is None:
        msg = "No s'ha pogut determinar la mida del fitxer"
        raise ValueError(msg)

    xsize = _parse_value(x_amp)
    ysize = _parse_value(y_amp)

    return round(xsize, 3), round(ysize, 3)


def _read_data_field(buffer: bytes, xdim: int, ydim: int, dtype: str) -> NDArray[np.float32]:

    match dtype:
        case "double":
            data = np.frombuffer(buffer, dtype=np.float64).astype(np.float32)
        case "float":
            data = np.frombuffer(buffer, dtype=np.float32).copy()
        case "short":
            data = np.frombuffer(buffer, dtype=np.int16).astype(np.float32)
        case _:
            msg = f"Tipus desconegut: {dtype}"
            raise ValueError(msg)

    data = np.array(data.reshape((ydim, xdim)), dtype=np.float32)

    return np.flipud(np.fliplr(data))


def _read_wsxm(filepath: Path) -> tuple[NDArray[np.float32], tuple[int, int], dict[str, str]]:
    data = Path(filepath).read_bytes()

    idx = _check_magic(data)
    if idx is None:
        msg = "No és un fitxer WSxM vàlid"
        raise ValueError(msg)

    header_end = _find_header_end(data)
    header = data[:header_end]

    meta = _parse_header(header)

    # Extreure resolució
    try:
        xdim = int(meta["General Info::Number of columns"])
        ydim = int(meta["General Info::Number of rows"])
    except KeyError as err:
        msg_error = "No s'han pogut obtindre les dimensions del fitxer."
        raise KeyError(msg_error) from err

    dtype = meta.get("General Info::Image Data Type", "double")
    binary_data = data[header_end:]

    image = _read_data_field(binary_data, xdim, ydim, dtype)

    return image, (xdim, ydim), meta


def _convert_z_data(z: NDArray[np.float32], meta: dict[str, str]) -> tuple[NDArray[np.float32], str]:
    z_amp = meta.get("General Info::Z Amplitude")

    if not z_amp:
        return z, ""

    parts = z_amp.split()
    amplitude = float(parts[0])
    units = parts[1] if len(parts) > 1 else ""

    zmin = z.min()
    zmax = z.max()

    if zmax == zmin:
        return z, units

    z = (z * amplitude / (zmax - zmin)).astype(np.float32)

    return z, units


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
    type_map = {".top": "Height", ".Auxfeed": "CPD", ".ch15": "Mag", ".ch16": "Phase"}
    name = type_map.get(filepath.suffix, filepath.suffix)

    raw_z, dim, meta = _read_wsxm(filepath)
    size = _get_lateral_size(meta)
    z, units = _convert_z_data(raw_z, meta)

    channel: dict[str, ChannelData] = {name: ChannelData(name=name, data=z, units=units)}

    return {
        "channel": channel,
        "geometry": GeometryData(dim, size),
        "objects": ObjectData(),
    }
