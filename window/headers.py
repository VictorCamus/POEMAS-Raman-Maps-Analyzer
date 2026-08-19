import numpy as np

from tkinter.ttk import Frame
from tkinter import messagebox
from .widgets import Widget
from drawing.colormap import cmaps

# Fitxer que crea la capçalera per a les pestanyes del notebook.
# Conté també els mètodes per afegir etiquetes, camps d'entrada i combobox a la capçalera.

class HeaderMap:
    def __init__(self, map):
        self.map = map
        self.view = ViewHeaderMap(parent=self.map.model.content, controller=self)

    @property
    def channel(self):
        return self.map.channel

    @property
    def frame(self):
        return self.view.frame

    def set_channel(self, channel):
        self.view.refresh(channel)
        self.map.footer.view.widgets['track_z'].label.config(text=f'{channel.name} ({channel.units})')
        self._redraw(cmap = True, lims = True)

    def on_cmap_change(self, value):
        self.channel.color.cmap_c = value
        self._redraw(cmap = True)
    
    def on_rev_change(self, value):
        ch = self.channel
        if ch.color.cmap_r != value and ch.color.limSup != ch.color.limInf:
            ch.color.limInf, ch.color.limSup = ch.color.limSup, ch.color.limInf
            rb_climsup = self.view.widgets["colSup"]
            rb_climsup.set(ch.color.limSup)
            
            rb_climinf = self.view.widgets["colInf"]
            rb_climinf.set(ch.color.limInf)
            
        ch.color.cmap_r = value
        self._redraw(cmap = True)

    def on_lim_inf_change(self, value: float):
        if value >= self.channel.lims[1]:
            messagebox.showerror(
                "Error en actualitzar la gràfica",
                "El límit inferior ha de ser menor que el superior."
            )
            
            return

        self.channel.lims[0] = value
        self._redraw(lims = True)
    
    def on_lim_sup_change(self, value: float):
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

class ViewHeaderMap:
    def __init__(self, parent, controller):
        self.controller = controller

        self.frame = Frame(parent)
        self.frame.columnconfigure(0, weight=1)

        self._create_widgets()

    @property
    def channel(self):
        return self.controller.channel

    def _create_widgets(self): # Afegeix controls per editar els límits del mapa.
        self.widgets = {
            'cmap_c': Widget(key='cmap_c', var_type=str, init=self.channel.name,
                      text="Color mapa:", widget='cb',
                      widget_kwargs={"options": cmaps, "width": '10'},
                      setter=self.controller.on_cmap_change),
            'cmap_r': Widget(key='cmap_r', var_type=bool, init=False,
                      widget='radiobutton',
                      widget_kwargs={"options": {'N': False, 'R': True}, 'direction': 'h'},
                      setter=self.controller.on_rev_change),
            'limSup': Widget(key='limSup', var_type=float, init=self.channel.lims[1],
                      text="Valor màxim:", widget='entry', widget_kwargs={"width": 10},
                      setter=self.controller.on_lim_sup_change),
            'limInf': Widget(key='limInf', var_type=float, init=self.channel.lims[0],
                      text="Valor mínim:", widget='entry', widget_kwargs={"width": 10},
                      setter=self.controller.on_lim_inf_change),
            'cscale': Widget(key='cscale', var_type=str, init='w',
                      text="Color escala:", widget='radiobutton',
                      widget_kwargs={"options": {'B': 'w', 'N': 'k'}, 'direction': 'h'},
                      setter=self.controller.on_scale_change),
            'colSup': Widget(key='colSup', var_type=str, init=self.channel.color.limSup,
                      widget='radiobutton',
                      widget_kwargs={'options': {'B': 'w', 'N': 'k'}, 'direction': 'h'},
                      setter=self.controller.on_col_sup_change),
            'colInf': Widget(key='colInf', var_type=str, init=self.channel.color.limInf,
                      widget='radiobutton',
                      widget_kwargs={'options': {'B': 'w', 'N': 'k'}, 'direction': 'h'},
                      setter = self.controller.on_col_inf_change)}

        layout = [(0, 3, 'cmap_c'), (0, 5, 'cmap_r'), (0, 7, 'limSup'), (0, 9, 'colSup'),
                  (1, 3, 'cscale'),                   (1, 7, 'limInf'), (1, 9, 'colInf')]

        for row, col, key in layout: self.widgets[key].add(self.frame, row, col)

    def refresh(self, ch = None): # Canvia la capçalera en canviar de canal.
        if not ch: return

        # ---- 1. Actualitzar els combobox dels colors del mapa----
        self.widgets["cmap_c"].set(ch.color.cmap_c)
        self.widgets["cmap_r"].set(ch.color.cmap_r)

        # ---- 2. Actualitzar els combobox dels colors de l'escala ----
        self.widgets["cscale"].set(ch.color.scale)
        self.widgets["colSup"].set(ch.color.limSup)
        self.widgets["colInf"].set(ch.color.limInf)
        
        # ---- 3. Actualitzar els camps d'entrada dels límits ----
        self.widgets["limInf"].set(f"{ch.lims[0]:g}")
        self.widgets["limSup"].set(f"{ch.lims[1]:g}")

