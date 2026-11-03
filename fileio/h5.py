"""Lector i escriptor de fitxers H5 i sessions HDF5."""

import annotationlib
from dataclasses import fields, is_dataclass
from types import UnionType
from typing import TYPE_CHECKING, Union, cast, get_args, get_origin

import h5py
import numpy as np

from classes.data import FileData

if TYPE_CHECKING:
    from pathlib import Path

    from classes.protocols import FileDataDict
    from classes.views import FileView

    type IntSlice = slice[
        int,
        int,
        int | None,
    ]

MAP_OLD_TYPES: dict[str, str] = {"Z": "data",
                                "N": "dim",
                                "A": "amp",
                                "npixels": "dim",
                                "midaBase": "base_size",
                                "CCD": "ccd",
                                "CCD_active": "ccd_active",
                                "limInf": "lim_inf",
                                "limSup": "lim_sup",
                                "ydata": "raw_ydata"}


def load(filepath: Path) -> FileDataDict:
    """Carrega el fitxer h5, associat a un fitxer únic, i el converteix a FileDataDict.

    Parameters
    ----------
    filepath: Path
        Camí del fitxer

    Returns
    -------
    dict: FileDataDict
        Dades preparades per a ser treballades pel programa.

    """
    with h5py.File(str(filepath), "r") as f:
        return cast("FileDataDict", read_data(f, FileData))


def load_session(filepath: Path) -> dict[str, FileDataDict]:
    """Carrega el fitxer hdf5, associat a una sessió de treball, i el converteix en un diccionari FileDataDict.

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
    TypeError
        Si els fitxers guardats no són grups d'H5.

    """
    with h5py.File(str(filepath), "r") as f:
        order = [str(key) for key in cast("list[str]", f.attrs["file_order"])]
        data: dict[str, FileDataDict] = {}

        for key in order:
            obj = f[key]

            if not isinstance(obj, h5py.Group):
                msg = f"{key!r} no és un grup HDF5."
                raise TypeError(msg)

            data[key] = cast(
                "FileDataDict",
                read_data(obj, FileData),
            )

        return data


def to_python(value: object) -> object:
    """Funció per a poder llegir booleans i passar-los a format numpy.

    Parameters
    ----------
    value: object
        Valor a transformar

    Returns
    -------
    new_value: object
        Valor transformat a format numpy, si escau.

    """
    return value.item() if isinstance(value, np.generic) else value


def read_object[T](group: h5py.Group, fileclass: type[T]) -> T:
    """Llig un objecte H5 i el converteix en una instància de la classe.

    Parameters
    ----------
    group : h5py.Group
        Grup H5 que conté l'objecte.
    fileclass : type[T]
        Classe que es crearà amb les dades llegides.

    Returns
    -------
    T
        Objecte reconstruït a partir de les dades del grup H5.

    """
    return fileclass(**read_data(group, fileclass))


def read_data(group: h5py.Group, fileclass: type) -> dict[str, object]:
    """Llig les dades d'un objecte des d'un grup H5.

    Parameters
    ----------
    group : h5py.Group
        Grup H5 que conté les dades.
    fileclass : type
        Classe que descriu l'estructura de les dades.

    Returns
    -------
    data: dict[str, object]
        Diccionari amb les dades llegides.

    Raises
    ------
    TypeError
        No hi ha cap anotació per a un atribut de la classe

    """
    annotations = annotationlib.get_annotations(
        fileclass,
        format=annotationlib.Format.VALUE,
    )

    data: dict[str, object] = {}

    # Atributs HDF5.
    for old_name, value in group.attrs.items():
        name = MAP_OLD_TYPES.get(old_name, old_name)
        annotation = annotations.get(name)

        # Pot haver-hi atributs auxiliars que no formen part de l'objecte.
        if annotation is None:
            continue

        data[name] = read_attribute(value, annotation)

    # Datasets i grups HDF5.
    for old_name in group:
        name = MAP_OLD_TYPES.get(old_name, old_name)
        annotation = annotations.get(name)

        if annotation is None:
            msg = f"No hi ha anotació per al camp {name} de la classe {fileclass.__name__}"
            raise TypeError(msg)

        data[name] = read_value(group, old_name, annotation)

    return data


