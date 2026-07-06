import numpy as np

from tkinter import messagebox
from tkinter.ttk import Frame

from classes import ChannelData, diccionaris as dicc
from .base import BaseMenu
from window import BaseWindow, BaseMapWindow
from process.shiftphase import cross_correlation_shift, apply_crop

class GestorMapes(BaseMenu): # Classe que gestiona les accions relacionades amb el zoom de les imatges.
    ordre = 40 # Atribut per a ordenar els menús (opcional)
    
    def __init__(self, app, get_current, set_current):
        super().__init__(app, get_current, set_current)

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

class RescaleMaps(BaseMapWindow):
    def __init__(self, gestor):
        self.opt = "sum"
        super().__init__(gestor, "Reescalar mapes")
    
    def _grid(self):
        files = list(self.files.keys())
        channels = list(self.file.channel.keys())
        opts = {"Sumar": "sum",
                "Multiplicar": "mult",
                "Normalitzar": "norm"}

        return [
            (("file", str, self.file.name), ("Arxiu:", 'cb', {"options": files}), (self, "attr")),  
            (("channel", str, self.channel.name), ("Canal:", 'cb', {"options": channels}), (self, "attr")),
            (("opt", str, self.opt), ("Opcions:", 'cb', {"options": opts}), (self, "attr")),
            (("value", float, 0), ("Valor:", 'entry'), (self.reescale_ops, "args"))
            ]
    
    def reescale_ops(self, value):
        file = self.file; channel = self.channel; opt = self.opt

        z = np.copy(channel.Z)
        match opt:  
            case "sum": z += value
            case "mult": z *= value
            case "norm":
                zMin, zMax = z.min(), z.max()
                z = (z-zMin)/(zMax-zMin)
                channel.lims = [0, 1]

        if opt != "norm":
            channel.lims = dicc.lims(z, channel.tipus)
            
        file.image.set_data(z)
        file.capçalera.limInf, file.capçalera.limSup = channel.lims
        file.canvas.draw_idle()

class OperarMaps(BaseWindow):
    def __init__(self, gestor):
        self.opt = "subs"
        self.new_chname = None
        self.new_chtype = "SPV"
        
        super().__init__(gestor, "Operar amb canals")

    def _grid(self):
        list_files, channels, initCh = self.compare_files()
        chTypes = list(dicc.all_maps().keys())
        
        operations = {"Suma (F2+F1)": "sum", "Resta (F2-F1)": "subs",
                        "Multiplicació (F2*F1)": "mult", "Divisió (F2/F1)": "div"}

        return [
            (("file_ref", str, self.file_ref.name), ("Arxiu Referència (F1)", 'cb', {"options": list_files[1:]}), (self, "attr")),  
            (("file", str, self.file.name), ("Arxiu 2 (F2)", 'cb', {"options": list_files}), (self, "attr")),
            (("channel", str, initCh), ("Canal", 'cb', {"options": channels}), (self, "attr")),
            (("opt", str, "subs"), ("Operació", 'radiobutton', {"options": operations}), (self, "attr")),
            (("new_chname", str, None), ("Nom nou canal", 'entry'), (self, "attr")),
            (("new_chtype", str, 'SPV'), ("Tipus de canal", 'cb', {"options": chTypes}), (self, "attr")),
            (("newCh", str, "Aplicar"), ("", 'button'), (self.apply_op, "args"))
            ]
    
    def base_op(self, files):
        file_ref = self.file_ref
        ch_ref = file_ref.channel[self.channel_key]

        for f in files:
            if f is file_ref: continue
                        
            if file_ref.N != f.N or file_ref.midaBase != f.midaBase:
                return False

            ch = f.channel[self.channel_key]

            match self.opt:
                case "sum":  zNew = ch.Z + ch_ref.Z
                case "subs": zNew = ch.Z - ch_ref.Z
                case "mult": zNew = ch.Z * ch_ref.Z
                case "div":  zNew = ch.Z / ch_ref.Z
            
            tab = Frame(f.notebook)
            f.notebook.add(tab, text=self.new_chname)

            f.channel[self.new_chname] = ChannelData(self.new_chtype, self.new_chname, zNew)
            f.channel[self.new_chname].frame = tab
            
        return True

    def apply_op(self, event):
        if not self.new_chname: 
            messagebox.showerror("Operacions amb mapes", "Cal triar un nom per al nou arxiu")
            return
        
        files = self.files_list()
        if not self.base_op(files):
            messagebox.showerror("Operacions amb mapes", "Els mapes triats no tenen les mateixes dimensions.")
            return

        if self.file_key != "Tots els mapes" and self.new_chname in self.file.channel:
            self.file.notebook.select(self.file.channel[self.new_chname].frame)

