"""Lector de fitxers .aist."""

import struct
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypedDict

import numpy as np

from classes.data import ChannelData, GeometryData, ObjectData, SpecData
from process.converter import nm_to_energy, nm_to_raman

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

    from classes.protocols import FileDataDict


MAP_CHANNELS = {"Height(Sen)": "Height", "Mag": "Mag", "Phase": "Phase", "CPD[2]": "CPD"}

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_IEND = b"IEND"


# =========================================================
# PROTOCOLS
# =========================================================


@dataclass
class AistState:
    """Protocol bàsic de les dades obtingudes d'un fitxer AIST."""

    channels: dict[str, ChannelData] = field(default_factory=dict)
    geometry: GeometryData | None = None
    objects: ObjectData = field(default_factory=ObjectData)
    type_name: str | None = None
    raw_spectra: NDArray[np.float32] | None = None


class RasterChannel(TypedDict):
    """Protocol d'un canal raster."""

    data: NDArray[np.float32]
    dim: tuple[int, int]
    size: tuple[float, float]
    units: AxisUnits
    mask: NDArray[np.bool_]


class CurveChannel(TypedDict):
    """Protocol d'una corba."""

    x: NDArray[np.float32]
    y: NDArray[np.float32]
    units: AxisUnits


class SpectroChannel(TypedDict):
    """Protocol d'un canal espectral."""

    data: NDArray[np.float32]
    dim: tuple[int, int]
    size: tuple[float, float]
    units: AxisUnits
    mask: NDArray[np.bool_]
    xdata: NDArray[np.float32]
    spectra: NDArray[np.uint16 | np.uint32]
    laser: float


class AxisUnits(TypedDict):
    """Protocol d'unitats."""

    x: str
    y: str
    z: str


# =========================================================
# BUFFER READER (equivalent a punters en C)
# =========================================================


class BufferReader:
    """Classe que conté un conjunt de bytes i indica la posició actual de les dades."""

    def __init__(self, data: bytes) -> None:
        """Guarda les dades i inicia la posició.

        Parameters
        ----------
        data: bytes
            Dades en format bytes.

        """
        self.data: bytes = data
        self.pos: int = 0

    def remaining(self) -> int:
        """Indica quants bytes queden per llegir.

        Returns
        -------
        remaining: int
            Dades restants.

        """
        return len(self.data) - self.pos

    def take(self, size: int) -> bytes:
        """Retorna els següents `size` bytes i avança la posició.

        Parameters
        ----------
        size: int
            Mida de la cadena

        Returns
        -------
        data: bytes
            Cadena de bytes

        Raises
        ------
        ValueError
            Si la longitud triada és major que les dades restants.

        """
        if size < 0 or self.remaining() < size:
            msg = "No hi ha prou dades per a llegir."
            raise ValueError(msg)

        start = self.pos
        self.pos += size
        return self.data[start:self.pos]

    def read_uint8(self) -> int:
        """Llig un enter de 8 bits.

        Returns
        -------
        value: int

        """
        return int(struct.unpack(">B", self.take(1))[0])

    def read_int32(self) -> int:
        """Llig un enter de 32 bits.

        Returns
        -------
        value: int

        """
        return int(struct.unpack(">i", self.take(4))[0])

    def read_int64(self) -> int:
        """Llig un enter de 64 bits.

        Returns
        -------
        value: int

        """
        return int(struct.unpack(">q", self.take(8))[0])

    def read_double(self) -> float:
        """Llig un nombre decimal de 64 bits.

        Returns
        -------
        value: float

        """
        return float(struct.unpack(">d", self.take(8))[0])

    def read_bool(self) -> bool:
        """Llig un booleà de 8 bits.

        Returns
        -------
        value: bool

        """
        return self.read_uint8() != 0

    def read_string(self) -> str:
        """Llig un vector de text encapçalat per la mida 'length'.

        Returns
        -------
        value: str

        """
        length = self.read_int32()

        if length == 0:
            return ""

        return self.take(length).decode("utf-16-be")

    def bool_array(self) -> NDArray[np.bool_]:
        """Llig una màscara booleana encapçalada per la mida 'length'.

        Returns
        -------
        mask: NDArray[np.bool_]

        """
        length = self.read_int32()
        return np.frombuffer(self.take(length), dtype=np.bool_)

    def float32_array(self) -> NDArray[np.float32]:
        """Llig un vector decimal de 32 bits encapçalat per la mida 'length' i el converteix a np.float32.

        Returns
        -------
        array: NDArray[np.bool_]

        """
        length = self.read_int32()
        return np.frombuffer(self.take(length), dtype=np.float32)

    def float64_array(self) -> NDArray[np.float64]:
        """Llig un vector decimal de 64 bits encapçalat per la mida 'length' i el converteix a np.float32.

        Returns
        -------
        array: NDArray[np.bool_]

        """
        length = self.read_int32()
        return np.frombuffer(self.take(length), dtype=np.float64)

    def sub_buffer(self) -> BufferReader | None:
        """Llig una subsecció encapçalada per la mida 'length'.

        Returns
        -------
        sub: BufferReader | None
            Subobjecte de la classe o None si la longitud és -1 (flag).

        Raises
        ------
        ValueError
            Si la longitud triada és major que les dades restants o menor que zero.

        """
        length = self.read_int32()

        if length == -1:
            return None

        if length < 0:
            msg = f"Longitud invàlida: {length}"
            raise ValueError(msg)

        if self.remaining() < length:
            msg = "El bloc supera les dades disponibles."
            raise ValueError(msg)

        start = self.pos
        self.pos += length

        return BufferReader(self.data[start:start + length])

    def require_end(self) -> None:
        """Comprova que no queden dades sense llegir.

        Raises
        ------
        ValueError
            Si encara no s'han llegit totes les dades

        """
        if self.remaining():
            msg = f"Queden {self.remaining()} bytes sense llegir."
            raise ValueError(msg)


