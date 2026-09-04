import numpy as np

from tkinter.ttk import Frame
from tkinter import messagebox

from classes.fits import Peak
from .widgets import Widget
from drawing.colormap import cmaps
from drawing.mapdraw import update_data
from process.mathfuncs import DEFAULT_PARAMS, get_units

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

    def set_channel(self, ch):
        self.view.refresh(ch)
        self.map.footer.view.widgets['track_z'].label.config(text=f'{ch.name} ({ch.units})')
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

        layout = [(0, 1, 'cmap_c'), (0, 3, 'cmap_r'), (0, 4, 'limSup'), (0, 6, 'colSup'),
                  (1, 1, 'cscale'),                   (1, 4, 'limInf'), (1, 6, 'colInf')]

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
        self.channel.spectra.lims[0] = value
        self.spec.axis.set_xlim(self.channel.spectra.lims)
        self.spec.canvas.draw_idle()
        self._update_map(self.channel)

    def on_spectra_right_change(self, value):
        self.channel.spectra.lims[1] = value
        self.spec.axis.set_xlim(self.channel.spectra.lims)
        self.spec.canvas.draw_idle()
        self._update_map(self.channel)

    def on_spectra_bottom_change(self, value):
        self.spec.axis.set_ylim(value, self.view.widgets['top'].get())
        self.spec.canvas.draw_idle()

    def on_spectra_top_change(self, value):
        self.spec.axis.set_ylim(self.view.widgets['bottom'].get(), value)
        self.spec.canvas.draw_idle()

    def on_units_change(self, value):
        self.channel.spectra.units = value
        self.spec.axis.set_xlabel(self.spec.xlabels[value])
        xdata = self.channel.spectra.x

        self.spec.line.set_xdata(xdata)
        self.spec.bkgline.set_xdata(xdata)

        self.channel.spectra.lims = [round(min(xdata), 3), round(max(xdata), 3)]
        self.spec.axis.set_xlim(*self.channel.spectra.lims)

        self.view.widgets['left'].set(self.channel.spectra.lims[0])
        self.view.widgets['right'].set(self.channel.spectra.lims[1])
        self.spec.footer.view.widgets['track_x'].label.config(text = self.spec.xlabels[value])
        self.spec.canvas.draw_idle()

        self._update_map(self.channel)

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

    def on_etiq_change(self, value):
        for etiq in self.spec.etiquette.values(): etiq.set_visible(value)

        self.spec.canvas.draw_idle()

    def delete_fit(self, value):
        if self.view.fit_key == 'rawdata': return

        self.channel.spectra.fits.pop(self.view.fit_key)
        self.view.update_fits()

    def on_ccd_change(self, value):
        spectra = self.channel.spectra
        spectra.CCD_active = value

        if value: spectra.ydata = (spectra.ydata - spectra.bkgdata) / spectra.CCD + spectra.bkgdata
        else: spectra.ydata = (spectra.ydata - spectra.bkgdata) * spectra.CCD + spectra.bkgdata

        self._update_map(self.channel)
        self.spec.plot_data()

    def _redraw(self):
        ch = self.channel
        map = self.spec.model.map

        map.image.set_clim(*ch.lims)
        map.cbar.limInf.set_text(f"{ch.lims[0]:g}" + (f" {ch.units}" if ch.units else ""))
        map.cbar.limSup.set_text(f"{ch.lims[1]:g}" + (f" {ch.units}" if ch.units else ""))

        update_data(map.image, ch.Z, self.spec.objects.mask)
        map.image.set_cmap(ch.color.cmap)

        map.header.view.widgets['limInf'].set(ch.lims[0])
        map.header.view.widgets['limSup'].set(ch.lims[1])
        map.header.view.widgets['cmap_c'].set(ch.color.cmap_c)

        map.canvas.draw_idle()

    def _update_map(self, channel):
        if self.view.fit_key != 'rawdata': return

        spectra = channel.spectra

        lim_inf, lim_sup = spectra.lims
        mask = ((spectra.x >= lim_inf) & (spectra.x <= lim_sup))

        if self.view.widgets['bkg'].get():
            channel.Z = np.nansum(spectra.ydata[:, :, mask], axis=2, dtype=float)
        else:
            channel.Z = np.nansum(np.maximum(spectra.ydata[:, :, mask] - self.spec.bkg[mask], 0), axis=2, dtype=float)

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

    @property
    def fit(self):
        return self._fit

    @fit.setter
    def fit(self, value):
        spec = self.channel.spectra

        if value in spec.fits:
            self._fit = spec.fits[value]
            self.fit_key = value

            # En canviar de fit, seleccionem el primer pic
            self._peak = next(iter(self.fit.peaks.values()))
            self.peak_key = self.peak.ref

            if self.parameter_key in self.peak.params: self._parameter = self.peak.params[self.parameter_key]
            else: self.parameter_key, self._parameter = next(iter(self.peak.params.items()))

            spec.units = self._fit.units
            self.widgets['units'].set(spec.units)
            self.widgets['units'].config(state = 'disabled')

            start, stop = round(spec.x[self.fit.xrange.start], 3), round(spec.x[self.fit.xrange.stop], 3)
            spec.lims = [start, stop] if start < stop else [stop, start]
            self.widgets['left'].set(spec.lims[0])
            self.widgets['right'].set(spec.lims[1])

            self.controller.spec.axis.set_xlim(spec.lims)

            self.update_peaks()

        elif value == 'rawdata':
            self.fit_key = 'rawdata'
            self.peak_key, self.peak = None, None
            self.parameter_key, self.parameter = None, None

            self.widgets['units'].config(state = 'readonly')
            self.channel.color.cmap_c = 'Spectra'
            self.channel.units = 'cts'

            self.controller.spec.model.map.footer.view.widgets['track_z'].label.config(text=f'{self.channel.name} ({self.channel.units})')
            self.controller._update_map(self.channel)

        self.controller.spec.plot_data()

    @property
    def peak(self):
        return self._peak

    @peak.setter
    def peak(self, value):
        if value is None:
            combo = self.widgets['peak'].widget
            combo.config(values = [])
            combo.options = {}
            combo.set('')

            return

        if value in self.fit.peaks:
            self._peak = self.fit.peaks[value]
            self.peak_key = value

            # En canviar de pic, seleccionem el primer paràmetre

            if self.parameter_key in self.peak.params: self._parameter = self.peak.params[self.parameter_key]
            else: self.parameter_key, self._parameter = next(iter(self.peak.params.items()))

            self.update_params()

        elif value == 'r2':
            self.parameter_key, self.parameter = None, None

            self.channel.Z = self.fit.r2
            self.channel.update_lims()
            self.channel.color.cmap_c = 'jet'
            self.channel.units = ''

            self.controller.spec.model.map.footer.view.widgets['track_z'].label.config(text = 'r2')
            self.controller._redraw()

    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, value):
        if value is None:
            combo = self.widgets['parameter'].widget
            combo.config(values = [])
            combo.options = {}
            combo.set('')
            return

        if value in self.peak.params:
            self._parameter = self.peak.params[value]
            self.parameter_key = value

        self.channel.Z = self._parameter
        self.channel.update_lims()

        param = DEFAULT_PARAMS[self.parameter_key]
        self.channel.units = get_units(dim = param['dim'], units = self.channel.spectra.units)
        self.channel.color.cmap_c = param['color']

        self.controller.spec.model.map.footer.view.widgets['track_z'].label.config(text = f'{self.parameter_key} ({self.channel.units})')
        self.controller._redraw()

    def update_fits(self):
        fits = ['rawdata', *self.channel.spectra.fits]

        combo = self.widgets["fit"].widget
        combo.config(values=fits)
        combo.options = dict(zip(fits, fits))

        if self.fit_key in fits:
            combo.set(self.fit_key)
            self.fit = self.fit_key
        else:
            combo.set(fits[0])
            self.fit = fits[0]

    def update_peaks(self):
        if self.fit is None or not self.fit.peaks or not hasattr(self, 'widgets'):
            return

        refs = [*self.fit.peaks.keys(), 'r2']
        peaks = [*[peak.name for peak in self.fit.peaks.values()], 'r2']
        mm = dict(zip(refs, peaks))
        combo = self.widgets["peak"].widget
        combo.config(values=peaks)
        combo.options = dict(zip(peaks, refs))

        if self.peak_key in self.fit.peaks:
            combo.set(mm[self.peak_key])
            self.peak = self.peak_key
        else:
            combo.set(refs[0])
            self.peak = refs[0]

    def update_params(self):
        if self.peak is None or not self.peak.params or not hasattr(self, 'widgets'):
            return

        params = list(self.peak.params.keys())

        combo = self.widgets["parameter"].widget
        combo.config(values=params)
        combo.options = dict(zip(params, params))

        if self.parameter_key in params:
            combo.set(self.parameter_key)
            self.parameter = self.parameter_key
        else:
            combo.set(params[0])
            self.parameter = params[0]

    def _create_widgets(self):
        self._fit, self._peak, self._parameter = None, None, None
        self.fit_key = 'rawdata'
        opts_fits = [self.fit_key, *self.channel.spectra.fits]
        opts_peaks, opts_pars = [], []

        self.peak_key = None
        self.parameter_key = None

        self.widgets = {
            'units': Widget(key="units", var_type=str, init=self.channel.spectra.units,
                            text="Unitats", widget='cb', widget_kwargs={"options": ["nm", "eV", "1/cm"], "width": 8},
                            setter=self.controller.on_units_change),

            'left':  Widget(key="left", var_type=float, init=self.channel.spectra.lims[0],
                     text="Eix X", widget='entry', widget_kwargs={"width": 10},
                     setter=self.controller.on_spectra_left_change),

            'right': Widget(key="right", var_type=float, init=self.channel.spectra.lims[1],
                     widget='entry', widget_kwargs={"width": 10},
                     setter=self.controller.on_spectra_right_change),

            'data':  Widget(key = "data", var_type = bool, init = True,
                     text = "Dades:", widget = 'checkbutton',
                     setter = self.controller.on_data_change),

            'log': Widget(key='log', var_type=bool, init=False,
                          text="Log Y:", widget='checkbutton',
                          setter=self.controller.on_log_change),

            'fit': Widget(key='fit', var_type=str, init=self.fit,
                          text='Ajusts:', widget='cb', widget_kwargs={'options': opts_fits, 'width': 8},
                          setter=self, mode='attr'),

            'bottom': Widget(key = "bottom", var_type = float, init = 0,
                      text = "Eix Y", widget = 'entry', widget_kwargs = {"width": 10},
                      setter = self.controller.on_spectra_bottom_change),

            'top':   Widget(key = 'top', var_type = float, init = 1,
                     widget = 'entry', widget_kwargs = {"width": 10},
                     setter = self.controller.on_spectra_top_change),

            'bkg': Widget(key="bkg", var_type=bool, init=True,
                          text="Fons:", widget='checkbutton',
                          setter = self.controller.on_bkg_change),

            'etiq':  Widget(key = "etiq", var_type = bool, init = True,
                     text = "Etiquetes:", widget = 'checkbutton',
                     setter=self.controller.on_etiq_change),

            'peak': Widget(key='peak', var_type=str, init=self.peak,
                           text='Pic:', widget='cb', widget_kwargs={'options': opts_peaks, 'width': 8},
                           setter=self, mode='attr'),

            'parameter': Widget(key='parameter', var_type=str, init=self.parameter,
                                text='Paràmetre:', widget='cb', widget_kwargs={'options': opts_pars, 'width': 8},
                                setter=self, mode='attr'),

            'del_fit': Widget(key='del_fit', var_type=str, init='Eliminar',
                              widget='button', setter=self.controller.delete_fit),

            'CCD':  Widget(key = "CCD", var_type = bool, init = self.channel.spectra.CCD_active,
                     text = "CCD:", widget = 'checkbutton',
                     setter=self.controller.on_ccd_change)}

        layout = [(0, 1, 'units'), (0, 3, 'left'),        (0, 5, 'right'),   (0, 6, 'data'), (0, 8, 'log'),
                  (1, 1, 'fit'),   (1, 3, 'bottom'),      (1, 5, 'top'),     (1, 6, 'bkg'),  (1, 8, 'etiq'),
                  (2, 1, 'peak'),  (2, 3, 'parameter'),   (2 ,5, 'del_fit'), (2, 6, 'CCD')]

        for row, col, key in layout: self.widgets[key].add(self.frame, row, col)