def read_value(group: h5py.Group, name: str, annotation: object) -> object:
    """Llig un objecte d'h5py segons la seua anotació.

    Parameters
    ----------
    group: h5py.Group
        Grup al que pertany
    name: str
        Referència de l'objecte
    annotation: object
        Anotació de l'objecte indica en la classe principal

    Returns
    -------
    result: object
        Objecte llegit pel programa

    Raises
    ------
    TypeError
        Si l'objecte no es pot llegir pel programa
    KeyError
        Si la referència no pertany a cap objecte

    """
    annotation = unwrap_optional(annotation)

    if name in group:
        obj = group[name]

        if isinstance(obj, h5py.Dataset):
            return obj[:]

        if isinstance(obj, h5py.Group):
            return read_group_value(obj, annotation)

        msg = f"Tipus HDF5 no suportat per {name!r}: {type(obj).__name__}"
        raise TypeError(msg)

    if name in group.attrs:
        return read_attribute(group.attrs[name], annotation)

    msg = f"No s'ha trobat {name!r} en el grup HDF5."
    raise KeyError(msg)


def read_group_value(group: h5py.Group, annotation: object) -> object:
    """Interpreta un grup HDF5 segons l'anotació.

    Parameters
    ----------
    group: h5py.Group
        grup h5
    annotation: object
        Classe d'objecte Python al que pertany el grup

    Returns
    -------
    result: object
        Objecte llegit

    Raises
    ------
    TypeError
        Si cap seqüència de valors no conté l'atribut values.

    """
    origin = get_origin(annotation)

    if origin is dict:
        return read_dict(group, annotation)

    if origin in {tuple, list}:
        if "values" not in group.attrs:
            msg = "El grup d'una seqüència no conté l'atribut 'values'."
            raise TypeError(msg)

        return read_sequence(group.attrs["values"], annotation)

    if annotation is slice:
        return slice(
            to_python(group.attrs.get("start")),
            to_python(group.attrs.get("stop")),
            to_python(group.attrs.get("step")),
        )

    if not isinstance(annotation, type):
        msg = f"L'anotació no és un tipus de classe: {annotation!r}"
        raise TypeError(msg)

    return read_object(group, annotation)


def read_dict(group: h5py.Group, annotation: object) -> dict[object, object]:
    """Llig un diccionari HDF5 segons l'anotació dels seus elements.

    Parameters
    ----------
    group: h5py.Group
        grup h5
    annotation: object
        Classe d'objecte Python al que pertany el grup

    Returns
    -------
    result: dict[object, object]
        Objecte llegit com un diccionari

    Raises
    ------
    TypeError
        Si no té estructura de diccionari
        Si les anotacions de les claus no són un identificador de classe
        Si el diccionari conté vectors de numpy però els atributs no coincideixen

    """
    args = get_args(annotation)

    if len(args) != 2:
        msg = f"El diccionari ha d'estar anotat amb clau i valor: {annotation!r}"
        raise TypeError(msg)

    key_annotation, value_annotation = args

    if not isinstance(key_annotation, type):
        msg = f"L'anotació de la clau no és un tipus: {key_annotation!r}"
        raise TypeError(msg)

    # `save_dict()` guarda l'ordre explícitament.
    if "order" in group.attrs:
        raw_keys = group.attrs["order"]

        if not isinstance(raw_keys, np.ndarray):
            msg = "L'atribut 'order' d'un diccionari HDF5 no és un ndarray."
            raise TypeError(msg)

        keys = [str(to_python(key)) for key in raw_keys]

    else:
        # Compatibilitat amb fitxers antics sense `order`.
        keys = list(group.keys()) + [
            key for key in group.attrs if key != "order"
        ]

    result: dict[object, object] = {}

    for key in keys:
        typed_key = key_annotation(key)
        result[typed_key] = read_value(group, key, value_annotation)

    return result


