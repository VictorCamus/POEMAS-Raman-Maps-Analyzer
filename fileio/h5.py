import h5py
import numpy as np
from dataclasses import is_dataclass
from typing import get_origin, get_args

def load(file_list, fileclass):
    file = file_list[0]
    with h5py.File(file, "r") as f:
        if file.suffix.lower() == '.hdf5':
            order = list(f.attrs["file_order"])
            return {key: read_object(f[key], fileclass) for key in order} # Et retorna tots els fitxers d'una.

        return read_object(f, fileclass)

def to_python(value): # Funció per a poder llegir booleans i passar-los a format Python.
    return value.item() if isinstance(value, np.generic) else value

def read_object(group, fileclass):
    if isinstance(group, h5py.Dataset):
        return group[()]

    data = {key: to_python(value) for key, value in group.attrs.items()} # Primer llig tots els atributs.
    for name, obj in group.items():
        if isinstance(obj, h5py.Dataset): data[name] = obj[:]
        elif isinstance(obj, h5py.Group):
            annotation = fileclass.__annotations__.get(name)
            if annotation is None:
                raise TypeError(f"No hi ha anotació per al camp {name} de la classe {fileclass.__name__}")

            origin = get_origin(annotation)
            args = get_args(annotation)

            if origin is dict:
                key_type, value_type = args

                if "order" in obj.attrs: keys = list(obj.attrs["order"])
                else: keys = list(obj.keys())

                data[name] = {key_type(key): read_object(obj[key], value_type) for key in keys}

            elif annotation is slice:
                data[name] = slice(to_python(obj.attrs.get("start")), to_python(obj.attrs.get("stop")), to_python(obj.attrs.get("step")))

            else: data[name] = read_object(obj, annotation) # Crea

    return fileclass(**data)

def save(filename, file):
    with h5py.File(filename, "w") as f:
        save_object(f, file)

def save_session(filename, files):
    with h5py.File(filename, "w") as f:
        f.attrs["file_order"] = list(files.keys())

        for file in files.values():
            fg = f.create_group(file.name)
            save_object(fg, file)

def save_object(group, obj):
    for name in type(obj).__annotations__:
        value = getattr(obj, name)
        save_value(group, name, value)

def save_value(group, name, value):

    if value is None:
        return

    if is_dataclass(value):
        save_object(group.create_group(name), value)

    elif isinstance(value, dict):
        sub_dict = group.create_group(name)
        sub_dict.attrs["order"] = np.array(list(map(str, value.keys())), dtype=h5py.string_dtype())

        for key, val in value.items():
            save_value(sub_dict, str(key), val)

    elif isinstance(value, np.ndarray):
        group.create_dataset(name, data=value)

    elif isinstance(value, slice):
        slice_group = group.create_group(name)

        if value.start is not None:
            slice_group.attrs["start"] = value.start

        if value.stop is not None:
            slice_group.attrs["stop"] = value.stop

        if value.step is not None:
            slice_group.attrs["step"] = value.step

    else:
        group.attrs[name] = value