class HeaderSpec:
    def __init__(self, spec):
        self.spec = spec
        self.view = ViewHeaderSpec(parent=self.spec.model.content, controller=self)

        self.xlabels = {'nm': 'λ (nm)', 'eV': 'E (eV)', '1/cm': r'Raman Shift (cm⁻¹)'}

    @property
    def channel(self):
        return self.spec.channel

    @property
    def frame(self):
        return self.view.frame

    def on_lim_inf_change(self, value):
        if value >= self.channel.lims[1]:
            messagebox.showerror(
                "Error en actualitzar la gràfica",
                "El límit inferior ha de ser menor que el superior."
            )

            return

        self.channel.lims[0] = value
        self._redraw()

    def on_lim_sup_change(self, value):
        if value <= self.channel.lims[0]:
            messagebox.showerror(
                "Error en actualitzar la gràfica",
                "El límit inferior ha de ser menor que el superior."
            )
            return

        self.channel.lims[1] = value
        self._redraw()

    def on_spectra_left_change(self, value):
        self.channel.spectra_lims[0] = value
        self.spec.axis.set_xlim(value, self.view.widgets['right'].get())
        self.spec.canvas.draw_idle()
        self._update_map(self.channel)

    def on_spectra_right_change(self, value):
        self.channel.spectra_lims[1] = value
        self.spec.axis.set_xlim(self.view.widgets['left'].get(), value)
        self.spec.canvas.draw_idle()
        self._update_map(self.channel)

    def on_spectra_bottom_change(self, value):
        self.spec.axis.set_ylim(value, self.view.widgets['top'].get())
        self.spec.canvas.draw_idle()

    def on_spectra_top_change(self, value):
        self.spec.axis.set_ylim(self.view.widgets['bottom'].get(), value)
        self.spec.canvas.draw_idle()

    def on_units_change(self, value):
        self.spec.axis.set_xlabel(self.xlabels[value])
        xdata = self.channel.xdata[value]

        self.spec.line.set_xdata(xdata)
        self.spec.bkgline.set_xdata(xdata)

        self.channel.spectra_lims = [round(min(xdata), 3), round(max(xdata), 3)]
        self.spec.axis.set_xlim(*self.channel.spectra_lims)

        self.view.widgets['left'].set(self.channel.spectra_lims[0])
        self.view.widgets['right'].set(self.channel.spectra_lims[1])
        self.spec.footer.view.widgets['track_x'].label.config(text = self.xlabels[value])
        self.spec.canvas.draw_idle()
        self._update_map(self.channel)

        return

    def on_data_change(self, value):
        if not hasattr(self.spec, 'line'): return

        self.spec.line.set_visible(value)
        self.spec.canvas.draw_idle()

    def on_log_change(self, value):
        if not hasattr(self.spec, 'line'): return

        if value:
            self.spec.axis.set_yscale('log')
            self.view.widgets['bottom'].set(1)
            self.spec.axis.set_ylim(bottom = 1)
        else:
            self.spec.axis.set_yscale('linear')
            self.view.widgets['bottom'].set(0)
            self.spec.axis.set_ylim(bottom = 0)

        self.spec.canvas.draw_idle()

    def on_bkg_change(self, value):
        self.spec.bkgline.set_visible(value)
        self.spec.plot_data()

        self.spec.canvas.draw_idle()

        self._update_map(self.channel)

    def _redraw(self):
        ch = self.channel
        map = self.spec.model.map

        map.image.set_clim(*ch.lims)
        map.cbar.limInf.set_text(f"{ch.lims[0]:g}" + (f" {ch.units}" if ch.units else ""))
        map.cbar.limSup.set_text(f"{ch.lims[1]:g}" + (f" {ch.units}" if ch.units else ""))
        map.image.set_data(ch.Z)

        map.canvas.draw_idle()

    def _update_map(self, channel):
        x = channel.xdata[self.view.widgets['units'].get()]
        spectra = channel.spectra

        lim_inf, lim_sup = channel.spectra_lims
        mask = ((x >= lim_inf) & (x <= lim_sup))

        if self.view.widgets['bkg'].get():
            Z = np.nansum(spectra[:, :, mask], axis=2, dtype=float)
        else:
            Z = np.nansum(np.maximum(spectra[:, :, mask] - channel.spec_bkg[:, :, mask], 0), axis=2, dtype=float)

        Z[~self.spec.model.controller.objects.mask] = np.nan
        channel.Z = Z

        channel.update_lims()

        self.spec.model.map.header.view.widgets["limInf"].set(channel.lims[0])
        self.spec.model.map.header.view.widgets["limSup"].set(channel.lims[1])

        self._redraw()

