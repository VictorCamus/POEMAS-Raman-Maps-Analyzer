"""Obertura, guardat i tancat de fitxers."""

from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

from matplotlib.pyplot import close

from classes.data import FileData
from classes.views import FileView, create_tab
from fileio import h5, open_file, open_session
from menubuild.base import BaseMenu

if TYPE_CHECKING:
    from tkinter import Menu

    from classes.protocols import FileDataDict


class GestorFile(BaseMenu):
    """Menú que permet obrir, guaradr i tancar fitxers."""

    def _add_menu(self, menu: Menu) -> None:
        self.add_tab(text="Obrir fitxer", func=self._open_file, shortcut="Control-o", file_check=False)
        self.add_tab(text="Guardar fitxer", func=self._save_file, shortcut="Control-g")
        self.add_tab(text="Guardar sessió", func=self._save_session, shortcut="Control-s")
        self.add_tab()
        self.add_tab(text="Tancar fitxer", func=self._close_file, shortcut="Control-t")
        self.add_tab(text="Eixir", func=self.root.quit, shortcut="Escape", file_check=False)

        menu.add_cascade(label="Arxiu", menu=self.submenu)

    def _open_file(self) -> None:
        """Obri les dades d'un fitxer segons el format triat."""
        filepaths = filedialog.askopenfilenames(
            filetypes=[
                ("Tots els arxius", ["*.aist", "*.txt", "*.h5", "*.hdf5", "*.top", "*.Auxfeed", "*.ch15", "*.ch16"]),
                ("AIST", "*.aist"),
                ("TXTRAMAN", "*.txt"),
                ("H5", "*.h5"),
                ("WSxM", ["*.top", "*.Auxfeed"]),
                ("Sessió", "*.hdf5")])

        if not filepaths:
            return

        if not self.files:
            self.notebook.lift()

        for filepath in filepaths:
            fp = Path(filepath)
            fmt = fp.suffix

            match fmt:
                case ".top" | ".Auxfeed" | ".ch15" | ".ch16":
                    base = f"{fp.name.split('.')[0]}.{fp.name.split('.')[1]}"
                case _:
                    base = fp.stem

            if fmt == ".hdf5":
                dict_data = open_session(filepath=fp)
                for name, data in dict_data.items():
                    self._add_file(file_key=name, data=data, parent=fp.parent)

            else:
                data = open_file(fmt=fmt, filepath=fp)
                self._add_file(file_key=base, data=data, parent=fp.parent)

    def _add_file(self, file_key: str, data: FileDataDict, parent: Path) -> None:
        """Afig les dades del fitxer al programa i les fa compatibles amb el visor de l'aplicació.

        Si el fitxer ja està obert, prova a obrir canals que puguen faltar, cas especialment útils per al format wsxm.
        Si no, crea el visor de zero.

        Parameters
        ----------
        file_key: str
            Clau del fitxer
        data: FileDataDict
            Dades del fitxer
        parent: Path
            Carpeta on es troba el fitxer

        """
        file_data = FileData(**data)

        if file_key in self.files:
            curr_file = self.files[file_key]

            for key in file_data.channel:
                if key not in curr_file.data.channel:
                    tab = create_tab(curr_file.notebook, key)
                    curr_file.channel[key] = file_data.channel[key]
                    curr_file.channel_tabs[key] = tab

            return

        folder = parent / file_key

        file = FileView(data=file_data, name=file_key, folder=folder, notebook=self.notebook)

        if not self.files:
            self.current_file = file

        self.files[file_key] = file

    def _save_file(self) -> None:
        """Guarda un fitxer amb tots els canals."""
        file = self.current_file
        h5.save(f"{file.folder}.h5", file)

    def _save_session(self) -> None:
        """Guarda la sessió amb el nom triat."""
        ruta = filedialog.asksaveasfilename(
            defaultextension=".hdf5",
            initialfile="Sessió1.hdf5",
            filetypes=[("HDF5", "*.hdf5")])

        if ruta:
            h5.save_session(ruta, self.files)

    def _close_file(self) -> None:
        """Tanca el fitxer actual i neteja les dades associades."""
        file = self.current_file

        figure = file.mapview.figure
        figure.clf()
        close(figure)

        self.notebook.forget(file.tab)

        for key in list(self.files.keys()):
            if self.files[key] is file:
                self.files.pop(key)
                break

        if not self.files:
            self.notebook.lower()
            self.current_file = None
