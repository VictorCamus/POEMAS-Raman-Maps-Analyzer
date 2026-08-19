import numpy as np

from tkinter import messagebox
from classes import ChannelData
from .base import BaseMenu
from window import BaseWindow
from process.shiftphase import cross_correlation_shift
from window.widgets import create_tab, Widget

class GestorMapes(BaseMenu): # Classe que gestiona les accions relacionades amb el zoom de les imatges.
    ordre = 40 # Atribut per a ordenar els menús (opcional)
    
    def __init__(self, app):
        super().__init__(app)

    def registrar_menu(self, menu):
        accions = [
            ("Sincronitzar límits", lambda: self.lims_sync(), None),
            ("Operar amb canals", lambda: OperarMaps(self), None),
            ("Ajustar mapes desplaçats", lambda: ShiftMaps(self), None),
            ("SEPARATOR"),
            ("Tancar canals", lambda: TancarMaps(self), None)
        ]
        
        self.create_menu("Mapes", menu, accions)

    def lims_sync(self):
        file = self.current_file

        for key, channel in file.channel.items():
            for f in self.files.values():
                if f is file: continue
                if key in f.channel: f.channel[key].lims = np.copy(channel.lims)

class OperarMaps(BaseWindow):
    def __init__(self, gestor):
        self.opt = "subs"
        self.new_chname = None
        
        super().__init__(gestor, "Operar amb canals")

    def _create_widgets(self):
        list_files, channels, initCh = self.compare_files()
        
        operations = {"Suma (F2+F1)": "sum", "Resta (F2-F1)": "subs",
                        "Multiplicació (F2*F1)": "mult", "Divisió (F2/F1)": "div"}

        self.widgets = {
            "file_ref": Widget(key="file_ref", var_type=str, init=self.file_ref.name,
                           text="Arxiu Referència (F1)", widget="cb", widget_kwargs={"options": list_files[1:]},
                           setter=self, mode="attr"),

            "file": Widget(key="file", var_type=str, init=self.file.name,
                           text="Arxiu 2 (F2)", widget="cb", widget_kwargs={"options": list_files},
                           setter=self, mode="attr"),

            "channel": Widget(key="channel", var_type=str, init=initCh,
                              text="Canal", widget="cb", widget_kwargs={"options": channels},
                              setter=self, mode="attr"),

            "opt": Widget(key="opt", var_type=str, init="subs",
                          text="Operació", widget="radiobutton", widget_kwargs={"options": operations},
                          setter=self, mode="attr"),

            "new_chname": Widget(key="new_chname", var_type=str, init=None,
                                 text="Nom nou canal", widget="entry",
                                 setter=self, mode="attr"),

            "newCh": Widget(key="newCh", var_type=str, init="Aplicar",
                            widget="button",
                            setter=self.apply_op)}
    
    def base_op(self, files):
        file_ref = self.file_ref
        ch_ref = file_ref.channel[self.channel_key]

        for f in files:
            if f is file_ref: continue
                        
            if not np.array_equal(file_ref.geometry.N, f.geometry.N) or not np.array_equal(file_ref.geometry.midaBase, f.geometry.midaBase):
                return False

            ch = f.channel[self.channel_key]

            match self.opt:
                case "sum":  zNew = ch.Z + ch_ref.Z; units = ch_ref.units
                case "subs": zNew = ch.Z - ch_ref.Z; units = ch_ref.units
                case "mult": zNew = ch.Z * ch_ref.Z; units = f'{ch_ref.units}²'
                case "div":  zNew = ch.Z / ch_ref.Z; units = ''
            
            tab = create_tab(f.view.selector, self.new_chname)

            f.channel[self.new_chname] = ChannelData(self.new_chname, zNew, units)
            f.channel[self.new_chname].tab = tab
            
        return True

    def apply_op(self, event):
        if not self.new_chname: 
            messagebox.showerror("Operacions amb mapes", "Cal triar un nom per al nou arxiu")
            return
        
        files = self.files_list()
        if not self.base_op(files):
            messagebox.showerror("Operacions amb mapes", "Els mapes triats no tenen les mateixes dimensions.")
            return

        if self.file_key != "Tots els mapes" and self.new_chname in list(self.file.channel):
            self.file.view.selector.select(self.file.channel[self.new_chname].tab)