# =========================================================
# FUNCIONS AUXILIARS
# =========================================================


def _extract_units(label: str) -> str:
    """Extrau les unitats del text AIST.

    Parameters
    ----------
    label: str
        Vector de text

    Returns
    -------
    units: str
        Unitats corresponents

    """
    if "[" in label and "]" in label:
        return label.split("[")[1].split("]", maxsplit=1)[0]
    return label


def _read_dim(sub: BufferReader) -> tuple[int, int]:
    """Extrau les dimensions de la matriu.

    Returns
    -------
    xdim:int
        Dimensió X de la matriu
    ydim: int
        Dimensió Y de la matriu

    """
    xdim = sub.read_int32()
    ydim = sub.read_int32()

    return xdim, ydim


def _read_size(sub: BufferReader) -> tuple[float, float]:
    """Extrau la mida de cada dimensió.

    Returns
    -------
    width: str
        Amplària de la imatge
    height: str
        Altura de la imatge

    """
    left = sub.read_double()
    right = sub.read_double()
    bottom = sub.read_double()
    top = sub.read_double()

    return right - left, top - bottom


def _read_units(sub: BufferReader) -> AxisUnits:
    """Extrau les unitats de la imatge.

    Returns
    -------
    units: dict{"x", "y", "z"}
        Dimensions de les coordenades X, Y i Z.

    """
    xunits = _extract_units(sub.read_string())
    yunits = _extract_units(sub.read_string())
    zunits = _extract_units(sub.read_string())

    return {"x": xunits, "y": yunits, "z": zunits}


def _read_xdata(sub: BufferReader) -> tuple[float, NDArray[np.float32], int]:
    """Llig el vector de valors associat a un espectre.

    Parameters
    ----------
    sub: BufferReader
        Subclasse de bytes

    Returns
    -------
    laser: float
        Longitud d'ona d'il·luminació si escau, si no és 100.0 per predeterminat.
    xdata: NDArray[np.float32]
        Vector de dades
    nchan:
        Nombre de dades del vector

    """
    sub.read_int32()
    laser = sub.read_double()

    _ = sub.read_double()
    _ = sub.read_double()
    _ = sub.read_int32()
    _ = sub.read_int32()

    nchan = sub.read_int32()
    xdata = sub.float32_array()

    return laser, xdata, nchan


# =========================================================
# TYPE READERS
# =========================================================


def read_aist_raster(sub: BufferReader | None) -> tuple[str, RasterChannel]:
    """Llig un canal amb format raster.

    Parameters
    ----------
    sub: BufferReader | None
        Subconjunt de bytes del lector principal

    Returns
    -------
    name: str
        Nom del canal
    channel: RasterChannel
        Dades del canal raster.

    Raises
    ------
    ValueError
        Si no hi ha cap data al raster.

    """
    if sub is None:
        msg = "No hi ha informació al raster."
        raise ValueError(msg)

    _flag = sub.read_int32()
    name = sub.read_string()
    _desc = sub.read_string()
    _int = sub.read_int32()

    channel = read_data_raster(sub)
    sub.require_end()

    return name, channel