def read_attribute(value: object, annotation: object) -> object:
    """Converteix un atribut HDF5 al tipus indicat per l'anotació.

    Parameters
    ----------
    value: object
        Valor de l'objecte
    annotation: object
        Identificador de l'objecte

    Returns
    -------
    result: object
        Valor llegit

    Raises
    ------
    TypeError
        Si el valor donat no es pot convertir a l'identificador

    """
    value = to_python(value)
    annotation = unwrap_optional(annotation)

    origin = get_origin(annotation)

    if origin in {tuple, list}:
        return read_sequence(value, annotation)

    if isinstance(value, bytes) and annotation is str:
        return value.decode()

    if isinstance(annotation, type) and not isinstance(value, annotation):
        try:
            return annotation(value)
        except (TypeError, ValueError) as exc:
            msg = f"No es pot convertir {value!r} a {annotation!r}"
            raise TypeError(msg) from exc

    return value


def read_sequence(values: object, annotation: object) -> tuple[object, ...] | list[object]:
    """Llig una seqüència de valors amb les anotacions corresponents.

    Parameters
    ----------
    values: object
        Valors d'una seqüència numpy
    annotation: object
        Identificador de l'objecte

    Returns
    -------
    result: tuple[object, ...] | list[object]
        Seqüència llegida

    Raises
    ------
    TypeError
        Si no és una seqüència de numpy
        Si les anotacions de la seqüència no són vàlides

    """
    if not isinstance(values, np.ndarray):
        msg = f"S'esperava un ndarray, però s'ha obtingut {type(values)!r}"
        raise TypeError(msg)

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is list:
        if len(args) != 1:
            msg = f"Anotació de llista no vàlida: {annotation!r}"
            raise TypeError(msg)

        item_annotation = args[0]

        if isinstance(item_annotation, type):
            return [item_annotation(to_python(value)) for value in values]

        if get_origin(item_annotation) in {list, tuple}:
            return [read_sequence(to_python(value), item_annotation) for value in values]

        msg = f"Anotació d'element de llista no vàlida: {item_annotation!r}"
        raise TypeError(msg)

    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            if not isinstance(args[0], type):
                msg = f"Anotació de tupla no vàlida: {annotation!r}"
                raise TypeError(msg)

            type_ = args[0]
            return tuple(type_(to_python(value)) for value in values)

        if len(args) != len(values) or not all(isinstance(type_, type) for type_ in args):
            msg = f"La longitud o els tipus de les dades ({len(values)}) no coincideixen amb l'anotació {annotation!r}"
            raise TypeError(msg)

        return tuple(type_(to_python(value)) for value, type_ in zip(values, args, strict=True))

    msg = f"Tipus de seqüència no suportat: {annotation!r}"
    raise TypeError(msg)


def save(filepath: str, file: FileView) -> None:
    """Guarda un fitxer en format H5.

    Parameters
    ----------
    filepath: str
        Ruta del fitxer H5 que es crearà.
    file: FileProtocol
        Fitxer que es vol guardar.

    """
    with h5py.File(filepath, "w") as f:
        save_object(f, file.data)


def save_session(filepath: str, files: dict[str, FileView]) -> None:
    """Guarda una sessió de fitxers en format HDF5.

    Els fitxers es guarden en el mateix ordre que tenen en el diccionari.

    Parameters
    ----------
    filepath: str
        Ruta del fitxer HDF5 que es crearà.
    files: dict[str, FileData]
        Diccionari de fitxers que es vol guardar, indexat pel seu nom.

    """
    with h5py.File(filepath, "w") as f:
        f.attrs["file_order"] = list(files.keys())

        for file in files.values():
            fg = f.create_group(file.name)
            save_object(fg, file.data)


