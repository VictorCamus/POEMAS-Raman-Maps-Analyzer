import numpy as np

from window import BaseMapWindow
from process import flatten as flat
from process.basics import set_lims
from .base import BaseMenu
from window.widgets import Widget

class GestorCorreccio(BaseMenu):  # Classe que gestiona les accions relacionades amb els perfils de fletxes.
    ordre = 20 # Atribut per a ordenar els menús (opcional)
    
    def __init__(self, app):
        super().__init__(app)  # Inicialitza la classe base

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

    def _create_widgets(self):
        files = list(self.files.keys())
        channels = list(self.file.channel.keys())
        opts = {"Sumar": "sum",
                "Multiplicar": "mult",
                "Normalitzar": "norm"}

        self.widgets = {
            "file":    Widget(key = 'file', var_type = str, init = self.file.name,

                       text = "Arxiu:", widget = 'cb', widget_kwargs = {"options": files},
                       setter = self.file_changed),
            "channel": Widget(key = "channel", var_type = str, init = self.channel.name,
                       text = "Canal:", widget = 'cb', widget_kwargs = {"options": channels},
                       setter = self.channel_changed),
            "opt":     Widget(key = "opt", var_type = str, init = self.opt,
                       text = "Opcions:", widget = 'radiobutton', widget_kwargs = {"options": opts},
                       setter = self, mode = 'attr'),
            "value":   Widget(key = 'value', var_type = float, init = 0,
                       text = "Valor:", widget = 'entry',
                       setter = self.reescale_ops),
            "apply":   Widget(key = "apply", var_type = str, init = "Aplicar",
                       widget = 'button',
                       setter = self.aplicar)}

    def reescale_ops(self, value):
        ch = self.file.channel[self.widgets['channel'].get()]; opt = self.opt

        self.z = np.copy(ch.Z)
        match opt:  
            case "sum": self.z += value; self.lims = [ch.lims[0]+value, ch.lims[1]+value]
            case "mult": self.z *= value; self.lims = [ch.lims[0]*value, ch.lims[1]*value]
            case "norm":
                zmin, zmax = self.z.min(), self.z.max()
                self.z = (self.z-zmin)/(zmax-zmin)
                self.lims = [0, 1]
        
        self.update_fig()

class LevelMaps(BaseMapWindow):
    def __init__(self, gestor):
        super().__init__(gestor, "Aplanar mapes")
        self._direction = True
        self._level_mode = "Cap"
        self._linematch_mode = "Cap"

    def _create_widgets(self):
        files = list(self.files.keys())
        channels = list(self.file.channel.keys())
        options_level = ["Cap", "General", "Cara dominant"]
        options_linematch = {'Cap': 'Cap', 'Mediana': 'median', 'Diferència de medianes': 'median_diff', 'Mòdul': 'modus', 'Comparació': 'match'}

        self.widgets = {
            "file": Widget(key="file", var_type=str, init=self.file.name,
                    text="Arxiu:", widget="cb", widget_kwargs={"options": files},
                    setter=self.on_file_changed),

            "channel": Widget(key="channel", var_type=str, init=self.channel.name, text="Canal:",
                       widget="cb", widget_kwargs={"options": channels}, setter=self.on_channel_changed),

            "level": Widget(key="level", var_type=str, init="Cap", text="Aplanament:",
                     widget="radiobutton", widget_kwargs={"options": options_level},
                     setter=self.level),

            "linematch": Widget(key="linematch", var_type=str, init="Cap", text="Corregir línies:",
                         widget="radiobutton", widget_kwargs={"options": options_linematch},
                         setter=self.linematch),

            "direction": Widget(key="direction", var_type=bool, init=True,
                         text="Direcció:", widget="radiobutton",
                         widget_kwargs={"options": {"H": True, "V": False}, "direction": "h"},
                         setter=self.direction),

            "apply": Widget(key="apply", var_type=str, init="Aplicar",
                     widget="button",
                     setter=self.aplicar),

            "apply_all": Widget(key="apply_all", var_type=str, init="Aplicar a tots els fitxers",
                            widget="button",
                            setter=self.aplicar_fitxers),
        }

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

    def apply_all(self, file = None):
        update = False

        if file is None:
            file = self.file
            update = True

        if self.widgets['channel'].get() not in list(file.channel.keys()): return

        ch = file.channel[self.widgets['channel'].get()]
        z = ch.Z.copy()
        npixels = file.geometry.N
        
        # --- LEVEL ---
        match self._level_mode:
            case "General": z = flat.level_plane(z, npixels)
            case "Cara dominant": z = flat.level_facet(z, npixels)
            case "Cap": pass

        # --- LINEMATCH ---
        if not self._direction: z = z.T; npixels = npixels[::-1]

        match self._linematch_mode:
            case "median": z = flat.linematch_median(z, npixels)
            case "median_diff": z = flat.linematch_median_diff(z, npixels)
            case "modus": z = flat.linematch_modus(z, npixels)
            case "match": z = flat.linematch_match(z, npixels)
            case "Cap": pass

        if not self._direction: z = z.T

        # --- FINAL ---

        self.lims, self.z = set_lims(ch.name, z)
        if update: self.update_fig()

    def aplicar_fitxers(self, value):
        curr_file = self.file
        for file in self.files.values():
            self.apply_all(file = file)
            self.aplicar(file = file)

        self.apply_all(file = curr_file)