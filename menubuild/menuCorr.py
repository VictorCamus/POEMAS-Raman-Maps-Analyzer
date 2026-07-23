import numpy as np
from window import BaseMapWindow
from process import flatten as flat
from .base import BaseMenu

class GestorCorreccio(BaseMenu):  # Classe que gestiona les accions relacionades amb els perfils de fletxes.
    ordre = 20 # Atribut per a ordenar els menús (opcional)
    
    def __init__(self, app, get_current, set_current):
        super().__init__(app, get_current, set_current)  # Inicialitza la classe base

    def registrar_menu(self, menu):
        accions = [
            ('Reescalar', lambda: RescaleMaps(self), None),
            ('Aplanar mapes', lambda: LevelMaps(self), None),
            ('Corregir enganxons', lambda: RescaleMaps(self), None)
        ]
        
        self.create_menu("Correcció", menu, accions)  # Crida a la funció comuna d'afegir menú

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
            (("file", str, self.file.name), ("Arxiu:", 'cb', {"options": files}), (self.file_changed, "args")),  
            (("channel", str, self.channel.name), ("Canal:", 'cb', {"options": channels}), (self.channel_changed, "args")),
            (("opt", str, self.opt), ("Opcions:", 'radiobutton', {"options": opts}), (self, "attr")),
            (("value", float, 0), ("Valor:", 'entry'), (self.reescale_ops, "args")),
            (("apply", str, "Aplicar"), ("", 'button'), (self.aplicar, "args"))
            ]
    
    def reescale_ops(self, value):
        ch = self.file.channel[self.widgets['channel'].get()]; opt = self.opt

        self.z = np.copy(ch.Z)
        match opt:  
            case "sum": self.z += value; self.lims = [ch.lims[0]+value, ch.lims[1]+value]
            case "mult": self.z *= value; self.lims = [ch.lims[0]*value, ch.lims[1]*value]
            case "norm":
                zMin, zMax = self.z.min(), self.z.max()
                self.z = (self.z-zMin)/(zMax-zMin)
                self.lims = [0, 1]
        
        self.update_fig(ch)

class LevelMaps(BaseMapWindow):
    def __init__(self, gestor):
        super().__init__(gestor, "Aplanar mapes")
        self._direction = True
        self._level_mode = "Cap"
        self._linematch_mode = "Cap"

    def _grid(self):
        files = list(self.files.keys())
        channels = list(self.file.channel.keys())
        options_level = ["Cap", "General", "Cara dominant"]
        options_linematch = {'Cap': 'Cap', 'Mediana': 'median', 'Diferència de medianes': 'median_diff', 'Mòdul': 'modus', 'Comparació': 'match'}
        
        return [
            (("file", str, self.file.name), ("Arxiu:", 'cb', {"options": files}), (self.on_file_changed, "args")),  
            (("channel", str, self.channel.name), ("Canal:", 'cb', {"options": channels}), (self.on_channel_changed, "args")),
            (("level", str, "Cap"), ("Aplanament:", 'radiobutton', {"options": options_level}), (self.level, "args")),
            (("linematch", str, "Cap"), ("Corregir línies:", 'radiobutton', {'options': options_linematch}), (self.linematch, "args")),
            (("direction", bool, True), ("Direcció:", 'radiobutton', {"options": {"H": True, "V": False}, "vertical": False}), (self.direction, "args")),
            (("apply", str, "Aplicar"), ("", 'button'), (self.aplicar, "args"))
            ]
    
    def on_file_changed(self, value):
        self.file_changed(value)
        self.apply_all()
        
    def on_channel_changed(self, value):
        self.channel_changed(value)
        self.apply_all()
        
    def level(self, value):
        self._level_mode = value
        self.apply_all()

    def linematch(self, value):
        self._linematch_mode = value
        self.apply_all()

    def direction(self, value):
        self._direction = value
        self.apply_all()

    def apply_all(self):
        ch = self.file.channel[self.widgets['channel'].get()]
        z = ch.Z.copy()
        N = np.copy(self.file.N)
        
        # --- LEVEL ---
        match self._level_mode:
            case "General": z = flat.level_plane(z, N)
            case "Cara dominant": z = flat.level_facet(z, N)
            case "Cap": pass

        # --- LINEMATCH ---
        if not self._direction: 
            z = z.T; N = N[::-1]

        match self._linematch_mode:
            case "median": z = flat.linematch_median(z, N)
            case "median_diff": z = flat.linematch_median_diff(z, N)
            case "modus": z = flat.linematch_modus(z, N)
            case "match": z = flat.linematch_match(z, N)
            case "Cap": pass

        if not self._direction: z = z.T; N = N[::-1]

        # --- FINAL ---
        self.z = z
        self.lims, self.z = ch.set_lims(self.z, ch.name)
        self.update_fig(ch)