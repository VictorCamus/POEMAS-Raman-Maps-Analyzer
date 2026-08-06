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
            ("Rotar en sentit horari", lambda: self._rotate(rot = 1), "<Shift-R>"),
            ("Rotar en sentit antihorari", lambda: self._rotate(rot = 3), "<Shift-L>"),
            ("Voltejar imatge", lambda: self._rotate(flip = True), "<Shift-F>"),
            ("Sincronitzar rotació", lambda: self._rot_sync(), None),
            ("Zoom manual", lambda: self._zoom_manual(), None),
            ("Sincronitzar zoom", lambda: self._zoom_sync(), None),
            ("SEPARATOR"),
            ("Desfer zoom", lambda: self._base_zoom(), None)
        ]
        
        self.create_menu("Operacions bàsiques", menu, accions)

    def _rotate(self, rot=0, flip = False, file=None):
        if not self.comprova_fitxer(): return
        if not file: file = self.current_file
        channel = file.current_channel
        g = file.geometry
        # --- Normalitzar rotació ---

        g.rotation += rot if not g.flip else -rot # Si està rotada, la rotació resta, si no, suma.
        if flip: g.flip = not g.flip

        # --- Rotar canals ---
        for ch in file.channel.values():
            if rot != 0:
                ch.Z = np.rot90(ch.Z, k=rot)
                if ch.spectra is not None: ch.spectra = np.rot90(ch.spectra, k=rot)
            if flip:
                ch.Z = np.flip(ch.Z, axis = 1)
                if ch.spectra is not None: ch.spectra = np.flip(ch.spectra, axis = 1)

        file.view.map.image.set_data(channel.Z)
        self._update_rotation(file, rot, flip)

    def _update_rotation(self, file, rot, flip):
        map = file.view.map
        g = file.geometry
        if rot % 2:
            g.midaBase = g.midaBase[::-1]
            g.N = g.N[::-1]

        mask = file.objects.mask
        if mask:
            if rot: mask = np.rot90(mask, k=rot)
            if flip: mask = np.flip(mask, axis = 1)
            mask.set_data(mask)

        g.rotate(rot, flip)
        map.refresh_geometry()
        map.image.set_extent([0, g.midaBase[0], 0, g.midaBase[1]])

        for prof in file.objects.profiles.values(): prof.rotate(g.N, rot, flip)
        map.profiles.update()

        if file.geometry.mida[0] != file.geometry.mida[1]: map.zoom.resize()

    def _rot_sync(self):
        if not self.comprova_fitxer(): return
        file = self.current_file

        for f in self.files.values():
            if f is not file:
                flip = xor(file.flip, f.flip)
                rot = (file.rot - f.rot) % 4 if not f.flip else - (file.rot - f.rot) % 4
                self._rotate(rot = rot, flip = flip, file=f)

    def _zoom_manual(self):
        if not self.comprova_fitxer(): return
        ZoomManual(self)
    
    def _zoom_sync(self):
        if not self.comprova_fitxer(): return
        file = self.current_file

        for f in self.files.values():
            if f.geometry.N != file.geometry.N and f.geometry.midaBase != file.geometry.midaBase:
                messagebox.showerror("Error", "Les dimensions dels arxius són diferents")
                return
            if f is not file:
                f.geometry.xylims = file.geometry.xylims
                f.view.map.refresh_geometry()

    def _desfer_zoom(self): # Desfés el zoom de totes les pestanyes obertes.       
        if not self.comprova_fitxer(): return
        file = self.current_file
        file.view.map.zoom.base_size()

class ZoomManual(BaseWindow):
    def __init__(self, parent):
        super().__init__(parent, "Canviar límits")

    @property
    def map(self):
        return self.file.view.map

    @property
    def geometry(self):
        return self.file.geometry

    def set_lims(self, left = None, right = None, bottom = None, top = None): # Aplica la sincronització del zoom.
        left = self.geometry.xlims[0] if left is None else left
        right = self.geometry.xlims[1] if right is None else right

        xlims =  self.validar(left, right, self.geometry.midaBase[0], self.widgets["left"], self.widgets["right"])
        if xlims is None: return

        bottom = self.geometry.ylims[0] if bottom is None else bottom
        top = self.geometry.ylims[1] if top is None else top

        ylims = self.validar(bottom, top, self.geometry.midaBase[1], self.widgets["bottom"], self.widgets["top"])
        if ylims is None: return

        self.geometry.xylims = xlims, ylims
        self.map.refresh_geometry()
        self.map.zoom.resize()

    def _grid(self):
        return [
            # Estructura: ((var_name, var_type), (label, object), setter, {getter, **extra})
            (("left", float, self.geometry.xlims[0]), ("Left (Eix X):", 'entry'), (self.set_lims, "kwargs")),
            (("right", float, self.geometry.xlims[1]), ("Right (Eix X):", 'entry'), (self.set_lims, "kwargs")),
            (("bottom", float, self.geometry.ylims[0]), ("Bottom (Eix Y):", 'entry'), (self.set_lims, "kwargs")),
            (("top", float, self.geometry.ylims[1]), ("Top (Eix Y):", 'entry'), (self.set_lims, "kwargs")),
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