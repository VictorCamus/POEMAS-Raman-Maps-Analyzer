import h5py
import numpy as np
from dataclasses import is_dataclass
from typing import get_origin, get_args

def load(file_list, fileclass):
    file = file_list[0]
    with h5py.File(file, "r") as f:
        if file.suffix.lower() == '.hdf5':
            return {key: read_object(group, fileclass) for key, group in f.items()} # Et retorna tots els fitxers d'una.

        return read_object(f, fileclass)

def to_python(value): # Funció per a poder llegir booleans i passar-los a format Python.
    return value.item() if isinstance(value, np.generic) else value

def read_object(group, fileclass):
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
                data[name] = {key_type(key): read_object(obj[key], value_type) for key in obj}

            else: data[name] = read_object(obj, annotation) # Crea

    return fileclass(**data)

def save(filename, file):
    with h5py.File(filename, "w") as f:
        save_object(f, file)

def save_session(filename, files):
    with h5py.File(filename, "w") as f:
        for file in files.values():
            fg = f.create_group(file.name)
            save_object(fg, file)

def save_object(group, obj):
    for name in type(obj).__annotations__:
        value = getattr(obj, name)
        if value is None: continue

        if is_dataclass(value): # Si és una classe, reitera la funció
            save_object(group.create_group(name), value)

        elif isinstance(value, dict): # Si és un diccionari, crea un subgrup i un data-set per a cada entrada del diccionari.
            sub_dict = group.create_group(name)
            for key, data in value.items():
                key = str(key)
                if is_dataclass(data): save_object(sub_dict.create_group(key), data)
                else: sub_dict.create_dataset(key, data=data)

        elif isinstance(value, np.ndarray): # Si és un np.array.
            group.create_dataset(name, data=value)

        else: group.attrs[name] = value # Si és un string, booleà o qualsevol variable que no siga un array.