class ShiftMaps(BaseWindow):
    def __init__(self, gestor):
        super().__init__(gestor, "Ajustar mapes desplaçats")
    
    def _grid(self):
        list_files, channels, initCh = self.compare_files()

        return [
            (("file_ref", str, self.file_ref.name), ("Arxiu Referència (F1)", 'cb', {"options": list_files[1:]}), (self, "attr")),  
            (("file", str, self.file.name), ("Arxiu 2 (F2)", 'cb', {"options": list_files}), (self, "attr")),
            (("channel", str, initCh), ("Canal", 'cb', {"options": channels}), (self, "attr")),
            (("phcorr", str, "Aplicar"), ("Dibuixa la correlació de fase", 'button'), (self.phcorr, "args")),
            (("newCh", str, "Aplicar"), ("Obtindre nou canal:", 'button'), (self.apply_op, "args")),
            ]
    
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

        Lx_ref, Ly_ref = file_ref.midaBase
        Nx_ref, Ny_ref = file_ref.N
        px_ref, py_ref = Lx_ref/Nx_ref, Ly_ref/Ny_ref

        # ROI global en coords físiques del fitxer de referència
        roi_global = [0, Lx_ref, 0, Ly_ref]

        # guardar shifts respecte referència
        shifts = {file_ref.name: (0, 0)}

        # calcular shifts i ROI preliminars

        for f in files:
            if f is file_ref:
                continue

            dx, dy = cross_correlation_shift(file_ref.channel[self.channel_key].Z,
                                            f.channel[self.channel_key].Z)
            shifts[f.name] = (dx, dy)

            # convertir a unitats físiques
            dx_phys, dy_phys = dx*px_ref, dy*py_ref

            # actualitzar ROI global
            roi_global[0] = max(roi_global[0], dx_phys)
            roi_global[1] = min(roi_global[1], dx_phys + f.midaBase[0])
            roi_global[2] = max(roi_global[2], dy_phys)
            roi_global[3] = min(roi_global[3], dy_phys + f.midaBase[1])

            if roi_global[0] >= roi_global[1] or roi_global[2] >= roi_global[3]:
                raise ValueError("No hi ha solapament global")
        
        for f in files:
            if f is file_ref:
                x0 = int(round(roi_global[0] * Nx_ref / Lx_ref))
                x1 = int(round(roi_global[1] * Nx_ref / Lx_ref))
                y0 = int(round(roi_global[2] * Ny_ref / Ly_ref))
                y1 = int(round(roi_global[3] * Ny_ref / Ly_ref))
            else:
                dx, dy = shifts[f.name]
                px, py = f.midaBase[0]/f.N[0], f.midaBase[1]/f.N[1]
                dx_phys, dy_phys = dx*px_ref, dy*py_ref

                x0 = int(round((roi_global[0] - dx_phys)/px))
                x1 = int(round((roi_global[1] - dx_phys)/px))
                y0 = int(round((roi_global[2] - dy_phys)/py))
                y1 = int(round((roi_global[3] - dy_phys)/py))

            apply_crop(f, x0, x1, y0, y1)

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
        
            f.notebook.forget(f.channel[self.channel_key].frame)
            f.channel.pop(self.channel_key, None)

            if not f.channel:
                self.notebook.forget(f.frame)
                close(self.file.figure)

                if f is self.file:    
                    self.files.pop(f.name,None)
                    
                    if not self.files:
                        self.label_inici.place(relx=0.5, rely=0.5, anchor='center')
                        
                        return
                    
                    self.file = next(iter(self.files))

                files = ["Tots els mapes"] + list(self.files.keys())
                self.update_files(files)

        self.update_channels()
        first_channel = next(iter(self.file.channel.values()))
        self.file.notebook.select(first_channel.frame)

    def _grid(self):
        files = ['Tots els mapes'] + list(self.files.keys())
        channels = list(self.file.channel.keys())

        return [
            (("file", str, self.file.name), ("Arxiu:", 'cb', {"options": files}), (self, "attr")),  
            (("channel", str, self.channel.name), ("Canal:", 'cb', {"options": channels}), (self, "attr")),
            (("tancar", str, "Aplicar"), ("Tancar:", 'button'), (self.tancar_canal, "args"))
            ]