class ViewHeaderSpec:
    def __init__(self, parent, controller):
        self.controller = controller

        self.frame = Frame(parent)
        self.frame.columnconfigure(0, weight=1)

        self._create_widgets()

    @property
    def channel(self):
        return self.controller.channel

    def _create_widgets(self):
        self.widgets = {
            'laser': Widget(key='laser', var_type=str, init=self.controller.spec.model.controller.laser,
                     text='λ₀ (nm):', widget='entry', widget_kwargs={"state": 'readonly', "width": 8}),

            'left':  Widget(key="left", var_type=float, init=self.channel.spectra_lims[0],
                     text="Eix X", widget='entry', widget_kwargs={"width": 10},
                     setter=self.controller.on_spectra_left_change),

            'right': Widget(key="right", var_type=float, init=self.channel.spectra_lims[1],
                     widget='entry', widget_kwargs={"width": 10},
                     setter=self.controller.on_spectra_right_change),

            'data':  Widget(key = "data", var_type = bool, init = True,
                     text = "Dades:", widget = 'checkbutton',
                     setter = self.controller.on_data_change),

            'log': Widget(key='log', var_type=bool, init=False,
                          text="Log Y:", widget='checkbutton',
                          setter=self.controller.on_log_change),

            'units': Widget(key="units", var_type=str, init='nm',
                     text="Unitats", widget='cb', widget_kwargs={"options": ["nm", "eV", "1/cm"], "width": 8},
                     setter = self.controller.on_units_change),

            'bottom': Widget(key = "bottom", var_type = float, init = 0,
                      text = "Eix Y", widget = 'entry', widget_kwargs = {"width": 10},
                      setter = self.controller.on_spectra_bottom_change),

            'top':   Widget(key = 'top', var_type = float, init = 1,
                     widget = 'entry', widget_kwargs = {"width": 10},
                     setter = self.controller.on_spectra_top_change),

            'bkg': Widget(key="bkg", var_type=bool, init=True,
                          text="Fons:", widget='checkbutton',
                          setter = self.controller.on_bkg_change),

            'etiq':  Widget(key = "etiq", var_type = bool, init = False,
                     text = "Etiquetes:", widget = 'checkbutton')}

        layout = [(0, 1, 'laser'), (0, 3, 'left'),   (0, 5, 'right'), (0, 7, 'data'), (0, 9, 'log'),
                  (1, 1, 'units'), (1, 3, 'bottom'), (1, 5, 'top'),   (1, 7, 'bkg'),  (1, 9, 'etiq')]

        for row, col, key in layout: self.widgets[key].add(self.frame, row, col)