def read_data_raster(sub: BufferReader) -> RasterChannel:
    """Llig les dades d'un raster.

    Returns
    -------
    channel: RasterChannel
        Dades del canal

    """
    dim = _read_dim(sub)
    size = _read_size(sub)
    units = _read_units(sub)

    values = np.array(sub.float64_array(), dtype=np.float32)
    values = values.reshape((dim[1], dim[0]))

    mask = sub.bool_array()
    mask = mask.reshape((dim[1], dim[0]))

    _flag = sub.read_int32()  # -1

    return {"data": values,
            "dim": dim,
            "size": size,
            "units": units,
            "mask": mask}


def read_aist_curve(sub: BufferReader | None) -> CurveChannel:
    """Llig un corba AIST.

    Parameters
    ----------
    sub: BufferReader | None
        Subconjunt de bytes del lector principal

    Returns
    -------
    channel: RasterChannel
        Dades del canal raster.

    Raises
    ------
    ValueError
        Si no hi ha cap data a la corba.

    """
    if sub is None:
        msg = "No hi ha informació a la corba."
        raise ValueError(msg)

    _flag = sub.read_int32()
    _name = sub.read_string()
    _desc = sub.read_string()

    resolution = sub.read_int32()

    values = np.array(sub.float64_array(), np.float32)
    _view = sub.float64_array()  # view data ignorat

    xunits = sub.read_string()
    yunits = sub.read_string()

    return {"x": values[:resolution],
            "y": values[resolution:],
            "units": {"x": _extract_units(xunits),
                      "y": _extract_units(yunits),
                      "z": ""}}


def read_data_spectra(sub: BufferReader | None, spec: NDArray[np.float32]) -> SpectroChannel:
    """Llig les dades relacionades amb un fitxer d'espectres arbitrari.

    Parameters
    ----------
    sub: BufferReader | None
        Subclasse de bytes
    spec: NDArray[np.float32]
        Dades crues de l'espectre

    Returns
    -------
    channel: SpectroChannel
        Dades d'un canal espectral

    Raises
    ------
    ValueError
        Si no hi ha dades a llegir

    """
    if sub is None:
        msg = "No s'han trobat dades relacionades amb l'espectre"
        raise ValueError(msg)

    laser, xdata, nchan = _read_xdata(sub)

    _flag = sub.read_int32()  # -1
    _name = sub.read_string()
    _desc = sub.read_string()
    _value = sub.read_int32()

    dim = _read_dim(sub)
    size = _read_size(sub)
    units = _read_units(sub)

    mask = sub.bool_array().reshape(dim[1], dim[0])

    spec = spec.reshape(dim[1], dim[0], nchan)
    spec = np.maximum(spec, 0)
    spectra = spec.astype(np.uint16) if np.nanmax(spec) <= np.iinfo(np.uint16).max\
            else spec.astype(np.uint32)

    data = np.nansum(spec, axis=2, dtype=float)

    read_spectro_maps(sub, dim)
    read_metadata(sub)

    return {"data": data,
            "dim": dim,
            "size": size,
            "units": units,
            "mask": mask,
            "xdata": xdata,
            "spectra": spectra,
            "laser": laser}


# =========================================================
# TYPE READERS
# =========================================================


def read_scan_properties(sub: BufferReader) -> dict[str, bool | int | float]:
    """Llig informació relativa a l'operació de l'equip i algorismes aplicats.

    Parameters
    ----------
    sub: BufferReader
        Subclasse de bytes

    Returns
    -------
    info: dict[str, bool | int | float]
        Diccionari amb la informació llegida

    Raises
    ------
    NotImplementedError
        Si existeix un format desconegut

    """
    info = {}
    value: bool | int | float

    for _ in range(sub.read_int32()):
        sub.read_string()

    for _ in range(sub.read_int32()):
        key = sub.read_string()
        type_id = sub.read_int32()
        _ = sub.read_bool()
        match type_id:
            case 1:
                value = sub.read_bool()
            case 2:
                value = sub.read_int32()
            case 6:
                value = sub.read_double()

            case _:
                msg = f"Tipus desconegut: {type_id}"
                raise NotImplementedError(msg)

        info[key] = value

    _flag = sub.read_int32()

    return info