class ShiftMaps(BaseWindow):
    def __init__(self, gestor):
        super().__init__(gestor, "Ajustar mapes desplaçats")
    
    def _create_widgets(self):
        list_files, channels, initCh = self.compare_files()

        self.widgets = {
            "file_ref": Widget(key="file_ref", var_type=str, init=self.file_ref.name,
                           text="Arxiu Referència (F1)", widget="cb", widget_kwargs={"options": list_files[1:]},
                           setter=self, mode="attr"),

            "file": Widget(key="file", var_type=str, init=self.file.name,
                           text="Arxiu 2 (F2)", widget="cb", widget_kwargs={"options": list_files},
                           setter=self, mode="attr"),

            "channel": Widget(key="channel", var_type=str, init=initCh,
                              text="Canal", widget="cb", widget_kwargs={"options": channels},
                              setter=self, mode="attr"),

            "phcorr": Widget(key="phcorr", var_type=str, init="Aplicar",
                             text="Dibuixa la correlació de fase", widget="button",
                             setter=self.phcorr),

            "newCh": Widget(key="newCh", var_type=str, init="Aplicar",
                            text="Obtindre nou canal:", widget="button",
                            setter=self.apply_op)}
    
    def phcorr(self, event):
        if self.file_key == "Tots els mapes":
            messagebox.showerror("Error", "Tria un arxiu específic per a vore la correlació de fase")
            return

        if self.file_ref is self._file:
            messagebox.showerror("Error", "Tria dos arxius diferents")
            return

        cross_correlation_shift(self.file_ref.channel[self.channel_key].Z, self.file.channel[self.channel_key].Z, plot=True)

    def apply_op(self, event):
        files = self.files_list()
        file_ref = self.file_ref

        Lx_ref, Ly_ref = file_ref.geometry.midaBase
        Nx_ref, Ny_ref = file_ref.geometry.N
        px_ref, py_ref = Lx_ref/Nx_ref, Ly_ref/Ny_ref

        # ROI global en coords físiques del fitxer de referència
        roi_global = [0, Lx_ref, 0, Ly_ref]

        # guardar shifts respecte referència
        shifts = {file_ref.name: (0, 0)}

        # calcular shifts i ROI preliminars

        for f in files:
            if f is file_ref:
                shifts[f.name] = (0, 0)
                continue

            dx, dy = cross_correlation_shift(file_ref.channel[self.channel_key].Z,
                                            f.channel[self.channel_key].Z)
            # convertir a unitats físiques
            shifts[f.name] = (dx*px_ref, dy*py_ref)

            # actualitzar ROI global
            roi_global[0] = max(roi_global[0], shifts[f.name][0])
            roi_global[1] = min(roi_global[1], shifts[f.name][0] + f.geometry.midaBase[0])
            roi_global[2] = max(roi_global[2], shifts[f.name][1])
            roi_global[3] = min(roi_global[3], shifts[f.name][1] + f.geometry.midaBase[1])

            if roi_global[0] >= roi_global[1] or roi_global[2] >= roi_global[3]:
                raise ValueError("No hi ha solapament global")

        for f in files:
            if f is file_ref: px, py = px_ref, py_ref
            else: px, py = f.geometry.midaBase[0]/f.geometry.N[0], f.geometry.midaBase[1]/f.geometry.N[1]

            x0 = int(round((roi_global[0] - shifts[f.name][0]) / px))
            x1 = int(round((roi_global[1] - shifts[f.name][0]) / px))
            y0 = int(round((roi_global[2] - shifts[f.name][1]) / py))
            y1 = int(round((roi_global[3] - shifts[f.name][1]) / py))

            f.geometry.N = np.array([x1 - x0, y1 - y0])
            f.geometry.midaBase = np.array([f.geometry.N[0] * px, f.geometry.N[1] * py])
            for ch in f.channel.values(): ch.Z = ch.Z[y0:y1, x0:x1]

            for prof in f.objects.profiles.values(): prof.line = [(x - x0, y - y0) for x, y in prof.line]
            f.view.map.zoom.base_size()

class TancarMaps(BaseWindow):
    def __init__(self, gestor):
        super().__init__(gestor, "Tancar canals")
        self.intersect = False

    def tancar_canal(self, event):
        from matplotlib.pyplot import close
        if not self.files: return
        files = self.files_list()
        
        for f in files:
            if self.channel_key not in f.channel: continue 
        
            f.view.selector.forget(f.channel[self.channel_key].tab)
            f.channel.pop(self.channel_key, None)

            if not f.channel:
                self.notebook.forget(f.view.tab)
                close(self.file.view.map.figure)

                if f is self.file:    
                    self.files.pop(f.name, None)
                    
                    if not self.files:
                        self.label_inici.place(relx=0.5, rely=0.5, anchor='center')
                        
                        return
                    
                    self.file = next(iter(self.files))

                files = ["Tots els mapes"] + list(self.files.keys())
                self.update_files(files)

        self.update_channels()
        first_channel = next(iter(self.file.channel.values()))
        self.file.view.selector.select(first_channel.tab)

    def _create_widgets(self):
        files = ['Tots els mapes'] + list(self.files.keys())
        channels = list(self.file.channel.keys())

        self.widgets = {
            "file": Widget(key="file", var_type=str, init=self.file.name,
                    text="Arxiu:", widget="cb", widget_kwargs={"options": files},
                    setter=self, mode="attr"),

            "channel": Widget(key="channel", var_type=str, init=self.channel.name,
                       text="Canal:", widget="cb", widget_kwargs={"options": channels},
                       setter=self, mode="attr"),

            "tancar": Widget(key="tancar", var_type=str, init="Aplicar",
                      text="Tancar:", widget="button",
                      setter=self.tancar_canal)}