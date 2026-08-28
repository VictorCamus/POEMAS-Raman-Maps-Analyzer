from dataclasses import dataclass, field
from tkinter.ttk import LabelFrame, Label
from tkinter import messagebox
from matplotlib.colors import TABLEAU_COLORS
from lmfit import Parameters, minimize
import numpy as np

from window.widgets import Widget
from window.builder import BaseWindow
from process.mathfuncs import Functions, FuncParams, DEFAULT_PARAMS, linear_combination

@dataclass
class FitConfig:
    name: str = 'Fit1'
    peaks: dict[str, Peak] = field(default_factory=dict)

@dataclass
class Peak:
    ref: str = 'P1'
    name: str = ''
    function: str = 'Gaussiana'
    params: dict[str, dict] = field(default_factory=dict)
    bkg: bool = False

    def ydata(self, xdata):
        param_values = {name: par['value'] for name, par in self.params.items()}
        return Functions[self.function](xdata, **param_values)

@dataclass
class PeakResult:
    name: str
    params: dict[str, np.ndarray] = field(default_factory=dict)
    function: str = 'Gaussiana'
    bkg: bool = False

    @property
    def func(self):
        return Functions[self.function]

@dataclass
class FitResult:
    name: str
    units: str
    xrange: slice = field(default_factory=slice)
    config: FitConfig = None
    peaks: dict[str, PeakResult] = field(default_factory=dict)
    r2: np.ndarray = None