def read_metadata(r: BufferReader) -> dict[str, dict[str, str]]:
    """Llig la metadata d'un bloc.

    Parameters
    ----------
    r: BufferReader
        Bloc de bytes.

    Returns
    -------
    metadata: dict[str, dict[str, str]]
        Dades llegides

    Raises
    ------
    ValueError
        Si l'estructura de les metadades és diferent de l'esperada.

    """
    metadata = {}

    default1 = r.read_string()
    metadata[default1] = {"description": r.read_string(),
                         "value": str(r.read_int32())}

    for _ in range(r.read_int32()):
        key = r.read_string()
        metadata[key] = {"description": r.read_string(),
                         "value": r.read_string()}

        separator = r.read_bool()
        if separator:
            msg = "Separador inesperat."
            raise ValueError(msg)

    _flag = r.read_int32()

    return metadata


def read_png(sub: BufferReader | None) -> bytes | None:
    """Llig una imatge amb format PNG.

    Parameters
    ----------
    sub: BufferReader | None
        Subclasse de bytes

    Returns
    -------
    png: bytes | None
        Retorna el PNG si existeix, si no retorna None

    Raises
    ------
    ValueError
        Si no conté la signatura d'un PNG

    """
    if sub is None:
        return None

    start = sub.pos
    sub.read_int32()
    if sub.take(8) != PNG_SIGNATURE:
        msg = "No és un PNG."
        raise ValueError(msg)

    while True:
        length = sub.read_int32()
        chunk_type = sub.take(4)

        _chunk_data = sub.take(length + 4)

        if chunk_type == b"IEND":
            sub.require_end()
            return sub.data[start:sub.pos]


def read_numbers(sub: BufferReader) -> None:
    """Llig números. La seua funció encara no està ben determinada.

    Parameters
    ----------
    sub: BufferReader
        Subclasse de bytes

    """
    for _ in range(4):
        sub.read_double()

    for _ in range(sub.read_int32()):
        sub.read_double()

    for _ in range(sub.read_int32()):
        sub.read_double()

    for _ in range(5):
        sub.read_int32()

    sub.read_bool()  # False

    sub.require_end()


def read_spectro_maps(sub: BufferReader, dim: tuple[int, int]) -> None:
    """Lector de mapes espectrals. La seua funció encara no hi està ben determinada.

    Parameters
    ----------
    sub: BufferReader
        Subclasse de bytes
    dim: tuple[int, int]
        Dimensions X i Y de les màscares

    """
    for _ in range(3):
        _ = sub.float32_array().reshape(dim[1], dim[0])

    _dim = _read_dim(sub)
    _size = _read_size(sub)

    sub.read_int32()
    sub.read_int32()
    _dim2 = _read_dim(sub)

    sub.read_int32()
    sub.read_int32()
    _dim3 = _read_dim(sub)

    _flag = sub.read_int32()


# =========================================================
# INFO READER
# =========================================================


def read_info_raster(sub: BufferReader | None) -> None:
    """Llig la informació completa relativa a un raster.

    Parameters
    ----------
    sub: BufferReader | None
        Subclasse de bytes. En cas de no haver-hi dades, retorna sense fer-hi res

    """
    if sub is None:
        return

    while sub.remaining() != 0:
        read_info_parameters(sub.sub_buffer())
        read_png(sub.sub_buffer())


def read_info_parameters(sub: BufferReader | None) -> None:
    """Llig tota la informació relativa a les dades d'un raster.

    Parameters
    ----------
    sub: BufferReader | None
        Subclasse de bytes. En cas de no haver-hi dades, retorna sense fer-hi res

    """
    if sub is None:
        return

    read_scan_properties(sub)
    read_metadata(sub)

    sub2 = sub.sub_buffer()
    if sub2 is not None:
        read_numbers(sub2)

    _dim = _read_dim(sub)
    _size = _read_size(sub)
    _flag = sub.read_int64()  # -1
    _end = sub.read_int64()  # 0

    sub.require_end()


