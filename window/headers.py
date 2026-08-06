from tkinter.ttk import Frame, Label, Entry, Combobox
from tkinter import messagebox, IntVar, BooleanVar, DoubleVar, StringVar, Checkbutton
from .labels import build_grid
from drawing.colormap import cmaps
from drawing.colormap import cmaps_matplotlib
from drawing import mapdraw as mapa
import numpy as np

# Fitxer que crea la capçalera per a les pestanyes del notebook.
# Conté també les mètodes per afegir etiquetes, camps d'entrada i comboboxes a la capçalera.

class GestorHeaderAFM:
    def __init__(self, map):
        self.map = map
        self.view = CrearHeaderAFM(parent=self.map.model.content, controller=self)

    @property
    def channel(self):
        return self.map.channel

    def set_channel(self, channel):
        self.view.refresh(channel)
        self._redraw(cmap = True, lims = True)

    def on_cmap_change(self, value):
        self.channel.color.cmap_c = value
        self._redraw(cmap = True)
    
    def on_rev_change(self, value, widget):
        ch = self.channel
        if ch.color.cmap_r != value and ch.color.limSup != ch.color.limInf:
            ch.color.limInf, ch.color.limSup = ch.color.limSup, ch.color.limInf
            rb_climsup = widget["colSup"]
            rb_climsup.value.set(ch.color.limSup)
            
            rb_climinf = widget["colInf"]
            rb_climinf.value.set(ch.color.limInf)
            
        ch.color.cmap_r = value
        self._redraw(cmap = True)

    def on_lim_inf_change(self, value):
        if value >= self.channel.lims[1]:
            messagebox.showerror(
                "Error en actualitzar la gràfica",
                "El límit inferior ha de ser menor que el superior."
            )
            
            return

        self.channel.lims[0] = value
        self._redraw(lims = True)
    
    def on_lim_sup_change(self, value):
        if value <= self.channel.lims[0]:
            messagebox.showerror(
                "Error en actualitzar la gràfica",
                "El límit inferior ha de ser menor que el superior."
            )
            return

        self.channel.lims[1] = value
        self._redraw(lims = True)

    def on_scale_change(self, value):
        self.channel.color.scale = value
        self.map.escala.color = self.channel.color.scale
        self.map.canvas.draw_idle()
        
    def on_col_sup_change(self, value):
        self.channel.color.limSup = value
        self._redraw(cmap = True)
    
    def on_col_inf_change(self, value):
        self.channel.color.limInf = value
        self._redraw(cmap = True)
        
    def _redraw(self, cmap = False, lims = False):
        ch = self.channel

        if cmap: 
            self.map.image.set_cmap(ch.color.cmap)
            self.map.cbar.limInf.set_color(ch.color.limInf)
            self.map.cbar.limSup.set_color(ch.color.limSup)
        
        if lims:
            self.map.image.set_clim(*ch.lims)
            self.map.cbar.limInf.set_text(f"{ch.lims[0]:g}" + (f" {ch.units}" if ch.units else ""))
            self.map.cbar.limSup.set_text(f"{ch.lims[1]:g}" + (f" {ch.units}" if ch.units else ""))

        self.map.canvas.draw_idle()

