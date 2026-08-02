from operator import xor
import numpy as np

from .base import BaseMenu
from tkinter import messagebox
from window.builder import BaseWindow

class GestorImatges(BaseMenu): # Classe que gestiona les accions relacionades amb el zoom de les imatges.
    ordre = 10 # Atribut per a ordenar els menús (opcional)
    
    def __init__(self, app, get_current, set_current):
        super().__init__(app, get_current, set_current)
        
    def registrar_menu(self, menu):
        accions = [
            ("Rotar en sentit horari", lambda: self._rotar(rot = 1), "<Shift-R>"),
            ("Rotar en sentit antihorari", lambda: self._rotar(rot = 3), "<Shift-L>"),
            ("Voltejar imatge", lambda: self._rotar(flip = True), "<Shift-F>"),
            ("Sincronitzar rotació", lambda: self._rot_sync(), None),
            ("Zoom manual", lambda: self._zoom_manual(), None),
            ("Sincronitzar zoom", lambda: self._zoom_sync(), None),
            ("SEPARATOR"),
            ("Desfer zoom", lambda: self._desfer_zoom(), None)
        ]
        
        self.create_menu("Operacions bàsiques", menu, accions)
        
    def _rotar(self, rot=0, flip = False, file=None):
        if not self.comprova_fitxer(): return
        if not file: file = self.current_file
        channel = file.current_channel
        # --- Normalitzar rotació ---

        file.rot += rot if not file.flip else -rot # Si està rotada, la rotació resta, si no, suma.
        if flip: file.flip = not file.flip

        # --- Rotar canals ---
        for ch in file.channel.values():
            if rot != 0: ch.Z = np.rot90(ch.Z, k=rot)
            if flip: ch.Z = np.flip(ch.Z, axis = 1)

        file.image.set_data(channel.Z)
        self._actualitzar_rotacio(file, rot, flip)

    def _rotar_limits(self, xlims, ylims, Lx, Ly, rotation, flip):
        match rotation:
            case 0: xnew, ynew = xlims, ylims
            case 1: xnew, ynew = ylims, (Ly - xlims[1], Ly - xlims[0])
            case 2: xnew, ynew = (Lx - xlims[1], Lx - xlims[0]), (Ly - ylims[1], Ly - ylims[0])
            case 3: xnew, ynew = (Lx - ylims[1], Lx - ylims[0]), xlims

        if flip: xnew = (Lx - xnew[1], Lx - xnew[0])

        return xnew, ynew

    def _actualitzar_rotacio(self, file, rot, flip):
        if rot % 2:
            file.midaBase = file.midaBase[::-1]
            file.N = file.N[::-1]

        if hasattr(file, 'mask'):
            if rot: file.mask = np.rot90(file.mask, k=rot)
            if flip: file.mask = np.flip(file.mask, axis = 1)
            file.mask.set_data(file.mask)

        file.zoom.xylims = self._rotar_limits(*file.zoom.xylims, *file.midaBase, rot, flip)
        file.image.set_extent([0, file.midaBase[0], 0, file.midaBase[1]])

        if file.profile is not None:
            for prof in file.profile.values(): prof.rotate(file.N, file.midaBase, rot, flip)

        if file.zoom.mida[0] != file.zoom.mida[1]: file.zoom._resize()

    def _rot_sync(self):
        if not self.comprova_fitxer(): return
        file = self.current_file

        for f in self.files.values():
            if f is not file:
                flip = xor(file.flip, f.flip)
                rot = (file.rot - f.rot) % 4 if not f.flip else - (file.rot - f.rot) % 4
                self._rotar(rot = rot, flip = flip, file=f)

    def _zoom_manual(self):
        if not self.comprova_fitxer(): return
        ZoomManual(self)
    
    def _zoom_sync(self):
        if not self.comprova_fitxer(): return
        file = self.current_file

        for f in self.files.values():
            if f.N != file.N and f.midaBase != file.midaBase:
                messagebox.showerror("Error", "Les dimensions dels arxius són diferents")
                return
            if f is not file:
                f.zoom.xylims = file.zoom.xylims

    def _desfer_zoom(self): # Desfés el zoom de totes les pestanyes obertes.       
        if not self.comprova_fitxer(): return
        file = self.current_file
        file.zoom._base_size()

class ZoomManual(BaseWindow):
    def __init__(self, parent):
        super().__init__(parent, "Canviar límits")

    def set_lims(self, left = None, right = None, bottom = None, top = None): # Aplica la sincronització del zoom.
        left = self.file.zoom.xlims[0] if left is None else left
        right = self.file.zoom.xlims[1] if right is None else right

        xlims =  self.validar(left, right, self.file.midaBase[0], self.widgets["left"], self.widgets["right"])
        if xlims is None: return

        bottom = self.file.zoom.ylims[0] if bottom is None else bottom
        top = self.file.zoom.ylims[1] if top is None else top

        ylims = self.validar(bottom, top, self.file.midaBase[1], self.widgets["bottom"], self.widgets["top"])
        if ylims is None: return

        self.file.zoom.xlims = xlims
        self.file.zoom.ylims = ylims

        self.file.zoom._resize()

    def _grid(self):
        return [
            # Estructura: ((var_name, var_type), (label, object), setter, {getter, **extra})
            (("left", float, self.file.zoom.xlims[0]), ("Left (Eix X):", 'entry'), (self.set_lims, "kwargs")),
            (("right", float, self.file.zoom.xlims[1]), ("Right (Eix X):", 'entry'), (self.set_lims, "kwargs")),
            (("bottom", float, self.file.zoom.ylims[0]), ("Bottom (Eix Y):", 'entry'), (self.set_lims, "kwargs")),
            (("top", float, self.file.zoom.ylims[1]), ("Top (Eix Y):", 'entry'), (self.set_lims, "kwargs")),
        ]

    @staticmethod
    def validar(lim_inf, lim_sup, mida, widgets_inf, widgets_sup):
        lim_inf = max(0, lim_inf)
        lim_sup = min(mida, lim_sup)

        widgets_inf.value.set(lim_inf)
        widgets_sup.value.set(lim_sup)

        if lim_inf >= lim_sup:
            messagebox.showerror("Límits del mapa", "El límit superior ha de ser major que l'inferior.")
            return None

        return lim_inf, lim_sup