def save_object(group: h5py.Group, obj: object) -> None:
    """Guarda els atributs anotats d'un objecte en un grup H5.

    Només es guarden els atributs declarats en les anotacions de tipus de la classe de l'objecte.

    Parameters
    ----------
    group: h5py.Group
        Grup H5 on es guardarà l'objecte.
    obj: object
        Objecte que es vol guardar.

    Raises
    ------
    TypeError
        Si l'objecte no és un dataclass.

    """
    if not is_dataclass(obj):
        msg = f"{type(obj).__name__} no és un dataclass."
        raise TypeError(msg)

    for field in fields(obj):
        if not field.metadata.get("h5", True):
            continue

        save_value(group, field.name, getattr(obj, field.name))


def save_value(group: h5py.Group, name: str, value: object) -> None:
    """Guarda un valor en un grup H5 segons el seu tipus.

    Els valors de tipus ``None`` no es guarden. Els dataclasses i els
    diccionaris es guarden com a grups, els arrays de NumPy com a datasets,
    i les tuples i els slices com a atributs dels seus grups corresponents.
    La resta de valors es guarden directament com a atributs H5.

    Parameters
    ----------
    group : h5py.Group
        Grup H5 on es guardarà el valor.
    name : str
        Nom que tindrà el valor dins del grup.
    value : object
        Valor que es vol guardar.

    """
    if value is None:
        return

    if is_dataclass(value):
        save_object(group.create_group(name), value)
    elif isinstance(value, dict):
        save_dict(group, name, value)
    elif isinstance(value, np.ndarray):
        group.create_dataset(name, data=value)
    elif isinstance(value, tuple):
        save_tuple(group, name, value)
    elif isinstance(value, slice):
        save_slice(group, name, cast("IntSlice", value))
    else:
        group.attrs[name] = value


def save_dict[K, V](group: h5py.Group, name: str, value: dict[K, V]) -> None:
    """Guarda un diccionari en un grup H5.

    Parameters
    ----------
    group : h5py.Group
        Grup H5 on es guardarà el diccionari.
    name : str
        Nom que tindrà el diccionari.
    value : dict[object, object]
        Diccionari que es vol guardar.

    """
    sub_dict = group.create_group(name)
    sub_dict.attrs["order"] = np.array(list(map(str, value.keys())), dtype=h5py.string_dtype())

    for key, val in value.items():
        save_value(sub_dict, str(key), val)


def save_tuple(group: h5py.Group, name: str, value: tuple[object, ...]) -> None:
    """Guarda una tupla com a atribut d'un grup H5.

    Parameters
    ----------
    group : h5py.Group
        Grup H5 on es guardarà la tupla.
    name : str
        Nom que tindrà la tupla.
    value : tuple[object, ...]
        Tupla que es vol guardar.

    """
    tuple_group = group.create_group(name)
    tuple_group.attrs["values"] = value


def save_slice(group: h5py.Group, name: str, value: IntSlice) -> None:
    """Guarda un slice com a atributs d'un grup H5.

    Parameters
    ----------
    group : h5py.Group
        Grup H5 on es guardarà el slice.
    name : str
        Nom que tindrà el slice.
    value : slice
        Slice que es vol guardar.

    """
    slice_group = group.create_group(name)
    slice_group.attrs["start"] = value.start
    slice_group.attrs["stop"] = value.stop

    if value.step is not None:
        slice_group.attrs["step"] = value.step


def unwrap_optional(annotation: object) -> object:
    """Elimina 'None' d'una anotació de tipus opcional.

    Si l'anotació és un'`Union' que conté exactament un tipus diferent de 'None', retorna aquest tipus.
    En qualsevol altre cas, retorna l'anotació sense modificar-la.

    Parameters
    ----------
    annotation: object
        Anotació de tipus que es vol desempaquetar.

    Returns
    -------
    new_annotation: object
        Anotació sense 'None' quan correspon.

    """
    origin = get_origin(annotation)

    if origin in {Union, UnionType}:
        args = tuple(arg for arg in get_args(annotation) if arg is not type(None))

        if len(args) == 1:
            return args[0]

    return annotation
