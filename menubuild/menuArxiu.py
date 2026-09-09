from pathlib import Path
from collections import defaultdict
from tkinter import filedialog, messagebox
from matplotlib.pyplot import close

from fileio import open_file, h5
from classes.file import FileData, FileView
from .base import BaseMenu

import sys
import numpy as np
from dataclasses import is_dataclass, fields

def object_size(obj, seen=None):
    """Mida total d'un objecte, evitant comptar referències repetides."""

    if seen is None:
        seen = set()

    obj_id = id(obj)

    if obj_id in seen:
        return 0

    seen.add(obj_id)

    if isinstance(obj, np.ndarray):
        return obj.nbytes

    if is_dataclass(obj) and not isinstance(obj, type):
        return (
            sys.getsizeof(obj)
            + sum(
                object_size(getattr(obj, field.name), seen)
                for field in fields(obj)
                if getattr(obj, field.name) is not None
            )
        )

    if isinstance(obj, dict):
        return (
            sys.getsizeof(obj)
            + sum(
                object_size(k, seen) + object_size(v, seen)
                for k, v in obj.items()
            )
        )

    if isinstance(obj, (list, tuple, set, frozenset)):
        return (
            sys.getsizeof(obj)
            + sum(object_size(x, seen) for x in obj)
        )

    return sys.getsizeof(obj)


def memory_report(obj):
    """Mostra la mida de cada instància/atribut de forma jeràrquica."""

    def show(value, name, indent=0):

        # Cada branca té el seu propi 'seen'
        size = object_size(value)

        print(
            f"{' ' * indent}"
            f"{name}: {size/ 1024} kB"
        )

        if is_dataclass(value) and not isinstance(value, type):

            for field in fields(value):
                child = getattr(value, field.name)

                if child is not None:
                    show(
                        child,
                        field.name,
                        indent + 4
                    )

        elif isinstance(value, dict):

            for key, child in value.items():
                show(
                    child,
                    str(key),
                    indent + 4
                )

    show(obj, type(obj).__name__)

class GestorArxiu(BaseMenu):  # Classe que gestiona les accions del menú "Arxiu" de l'aplicació.
    ordre = 0 # Atribut per a ordenar els menús (opcional)
    
    def __init__(self, app):
        super().__init__(app)  # Inicialitza la classe base
        
    def registrar_menu(self, menu): # Registra les accions del menú "Arxiu" a l'aplicació.
        accions = [
            ("Obrir fitxer", lambda: self._open_file(), '<Control-o>'),
            ("Obrir sessió", lambda: self._open_session(), '<Control-Shift-O>'),
            ("SEPARATOR"),
            ("Guardar fitxer", lambda: self.save_file(func = self._save), '<Control-g>'),
            ("Guardar tots els fitxers", lambda: self.save_file(func = self._save, tots = True), '<Control-Shift-G>'),
            ("Guardar sessió", lambda: self._save_session(), '<Control-s>'),
            ("SEPARATOR"),
            ("Tancar fitxer", lambda: self._close_file(), '<Control-t>'),
            ("Eixir", self.root.quit, '<Escape>'),
        ]
        
        self.create_menu("Arxiu", menu, accions)  # Crida a la funció comuna d'afegir menú

    def _open_file(self): # Obre un fitxer AIST i carrega les dades en el notebook.
        filepaths = filedialog.askopenfilenames(
                    filetypes = [("H5", "*.h5"), ("AIST", "*.aist"), ("WSxM", ["*.top", "*.Auxfeed"]),
                                 ("TXTRAMAN", "*.txt")])

        if not filepaths: return

        self.label_inici.place_forget()
        groups = defaultdict(list)

        for fp in filepaths:
            fp = Path(fp)
            format = fp.suffix

            match format:
                case '.top' | '.Auxfeed':
                    base = fp.name.split('.', 1)[0]
                    format = '.wsxm'
                case _: base = fp.stem

            groups[base].append(fp)

        for filename, files in groups.items():
            file = open_file(format, file_list = files, fileclass = FileData)
            memory_report(file)
            self._add_file(filename, file, files[0].parent)

    def _open_session(self):  # Obre un fitxer AIST i carrega les dades en el notebook.
        filepath = filedialog.askopenfilename(filetypes=[("Sessió", "*.hdf5")])
        if not filepath: return

        filepath = Path(filepath)
        self.label_inici.place_forget()

        files = open_file(".hdf5", file_list = [filepath], fileclass = FileData)
        for name, file in files.items():
            self._add_file(name, file, filepath.parent)

    def _add_file(self, name, file, parent):
        if name in self.files:
            messagebox.showinfo("Informació", f"El fitxer «{name}» ja està obert.")
            return

        folder = parent / name
        file.name = name; file.folder = folder

        file.view = FileView(self.notebook, file)
        self.files[name] = file

        if self.current_file is None: self.set_file(file)

    def _save(self, file):  # Guarda les dades de totes les pestanyes obertes en fitxers.
        if not self.condicions_guardar(file): return False
        file.folder.mkdir(parents=True, exist_ok=True)

        map = file.view.map

        for channelKey, ch in file.channel.items():
            map.refresh_map(ch)
            map.figure.savefig(f"{file.folder}/{channelKey}.png", bbox_inches='tight')

        map.refresh_map(file.current_channel)
        h5.save(Path(f'{file.folder}.h5'), file)
        return True
    
    def _save_session(self):
        if not self.comprova_fitxer(): return
        
        ruta = filedialog.asksaveasfilename(parent = self.notebook, defaultextension=".hdf5", initialfile=f"Sessió1.hdf5",
            filetypes=[("HDF5", "*.hdf5")])
        
        if ruta: h5.save_session(ruta, self.files)
    
    def _close_file(self): # Tanca el fitxer actual i neteja les dades associades.
        file = self.current_file
        if not file: return

        figure = file.view.map.figure
        figure.clf()
        close(figure)

        self.notebook.forget(file.view.tab)
        
        for key in list(self.files.keys()):
            if self.files[key] is file:
                self.files.pop(key)
                break

        if not self.files:
            self.label_inici.place(relx=0.5, rely=0.5, anchor='center')
            self.set_file(None)