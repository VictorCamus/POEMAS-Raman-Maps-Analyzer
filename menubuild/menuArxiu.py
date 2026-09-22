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

class GestorArxiu(BaseMenu):  # Classe que gestiona les accions del menú "Arxiu" de l'aplicació.
    ordre = 0 # Atribut per a ordenar els menús (opcional)

    def registrar_menu(self, menu): # Registra les accions del menú "Arxiu" a l'aplicació.
        self.add_tab(text = "Obrir fitxer", func = self._open_file, shortcut = 'Control-o', file_check = False)
        self.add_tab(text = "Guardar fitxer", func = self._save_file, shortcut = 'Control-g')
        self.add_tab(text = "Guardar sessió", func = self._save_session, shortcut = 'Control-s')
        self.add_tab()
        self.add_tab(text = "Tancar fitxer", func = self._close_file, shortcut = 'Control-t')
        self.add_tab(text = "Eixir", func = self.root.quit, shortcut = 'Escape', file_check = False)
        
        menu.add_cascade(label="Arxiu", menu=self.submenu)  # Crida a la funció comuna d'afegir menú

    def _open_file(self): # Obre un fitxer AIST i carrega les dades en el notebook.
        filepaths = filedialog.askopenfilenames(filetypes = [("H5", "*.h5"), ("AIST", "*.aist"), 
                                                ("WSxM", ["*.top", "*.Auxfeed"]), ("TXTRAMAN", "*.txt"), ("Sessió", "*.hdf5")])

        if not filepaths: return
        if not self.files: self.notebook.lift()
        
        groups = defaultdict(list)

        for fp in filepaths:
            fp = Path(fp)
            fmt = fp.suffix

            if fmt == '.hdf5' and len(filepaths) > 1:
                messagebox.showerror("Obrir fitxer", "Les sessions només poden obrir-se individualment")
                return

            match fmt:
                case '.top' | '.Auxfeed':
                    base = fp.name.split('.', 1)[0]
                    fmt = '.wsxm'
                case _: base = fp.stem

            groups[base].append(fp)
        
        for filename, filepath in groups.items():
            file = open_file(fmt, file_list = filepath, fileclass = FileData)
            if fmt == '.hdf5':
                for name, f in file.items(): self._add_file(name, f, filepath[0].parent)
            
            else: self._add_file(filename, file, filepath[0].parent)

    def _add_file(self, name, file, parent):
        if name in self.files:
            messagebox.showinfo("Informació", f"El fitxer «{name}» ja està obert.")
            return

        folder = parent / name
        file.name = name; file.folder = folder

        file.view = FileView(self.notebook, file)
        self.files[name] = file

        if self.current_file is None: self.set_file(file)

    def _save_file(self):  # Guarda les dades de totes les pestanyes obertes en fitxers.
        file = self.current_file

        file.folder.mkdir(parents=True, exist_ok=True)
        h5.save(Path(f'{file.folder}.h5'), file)
        
        return True
    
    def _save_session(self):
        ruta = filedialog.asksaveasfilename(parent = self.notebook, defaultextension=".hdf5", initialfile=f"Sessió1.hdf5",
            filetypes=[("HDF5", "*.hdf5")])
        
        if ruta: h5.save_session(ruta, self.files)
    
    def _close_file(self): # Tanca el fitxer actual i neteja les dades associades.
        file = self.current_file
        
        figure = file.view.map.figure
        figure.clf()
        close(figure)

        self.notebook.forget(file.view.tab)
        
        for key in list(self.files.keys()):
            if self.files[key] is file:
                self.files.pop(key)
                break

        if not self.files:
            self.notebook.lower()
            self.set_file(None)

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