class CrearHeaderAFM:
    def __init__(self, parent, controller):
        self.controller = controller

        self.frame = Frame(parent)
        self.frame.columnconfigure(0, weight=1)

        self._editar_limits()
        self._color_mapa_escala()

    @property
    def channel(self):
        return self.controller.channel

    def _color_mapa_escala(self): # Afegeix controls per canviar el color del mapa i de l'escala.
        def _grid_color():
            return [
                (("cmap_c", str, self.channel.name),
                 ("Color mapa:", 'cb', {"options": cmaps, "width": '10'}),
                 (self.controller.on_cmap_change, "args", {})),
                (("cscale", str, 'w'),
                 ("Color escala:", 'radiobutton', {"options": {'B': 'w', 'N': 'k'}, 'vertical': False}),
                 (self.controller.on_scale_change, "args", {})),
            ]

        def _grid_crev():
            return [
                (("cmap_r", bool, False),
                (None, 'radiobutton', {"options": {'N': False, 'R': True}, 'vertical': False}),
                (self.controller.on_rev_change, "args", {'widget': self.widgets_lims})),
            ]
        
        self.widgets_scale = build_grid(self.frame, _grid_color(), row=0, col=3, button=False)
        widget_rev = build_grid(self.frame, _grid_crev(), row=0, col=5, button=False)
        self.widgets_scale.update(widget_rev)

    def _editar_limits(self): # Afegeix controls per editar els límits del mapa.
        def _grid_lims():
            return [
                (("limSup", float, self.channel.lims[1]),
                 ("Valor màxim:", 'entry', {"width": 10}),
                 (self.controller.on_lim_sup_change, "args", {})),
                (("limInf", float, self.channel.lims[0]),
                 ("Valor mínim:", 'entry', {"width": 10}),
                 (self.controller.on_lim_inf_change, "args", {}))
            ]
        def _color_lims():
            return [
                (("colSup", str, self.channel.color.limSup),
                 (None, 'radiobutton', {'options': {'B': 'w', 'N': 'k'}, 'vertical': False}),
                 (self.controller.on_col_sup_change, "args", {})),
                (("colInf", str, self.channel.color.limInf),
                 (None, 'radiobutton', {'options': {'B': 'w', 'N': 'k'}, 'vertical': False}),
                 (self.controller.on_col_inf_change, "args", {}))
            ]

        self.widgets_lims = build_grid(self.frame, _grid_lims(), row=0, col=7, button=False)
        col_lims = build_grid(self.frame, _color_lims(), row=0, col=9, button=False)
        self.widgets_lims.update(col_lims)

    def refresh(self, ch = None): # Canvia la capçalera en canviar de canal.
        if not ch: return

        # ---- 1. Actualitzar els comboboxes dels colors del mapa----
        combo_cmap = self.widgets_scale["cmap_c"]
        combo_cmap.set(ch.color.cmap_c)

        rb_cmap_rev = self.widgets_scale["cmap_r"]
        rb_cmap_rev.value.set(ch.color.cmap_r)

        # ---- 2. Actualitzar els comboboxes dels colors de l'escala ----
        rb_cscale = self.widgets_scale["cscale"]
        rb_cscale.value.set(ch.color.scale)
        
        rb_climsup = self.widgets_lims["colSup"]
        rb_climsup.value.set(ch.color.limSup)
        
        rb_climinf = self.widgets_lims["colInf"]
        rb_climinf.value.set(ch.color.limInf)
        
        # ---- 3. Actualitzar els camps d'entrada dels límits ----
        self.widgets_lims["limInf"].value.set(f"{ch.lims[0]:g}")
        self.widgets_lims["limSup"].value.set(f"{ch.lims[1]:g}")

class GestorHeaderSpectrum:
    def __init__(self, map):
        self.map = map
        self.view = CrearHeaderSpectrum(parent=self.map.model.content, controller=self)

        self.xlabels = {'nm': 'λ (nm)', 'eV': 'E (eV)', '1/cm': r'Raman Shift (cm⁻¹)'}

    @property
    def channel(self):
        return self.map.channel

    def on_lim_inf_change(self, value):
        if value >= self.channel.lims[1]:
            messagebox.showerror(
                "Error en actualitzar la gràfica",
                "El límit inferior ha de ser menor que el superior."
            )

            return

        self.channel.lims[0] = value
        self._redraw(lims=True)

    def on_lim_sup_change(self, value):
        if value <= self.channel.lims[0]:
            messagebox.showerror(
                "Error en actualitzar la gràfica",
                "El límit inferior ha de ser menor que el superior."
            )
            return

        self.channel.lims[1] = value
        self._redraw(lims=True)

    def on_spectra_left_change(self, value):
        self.channel.spectra_lims[0] = value
        self.map.axis.set_xlim(value, self.view.widgets_xlim['right'].value.get())
        self.map.canvas.draw_idle()
        self._update_spectra_Z(self.channel)

    def on_spectra_right_change(self, value):
        self.channel.spectra_lims[1] = value
        self.map.axis.set_xlim(self.view.widgets_xlim['left'].value.get(), value)
        self.map.canvas.draw_idle()
        self._update_spectra_Z(self.channel)

    def on_spectra_bottom_change(self, value):
        self.map.axis.set_ylim(value, self.view.widgets_ylim['top'].value.get())
        self.map.canvas.draw_idle()

    def on_spectra_top_change(self, value):
        self.map.axis.set_ylim(self.view.widgets_ylim['bottom'].value.get(), value)
        self.map.canvas.draw_idle()

    def on_units_change(self, value):
        self.map.axis.set_xlabel(self.xlabels[value])
        spec = self.map.line.get_ydata()
        xdata = self.channel.xdata[value]

        self.map.line.set_data(xdata, spec)
        self.channel.spectra_lims = round(min(xdata), 3), round(max(xdata), 3)
        self.map.axis.set_xlim(*self.channel.spectra_lims)

        self.view.widgets_xlim['left'].value.set(self.channel.spectra_lims[0])
        self.view.widgets_xlim['right'].value.set(self.channel.spectra_lims[1])
        self.map.footer.view.widgets['track_x']._label.config(text = self.xlabels[value])
        self.map.canvas.draw_idle()
        self._update_spectra_Z(self.channel)

        return

    def on_data_change(self, value):
        if not hasattr(self.map, 'line'): return

        self.map.line.set_visible(value)
        self.map.canvas.draw_idle()

    def on_log_change(self, value):
        if not hasattr(self.map, 'line'): return

        if value:
            self.map.axis.set_yscale('log')
            self.view.widgets_ylim['bottom'].value.set(1)
            self.map.axis.set_ylim(bottom = 1)
        else:
            self.map.axis.set_yscale('linear')
            self.view.widgets_ylim['bottom'].value.set(0)
            self.map.axis.set_ylim(bottom = 0)

        self.map.canvas.draw_idle()

    def _redraw(self, lims=False, Z=False):
        ch = self.channel
        map = self.map.model.map

        map.image.set_clim(*ch.lims)
        map.cbar.limInf.set_text(f"{ch.lims[0]:g}" + (f" {ch.units}" if ch.units else ""))
        map.cbar.limSup.set_text(f"{ch.lims[1]:g}" + (f" {ch.units}" if ch.units else ""))
        map.image.set_data(ch.Z)

        map.canvas.draw_idle()

    def _update_spectra_Z(self, channel):
        x = channel.xdata[self.view.widgets['units'].value.get()]
        spectra = channel.spectra

        lim_inf, lim_sup = channel.spectra_lims
        mask = ((x >= lim_inf) & (x <= lim_sup))

        channel.Z = np.nansum(spectra[:, :, mask], axis=2)
        channel.update_lims()

        self.map.model.map.header.view.widgets_lims["limInf"].value.set(channel.lims[0])
        self.map.model.map.header.view.widgets_lims["limSup"].value.set(channel.lims[1])

        self._redraw(lims=True, Z=True)