def read_info_spectra(sub: BufferReader | None, spectra: NDArray[np.float32]) -> SpectroChannel:
    """Llig la informació completa relativa a un raster.

    Parameters
    ----------
    sub: BufferReader | None
        Subclasse de bytes. En cas de no haver-hi dades, retorna sense fer-hi res
    spectra: NDArray[np.float32]
        Dades creus de l'espectre

    Returns
    -------
    channel: SpectroChannel
        Dades d'un canal espectral

    Raises
    ------
    ValueError
        Si no hi ha dades a llegir

    """
    if sub is None:
        msg = "No s'ha pogut llegir les dades de l'espectre"
        raise ValueError(msg)

    channel = read_data_spectra(sub.sub_buffer(), spectra)
    read_png(sub.sub_buffer())

    return channel


# =========================================================
# FUNCIONS PRINCIPALS
# =========================================================


def read_aist_tree(r: BufferReader, state: AistState) -> None:
    """Llig els arbres de dades del lector principal.

    Parameters
    ----------
    r: BufferReader
        Subclasse de bytes
    state: AistState
        Dades principals del fitxer AIST

    Raises
    ------
    NotImplementedError
        Si cap lector de dades no pot ser identificat

    """
    is_data = r.read_bool()

    if is_data:
        type_name = r.read_string()

        if state.type_name is None:
            state.type_name = type_name

        match type_name:
            case "raster":
                name, channel = read_aist_raster(r.sub_buffer())
                if name != "CPD" and (name == "CPD[2]" or not name.endswith("[2]")):

                    tipus = MAP_CHANNELS.get(name, name)

                    state.channels[tipus] = ChannelData(name=tipus, data=channel["data"],
                                                    units=channel["units"]["z"])

                    if state.geometry is None:
                        state.geometry = GeometryData(channel["dim"], channel["size"])

            case "curve":
                _curve = read_aist_curve(r.sub_buffer())
                msg = "El programa no està dissenyat per a llegir corbes encara."
                raise NotImplementedError(msg)
            case "spectro":
                r.pos += 4  # Correcció per un error de format
                state.raw_spectra = r.float32_array()

            case "curveMap":
                state.raw_spectra = r.float32_array()

            case _:
                msg = f"Classe d'arxiu desconeguda: {type_name}"
                raise NotImplementedError(msg)

    _name = r.read_string()
    nchildren = r.read_int32()

    for _ in range(nchildren):
        read_aist_tree(r, state)


def load(filepath: Path) -> FileDataDict:
    """Carrega el fitxer AIST i el converteix a FileDataDict.

    Parameters
    ----------
    filepath: Path
        Camí del fitxer

    Returns
    -------
    dict: FileDataDict
        Dades preparades per a ser treballades pel programa.

    Raises
    ------
    ValueError
        Si hi ha cap error de lectura o falten dades

    """
    reader = BufferReader(filepath.read_bytes())
    state = AistState()

    read_aist_tree(reader, state)

    if not state.channels and state.raw_spectra is None:
        msg = "Error en obrir el fitxer: No s'han trobat dades."
        raise ValueError(msg)

    if state.type_name not in {"spectro", "curveMap"}:
        read_info_raster(reader.sub_buffer())

    else:
        if state.raw_spectra is None:
            msg = "Falten les dades espectrals."
            raise ValueError(msg)

        channel = read_info_spectra(reader.sub_buffer(), state.raw_spectra)
        if state.type_name == "spectro":
            xdata: dict[str, NDArray[np.float32]] = {
                "nm": channel["xdata"],
                "eV": nm_to_energy(channel["xdata"]),
                "1/cm": nm_to_raman(channel["xdata"], channel["laser"])}
            state.channels["SpecData"] = ChannelData(name="SpecData", data=channel["data"], units="cts",
                                    spectra=SpecData(xdata=xdata, raw_ydata=channel["spectra"],
                                                     units="nm", laser=channel["laser"]))

        state.geometry = GeometryData(dim=channel["dim"], base_size=channel["size"])
        state.objects = ObjectData()

    sub = reader.sub_buffer()
    if sub is not None:
        while sub.remaining() != 0:
            read_png(sub.sub_buffer())

        sub.require_end()

    reader.require_end()

    if state.geometry is None:
        msg = "No s'ha pogut llegir la geometria del fitxer"
        raise ValueError(msg)

    return {
        "channel": state.channels,
        "geometry": state.geometry,
        "objects": state.objects,
    }
