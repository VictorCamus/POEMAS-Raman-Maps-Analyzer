from fileio import open_file, h5
from process import statistics as stats
from pathlib import Path
from classes import FileData 
from .base import BaseMenu
import h5py

from collections import defaultdict
from tkinter import filedialog, messagebox
from tkinter.ttk import Notebook
from matplotlib.pyplot import close

class GestorArxiu(BaseMenu):  # Classe que gestiona les accions del menú "Arxiu" de l'aplicació.
    ordre = 0 # Atribut per a ordenar els menús (opcional)
    
    def __init__(self, app, get_current, set_current):
        super().__init__(app, get_current, set_current)  # Inicialitza la classe base
        
    def registrar_menu(self, menu): # Registra les accions del menú "Arxiu" a l'aplicació.
        accions = [
            ("Obrir fitxer", lambda: self._open_file(), '<Control-o>'),
            ("Obrir sessió", lambda: self._open_session(), '<Control-s>'),
            ("SEPARATOR"),
            ("Guardar imatge i estadística", lambda: self.save_file(func = self._save), '<Control-g>'),
            ("Guardar tots els fitxers oberts", lambda: self.save_file(func = self._save, tots = True), '<Control-Shift-G>'),
            ("Guardar sessió", lambda: self._save_session(), '<Control-Shift-S>'),
            ("SEPARATOR"),
            ("Tancar fitxer", lambda: self._close_file(), '<Control-t>'),
            ("Eixir", self.root.quit, '<Escape>'),
        ]
        
        self.create_menu("Arxiu", menu, accions)  # Crida a la funció comuna d'afegir menú
    
    def _open_file(self): # Obre un fitxer AIST i carrega les dades en el notebook.
        filepaths = filedialog.askopenfilenames(filetypes = [("H5", "*.h5"), ("AIST", "*.aist"), ("WSxM", ["*.top", "*.Auxfeed"]), ("XYZ", "*.xyz")])
        ordre = ['AFM', 'MAG', 'PHASE', 'CPD', 'SPV']
        if not filepaths: return
        
        self.label_inici.place_forget()
        groups = defaultdict(list)
        
        for fp in filepaths:
            fp = Path(fp)
            format = fp.suffix

            match format:
                case '.xyz': base, _ = fp.stem.rsplit(' - ', 1)
                case '.top' | '.Auxfeed': 
                    base = fp.name.split('.', 1)[0]
                    format = '.wsxm'
                case _: base = fp.stem
            
            groups[base].append(fp)

        for filename, files in groups.items():

            if filename in self.files:
                messagebox.showinfo("Informació", "Aquest fitxer ja està obert.")
                continue
            
            channels, N, midaBase = open_file(files, format)
            channels = {k: channels[k] for k in ordre if k in channels}
            
            folder = files[0].parent / filename
            self._create_file(filename, folder, channels, N, midaBase)
            
    def _open_session(self): # Obre un fitxer AIST i carrega les dades en el notebook.
        filepath = filedialog.askopenfilename(filetypes = [("HDF5", "*.hdf5")])
        if not filepath: return
        
        filepath = Path(filepath)
        self.label_inici.place_forget()

        with h5py.File(filepath, "r") as f:
            for key in f:
                fg = f[key]
                folder = filepath.parent / key
                if key in self.files:
                    messagebox.showinfo("Informació", "Aquest fitxer ja està obert.")
                    continue

                channels, N, midaBase = h5.read(fg)
                self._create_file(key, folder, channels, N, midaBase)
    
    def _create_file(self, filename, folder, channels, N, midaBase):
        fileframe = self.create_frame(self.notebook, filename)
        notebookChannels = Notebook(fileframe)
        
        self.files[filename] = FileData(frame=fileframe, notebook=notebookChannels, folder=folder, 
            name=filename, channel=channels, N=N, _midaBase=midaBase)

        if not self.current_file: self.current_file = self.files[filename]
        
    def _save_session(self):
        if not self.comprova_fitxer(): return
        
        ruta = filedialog.asksaveasfilename(parent = self.notebook, defaultextension=".hdf5", initialfile=f"Sessió1.hdf5",
            filetypes=[("HDF5", "*.hdf5")])
        
        if ruta: self.h5save(ruta, self.files)
        
    def h5save(self, filename, files):
        with h5py.File(filename, "w") as f:
            if isinstance(files, dict): 
                for file in files.values(): 
                    fg = f.create_group(file.name)
                    self.h5save_single(fg, file)
            else: self.h5save_single(f, files)
            
    def h5save_single(self, f, file):
        f.attrs["filename"] = file.name
        f.attrs["Nx"], f.attrs["Ny"] = file.N
        f.attrs["midaX"], f.attrs["midaY"] = file.midaBase

        ch_grp = f.create_group("channels")

        for tipus, ch in file.channel.items():
            cg = ch_grp.create_group(tipus)
            cg.create_dataset("Z", data=ch.Z)
            cg.create_dataset("lims", data=ch.lims)
            cg.attrs["name"] = ch.name
            cg.attrs["mult"] = ch.mult

    def _save(self, file, fig, ax, amb_histograma=True): # Guarda les dades de totes les pestanyes obertes en fitxers.
        if not self.condicions_guardar(file): return False
        file.folder.mkdir(parents = True, exist_ok=True)
        
        for channelKey, ch in file.channel.items():
            file.redraw(ch)

            if amb_histograma:
                x0, x1, y0, y1 = file.limit_pixels
                zhist = ch.Z[y0:y1, x0:x1].flatten()

                if ch.tipus != 'GRAIN': stats.guardar_histograma(fig, ax, zhist, ch.lims, file.folder, channelKey, title = ch.dades.title)
                else: stats.guardar_histograma_grans(zhist, file.folder, file.midaBase, file.N, ch.tipus, channelKey)

            if not hasattr(file,'mask'): file.figure.savefig(f"{file.folder}/{channelKey}.png", bbox_inches='tight')
            else: 
                mask_folder = file.folder / 'Màscares'
                if not mask_folder.is_dir(): mask_folder.mkdir(parents=True, exist_ok=True)
                file.figure.savefig(f"{file.folder}/Màscares/{channelKey}.png", bbox_inches='tight')

        self.h5save(Path(f'{file.folder}.h5'), file)
        return True
    
    def _close_file(self): # Tanca el fitxer actual i neteja les dades associades.
        file = self.current_file
        if not file: return
        
        file.figure.clf()
        close(file.figure)

        self.notebook.forget(file.frame)
        
        for key in list(self.files.keys()):
            if self.files[key] is file:
                self.files.pop(key)
                break

        if not self.files: 
            self.label_inici.place(relx=0.5, rely=0.5, anchor='center')
            self.current_file = None