class CrearHeaderSpectrum:
    def __init__(self, parent, controller):
        self.controller = controller

        self.frame = Frame(parent)
        self.frame.columnconfigure(0, weight=1)

        self._laser_units()
        self._editar_limits_spectra()
        self._marks()

    @property
    def channel(self):
        return self.controller.channel

    def _laser_units(self):
        def _grid():
            return [
                (("laser", str, self.controller.map.model.controller.laser),
                 ('λ₀ (nm):', 'entry', {"state": 'readonly', "width": 8}),
                 (self.controller.on_units_change, "args")),

                (("units", str, 'nm'),
                 ("Unitats", 'cb', {"options": ["nm", "eV", "1/cm"], "width": 8}),
                 (self.controller.on_units_change, "args"))
            ]

        self.widgets = build_grid(self.frame, _grid(), row=0, col=1, button=False)

    def _editar_limits_spectra(self):
        def _grid_xlim_spectra():
            return [
                (("left", float, self.channel.spectra_lims[0]),
                 ("Eix X", 'entry', {"width": 10}),
                 (self.controller.on_spectra_left_change, "args")),

                (("right", float, self.channel.spectra_lims[1]),
                 ("", 'entry', {"width": 10}),
                 (self.controller.on_spectra_right_change, "args"))
            ]

        def _grid_ylim_spectra():
            return [
                (("bottom", float, 0),
                 ("Eix Y", 'entry', {"width": 10}),
                 (self.controller.on_spectra_bottom_change, "args")),

                (("top", float, 1),
                 ("", 'entry', {"width": 10}),
                 (self.controller.on_spectra_top_change, "args"))
            ]

        self.widgets_xlim = build_grid(self.frame, _grid_xlim_spectra(), row=0, col=3, button=False, vertical = False)
        self.widgets_ylim = build_grid(self.frame, _grid_ylim_spectra(), row=1, col=3, button=False, vertical = False)

    def _marks(self):
        def _grid_data_bkg():
            return [
                (("data", bool, True),
                 ("Dades:", 'checkbutton'),
                 (self.controller.on_data_change, "args")),
                (("bkg", bool, True),
                 ("Fons:", 'checkbutton'),
                 (self.controller.on_data_change, "args"))
            ]

        def _grid_log_etiq():
            return [
                (("log", bool, False),
                 ("Log Y:", 'checkbutton'),
                 (self.controller.on_log_change, "args")),
                (("etiq", bool, False),
                 ("Etiquetes:", 'checkbutton'),
                 (self.controller.on_log_change, "args"))
            ]

        self.marks = build_grid(self.frame, _grid_data_bkg(), row=0, col=7, button=False)
        self.marks.update(build_grid(self.frame, _grid_log_etiq(), row=0, col=9, button=False))