class FitSpec(BaseWindow):
    def __init__(self, gestor, config=None):
        self.config = config or FitConfig()

        super().__init__(gestor, "Ajust espectral")
        self.main_frame.pack_configure(fill=None, expand=False)
        self.control_frame.pack_configure(side = 'top', anchor='w')
        self.peaks = {}
        self.spec = self.file.view.spectrum

        self.spec.fitline = {}
        self.spec.fitline['All'], = self.spec.axis.plot(self.xdata, np.full(self.xdata.shape, 0), color='black')
        self.peaks_frame = LabelFrame(self.main_frame)
        self.peaks_frame.pack(side = 'bottom', fill='both', expand=True, pady = 2)

        if self.spec.header.view.fit_key != 'rawdata':
            fit = self.channel.spectra.fits[self.spec.header.view.fit_key]
            self.config = fit.config
            self.widgets['name'].set(self.config.name)

            for peak in self.config.peaks.values():
                self._add_peak(peak = peak)

        layout = [(0, 1, 'name'), (0, 3, 'add'),    (0, 4, 'fit'),
                  (1, 1, 'r2'),   (1, 3, 'remove'), (1, 4, 'fitmap')]

        for row, col, key in layout: self.widgets[key].widget.grid_configure(row = row, column = col)

    @property
    def xdata(self):
        return self.channel.spectra.x[self.xrange]

    @property
    def bkg(self):
        if self.spec.header.view.widgets['bkg'].get():
            bkg = self.channel.spectra.bkg[self.xrange].copy()
            for peak in self.peaks.values():
                if peak.bkg:
                    bkg += peak.ydata(self.xdata)
        else:
            bkg = np.zeros_like(self.channel.spectra.bkg[self.xrange])

        return bkg

    @property
    def xrange(self):
        return self.channel.spectra.xrange

    def _add_peak(self, value = None, peak = None):
        i = len(self.peaks)
        colors = list(TABLEAU_COLORS.values())

        if peak is None:
            peak = Peak(name=f'P{i + 1}')
            peak.params = {name: DEFAULT_PARAMS[name].copy() for name in FuncParams[peak.function]}

        row = i % 3
        col = i // 3

        frame = LabelFrame(self.peaks_frame)
        frame.grid(row=row, column=col, padx=5, pady=5, sticky='nw')

        widgets = {
            'name': Widget(key='name', var_type = str, init=peak.name,
                    widget='entry', widget_kwargs={'width': 8},
                    setter = peak, mode = 'attr'),

            'function': Widget(key='function', var_type = str, init = peak.function,
                        widget='cb', widget_kwargs={'options': Functions.keys(), 'width': 10},
                        setter = self.update_func, setter_kwargs = {'peak': peak}),

            'bkg': Widget(key='bkg', var_type=bool, init=peak.bkg,
                   text = 'Fons:', widget='checkbutton',
                   setter = peak, mode = 'attr')}

        peak.frame = frame
        peak.widgets = widgets

        # Afegim nom i funció
        widgets['name'].add(frame, row=0, col=0)
        widgets['function'].add(frame, row=0, col=1)
        widgets['bkg'].add(frame, row=0, col=2)

        # Capçalera dels paràmetres
        Label(frame, text='Value').grid(row=1, column=1)
        Label(frame, text='Min').grid(row=1, column=2)
        Label(frame, text='Max').grid(row=1, column=3)
        Label(frame, text='Vary').grid(row=1, column=4)

        for row, name in enumerate(FuncParams[peak.function], start=2):
            parameter = peak.params[name]
            self._add_parameter_widgets(peak, parameter, name, row)

        peak.ref = f'P{i+1}'
        self.spec.fitline[peak.ref] = self.spec.axis.fill_between(self.xdata, peak.ydata(self.xdata), 0, color = colors[i+1], alpha=0.6)
        self.peaks[peak.ref] = peak

    def _add_parameter_widgets(self, peak, parameter, name, row):
        widgets = peak.widgets
        widgets[f'{name}_value'] = Widget(key=f'value', var_type=float, init=parameter['value'],
                                   text=f'{name}:', widget='entry', widget_kwargs={'width': 10},
                                   setter = self.update_value, setter_kwargs = {'peak': peak, 'par': name})

        widgets[f'{name}_min'] = Widget(key=f'min', var_type=float, init=parameter['min'],
                                 widget='entry', widget_kwargs={'width': 8},
                                 setter = parameter, mode = 'dict')

        widgets[f'{name}_max'] = Widget(key=f'max', var_type=float, init=parameter['max'],
                                 widget='entry', widget_kwargs={'width': 8},
                                 setter = parameter, mode = 'dict')

        widgets[f'{name}_vary'] = Widget(key=f'vary', var_type=bool, init=parameter['vary'],
                                 widget='checkbutton',
                                 setter = parameter, mode = 'dict')

        widgets[f'{name}_value'].add(peak.frame, row=row, col=0)
        widgets[f'{name}_min'].add(peak.frame, row=row, col=2)
        widgets[f'{name}_max'].add(peak.frame, row=row, col=3)
        widgets[f'{name}_vary'].add(peak.frame, row=row, col=4)

    def update_func(self, func, peak):
        old_params = peak.params
        peak.function = func
        peak.params = {}

        for name in FuncParams[func]:
            if name in old_params: peak.params[name] = old_params[name]
            else: peak.params[name] = DEFAULT_PARAMS[name].copy()

        self._rebuild_peak_widgets(peak)
        self.update_peak(peak.name, ydata = peak.ydata(self.xdata), bkg = peak.bkg)

    def update_peak(self, name, ydata, bkg):
        if not bkg:
            ydata += self.bkg
            verts = np.column_stack([np.r_[self.xdata, self.xdata[::-1]], np.r_[ydata, self.bkg[::-1]]])
        else: verts = np.column_stack([np.r_[self.xdata, self.xdata[::-1]], np.r_[ydata, np.full_like(ydata, 0)]])

        self.spec.fitline[name].set_verts([verts])
        self.spec.canvas.draw_idle()

    def _rebuild_peak_widgets(self, peak):
        for key in list(peak.widgets.keys()):
            if key in ('name', 'function', 'bkg'): continue

            widget = peak.widgets[key]
            if hasattr(widget, 'label'): widget.label.destroy()
            widget.widget.destroy()
            del peak.widgets[key]

        for row, name in enumerate(FuncParams[peak.function], start=2):
            self._add_parameter_widgets(peak, peak.params[name], name, row)

    def update_value(self, value, peak, par):
        peak.params[par]['value'] = value
        self.update_peak(peak.ref, peak.ydata(self.xdata), bkg = peak.bkg)
        self._update_fit()

    def _update_fit(self):
        ydata = np.full(self.xdata.shape, 0, dtype = float)

        for peak in self.peaks.values():
            ydata += peak.ydata(self.xdata)

        self.spec.fitline['All'].set_data(self.xdata, ydata)
        self.spec.canvas.draw_idle()

    def _remove_peak(self, value):
        if not self.peaks: return

        peak = next(reversed(self.peaks.values()))
        self.spec.fitline[peak.ref].remove()
        peak.frame.destroy()

        for key, item in self.peaks.items():
            if item is peak:
                del self.peaks[key]
                break

        self._update_fit()

    def _create_parameters(self):
        params = Parameters()
        for name, peak in self.peaks.items():
            for par_name, par in peak.params.items():
                params.add(f'{name}_{par_name}', value=par['value'], min=par['min'], max=par['max'], vary=par['vary'])

        return params

    def _create_model(self):
        names = list(self.peaks)
        funcs = [self.peaks[name].function for name in names]

        return linear_combination(names, funcs)

    def _create_fit_result(self):
        result = FitResult(name = self.widgets['name'].get(),
                           units = self.channel.spectra.units,
                           config = self.get_config(),
                           xrange = self.xrange)

        for name, peak in self.peaks.items():
            result.peaks[peak.name] = PeakResult(name = peak.name, function = peak.function, bkg = peak.bkg)

            for par in peak.params:
                result.peaks[peak.name].params[par] = np.full(self.channel.Z.shape, np.nan, dtype=float)

            result.r2 = np.full(self.channel.Z.shape, np.nan, dtype=float)

        return result

    def _fitmap(self, value):
        model, init_params = self._init_fit()
        fit_result = self._create_fit_result()

        params = init_params.copy()

        spectra = self.channel.spectra.ydata
        bkg = self.channel.spectra.bkgdata

        for i in range(spectra.shape[0]):
            for j in range(spectra.shape[1]):

                if not self.file.objects.mask[i, j]: continue

                ydata = spectra[i, j][self.xrange] - bkg[i, j][self.xrange]
                result = self._fit(self.xdata, ydata, model, params)

                if result is None:
                    params = init_params.copy()
                    continue

                params = result.params
                yfit = model(self.xdata, params)
                r2 = self._r2(ydata, yfit)

                if not result.success or any(p.stderr is None for p in params.values()):
                    params = init_params.copy()
                    continue

                for name, peak in self.peaks.items():
                    for par_name in peak.params:
                        fit_result.peaks[peak.name].params[par_name][i, j] = params[f'{name}_{par_name}'].value

                    fit_result.r2[i, j] = r2

        name = self.widgets['name'].get()
        self.channel.spectra.fits[name] = fit_result

        combofit = self.spec.header.view.widgets['fit'].widget
        combofit.options[name] = name
        combofit.config(values = list (combofit.options.keys()))

    def _init_fit(self):
        names = list(self.peaks)
        funcs = [self.peaks[name].function for name in names]

        model = linear_combination(names, funcs)
        params = self._create_parameters()

        return model, params

    @staticmethod
    def _fit(x, y, model, params):
        def residual(params):
            return model(x, params) - y

        try:
            return minimize(residual, params, method="least_squares", diff_step=1e-4, max_nfev=500)

        except (ValueError, RuntimeError) as e:
            return None

    @staticmethod
    def _r2(y, yfit):
        ss_res = np.sum((y - yfit) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        r2 = 1 - ss_res / ss_tot

        return r2

    def _draw_fit(self, y, params, r2 = None):
        self.spec.fitline['All'].set_ydata(y)
        self.spec.canvas.draw_idle()

        for name, peak in self.peaks.items():
            for par_name, par in peak.params.items():
                par['value'] = round(params[f'{name}_{par_name}'].value, 3)
                peak.widgets[f'{par_name}_value'].set(par['value'])

        for peak in self.peaks.values():
            self.update_peak(peak.ref, ydata = peak.ydata(self.xdata), bkg = peak.bkg)

        self._update_fit()
        self.widgets['r2'].set(round(r2, 4))

    def _fitdata(self, value = None):
        model, init_params = self._init_fit()

        spectra = self.channel.spectra.y
        bkg = self.channel.spectra.bkg

        ydata = spectra[self.xrange] - bkg[self.xrange]
        result = self._fit(self.xdata, ydata, model, init_params)

        if result is not None:
            if result.success or not any(p.stderr is None for p in result.params.values()): pass
        else:
            messagebox.showerror('Error', "L'ajust ha fallat. Prova a introduir uns altres paràmetres inicials.")
            self.widgets['r2'].set('')
            return

        yfit = model(self.xdata, result.params)

        r2 = self._r2(ydata, yfit)
        self._draw_fit(yfit, result.params, r2)

    def get_config(self):
        config = FitConfig(name=self.widgets['name'].get())

        for peak in self.peaks.values():
            peak.name = peak.widgets['name'].get()
            peak.function = peak.widgets['function'].get()

            for parameter, data in peak.params.items():
                data['value'] = peak.widgets[f'{parameter}_value'].get()
                data['min'] = peak.widgets[f'{parameter}_min'].get()
                data['max'] = peak.widgets[f'{parameter}_max'].get()
                data['vary'] = peak.widgets[f'{parameter}_vary'].get()

            config.peaks[peak.name] = peak

        return config

    def config_to_parameters(config):
        params = Parameters()

        for i, peak in enumerate(config.peaks, 1):
            prefix = f'P{i}'

            for name in ('x0', 'FWHM', 'A'):
                p = getattr(peak, name)
                kwargs = {'value': p['value']}

                if p['min'] is not None: kwargs['min'] = p['min']
                if p['max'] is not None: kwargs['max'] = p['max']
                if p['vary'] is not None: kwargs['vary'] = p['vary']

                params.add(f'{prefix}_{name}', **kwargs)

        return params

    def _create_widgets(self):

        self.widgets = {
            'name': Widget(key='name', var_type=str, init=self.config.name,
                    text='Nom:', widget='entry', widget_kwargs = {'width': 10}),

            'r2': Widget(key='r2', var_type=float, init='',
                       text='R²', widget='entry', widget_kwargs = {'state': 'readonly', 'width': 10}),

            'add': Widget(key = 'add', var_type = str, init = 'Afegir pic',
                    widget = 'button', setter = self._add_peak),

            'remove': Widget(key='remove', var_type=str, init='Eliminar pic',
                            widget='button', setter=self._remove_peak),

            'fit': Widget(key = 'fit', var_type = str, init = 'Ajustar pic',
                          widget = 'button', setter = self._fitdata),

            'fitmap': Widget(key = 'fitmap', var_type = str, init = 'Ajustar mapa complet',
                             widget = 'button', setter = self._fitmap)}