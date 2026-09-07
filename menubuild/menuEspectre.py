import numpy as np
import threading
from pybaselines import Baseline
from tkinter import ttk, messagebox
from dataclasses import dataclass

from .base import BaseMenu
from window import BaseWindow
from window.widgets import Widget, Progress
from classes.fits import FitSpec
from process.mathfuncs import get_units, DEFAULT_PARAMS

class GestorEspectre(BaseMenu):  # Classe que gestiona les accions relacionades amb els perfils de fletxes.
    ordre = 200
    
    def __init__(self, app):
        super().__init__(app)  # Inicialitza la classe base

    def registrar_menu(self, menu):
        accions = [
            ('Calcular fons', lambda: Fons(self)),
            ('Fer ajust', lambda: FitSpec(self)),
            ('Operar amb paràmetres', lambda: ParamsOp(self)),
            ('Guardar espectre', self._guardar),
        ]
        
        self.create_menu("Espectre", menu, accions)  # Crida a la funció comuna d'afegir menú

    def _guardar(self): # Guarda els perfils dibuixats en fitxers de perfil.
        spec = self.current_file.view.spectrum

        folder = self.current_file.folder
        channel = self.current_file.current_channel
        posy, posx = channel.spectra.coords

        ruta = folder / 'Spectra'
        ruta.mkdir(parents=True, exist_ok=True)
        nom = ruta / f'{folder.stem}_{posx}_{posy}'

        header = '\t'.join([
            f'{"Xdata (" + channel.spectra.units + ")":>12}',
            f'{"I (a.u.)":>12}',
            f'{"Bkg (a.u.)":>12}'
        ])
        np.savetxt(f'{nom}.txt', np.c_[channel.spectra.x, channel.spectra.y, channel.spectra.bkg],
            header=header, delimiter='\t', fmt='%12.4f\t%12.2f\t%12.2f')

        spec.figure.savefig(f'{nom}.png', bbox_inches = 'tight')

class Fons(BaseWindow):
    def __init__(self, gestor):
        super().__init__(gestor, "Calcular fons")

        self.spec = self.file.view.spectrum
        self.bkg = np.full(self.spec.xdata.shape, np.nan)

    @property
    def xdata(self):
        return self.channel.spectra.x

    @property
    def ydata(self):
        return self.channel.spectra.y[self.xrange]

    @property
    def xrange(self):
        return self.channel.spectra.xrange

    @property
    def baseline(self):
        return Baseline(x_data=self.xdata[self.xrange])

    def plot_bkg(self, value):
        self.widgets["percentile"].config(state = 'disabled')
        self.widgets["spline"].config(state='disabled')
        self.bkg = np.full(self.xdata.shape, np.nan)
        bkg_value = np.full_like(self.xrange, np.nan)

        match value:
            case 'nan': pass
            case 'percentile':
                self.widgets["percentile"].config(state='normal')
                bkg_value = np.nanpercentile(self.ydata, self.widgets["percentile"].get())

            case 'spline':

                self.widgets["spline"].config(state='normal')
                bkg_value, _ = self.baseline.mixture_model(self.ydata, lam = 10 ** self.widgets["spline"].get())

        self.bkg[self.xrange] = bkg_value
        self.spec.bkgline.set_ydata(self.bkg)
        self.spec.canvas.draw_idle()

    def percentile(self, value):
        bkg_value = np.nanpercentile(self.ydata, value)

        self.bkg = np.full(self.xdata.shape, np.nan)
        self.bkg[self.xrange] = bkg_value

        self.spec.bkgline.set_ydata(self.bkg)
        self.spec.canvas.draw_idle()

        return

    def spline(self, value):
        bkg_value, _ = self.baseline.mixture_model(self.ydata, lam = 10 ** value)

        self.bkg = np.full(self.xdata.shape, np.nan)
        self.bkg[self.xrange] = bkg_value

        self.spec.bkgline.set_ydata(self.bkg)
        self.spec.canvas.draw_idle()

        return

    def apply_bkg(self, value):
        bkg_class = self.widgets["bkg"].get()
        if bkg_class == 'nan':
            self.channel.spectra.bkgdata = np.zeros_like(self.channel.spectra.ydata)
            return

        if self.widgets["map_bkg"].get() == 'one':
            N = self.file.geometry.N
            self.channel.spectra.bkgdata = np.tile(self.bkg, (N[1], N[0], 1))
        else:
            spec = self.channel.spectra.ydata
            total = spec.shape[0] * spec.shape[1]

            progress = Progress(self.window, title="Calculant fons", maximum=total)
            threading.Thread(target=self._calculate_bkg_thread, args=(bkg_class, progress), daemon=True).start()

    def _calculate_bkg_thread(self, value, progress):
        spec = self.channel.spectra.ydata
        mask = self.file.objects.mask
        bkg_class = value

        # Resultat temporal
        bkgdata = np.zeros_like(spec)

        current = 0

        for i in range(spec.shape[0]):
            for j in range(spec.shape[1]):
                if progress.cancelled():
                    progress.finish("Operació cancel·lada")
                    return

                current += 1
                progress.update(current, text=f"Calculant fons: {current}/{progress.maximum}")

                if not mask[i, j]: continue

                spectrum = spec[i, j, :][self.xrange]
                bkg = np.full(self.xdata.shape, np.nan)

                if bkg_class == 'percentile':
                    bkg_value = np.nanpercentile(spectrum, self.widgets["percentile"].get())

                elif bkg_class == 'spline':
                    bkg_value, _ = self.baseline.mixture_model(spectrum)

                bkg[self.xrange] = bkg_value
                bkgdata[i, j, :] = bkg

        self.channel.spectra.bkgdata = bkgdata
        progress.finish()

    def _create_widgets(self):
        opts = {"Cap": 'nan',
                "Percentil": "percentile",
                "Spline": "spline"}

        opts_bkg = {'Únic': 'one', 'Un per espectre': 'different'}

        self.widgets = {
            "bkg": Widget(key="bkg", var_type=str, init='nan',
                       text="Classe de fons:", widget="radiobutton", widget_kwargs={"options": opts},
                       setter=self.plot_bkg),

            "percentile": Widget(key="percentile", var_type=float, init=0,
                          text="Percentil (%):", widget="scale",
                          widget_kwargs = {'to': 100, 'resolution': 1, 'state': 'disabled'},
                          setter=self.percentile),

            "spline": Widget(key="spline", var_type=float, init=5,
                      text="Spline:", widget="scale",
                      widget_kwargs={"from": 3, "to": 7, "resolution": 1, "state": "disabled"},
                      setter = self.spline),

            "map_bkg": Widget(key="map_bkg", var_type=str, init='one',
                       text="Fons del mapa:", widget="radiobutton", widget_kwargs={"options": opts_bkg}),

            "apply": Widget(key="apply", var_type=str, init='Aplicar',
                       text = "Aplicar", widget = 'button',
                       setter = self.apply_bkg)
            }

@dataclass
class Operand:
    fit: str = ""
    peak: str = ""
    parameter: str = ""

    @property
    def label(self) -> str:
        if not self.peak or not self.parameter:
            return "Operand buit"
        return f"{self.peak}.{self.parameter}"

class ParamsOp(BaseWindow):
    def __init__(self, gestor):
        self.operands: list[dict] = []
        self.tokens: list[Operand | str] = []

        super().__init__(gestor, "Operar amb paràmetres")

        op_frame = ttk.Frame(self.control_frame)
        row = len(self.widgets)
        op_frame.grid(row = 0, column = 2, rowspan = 3)

        for i, op in enumerate(("+", "-", "*", "/", "(", ")")):
            self.widgets[op] = Widget(key = op, var_type = str, init = op,
                                      widget = 'button', widget_kwargs = {'width': 3},
                                      setter = self._add_operator)
            self.widgets[op].add(op_frame, row = i % 2, col = i // 2)

        self.widgets['expr'] = Widget(key = 'expr', var_type = str, init = '',
                               widget = 'entry',
                               widget_kwargs = {'width': 45, 'state': 'readonly'})
        self.widgets['expr'].add(self.control_frame, row = row + 1, col = 0, columnspan = 3)
        self.widgets['expr'].config(font = ('Helvetica', 12))

        self.widgets['add_par'] = Widget(key='add_par', var_type=str, init='Afegir paràmetre',
                                         widget='button',
                                         setter=self._operand_to_expression)
        self.widgets['add_par'].add(self.control_frame, row=row + 2, col = 0)

        self.widgets['delete'] = Widget(key = 'delete', var_type = str, init = 'Esborrar',
                                        widget = 'button', widget_kwargs = {'width': 12},
                                        setter = self._clear_expression)
        self.widgets['delete'].add(self.control_frame, row = row + 2, col = 1)

        self.widgets['calc'] = Widget(key = 'calc', var_type = str, init = 'Calcular',
                                      widget = 'button', widget_kwargs = {'width': 12},
                                      setter = self.calculate)
        self.widgets['calc'].add(self.control_frame, row = row + 2, col = 2)

    @property
    def fit(self):
        return self._fit

    @fit.setter
    def fit(self, value):
        spec = self.channel.spectra

        self._fit = spec.fits[value]
        self.fit_key = value

        # En canviar de fit, seleccionem el primer pic
        self._peak = next(iter(self.fit.peaks.values()))
        self.peak_key = self.peak.ref

        if self.parameter_key in self.peak.parameter_names: self._parameter = self.peak.get_parameter(self.parameter_key)
        else: self.parameter_key, self._parameter = next(iter(self.peak.params.items()))

        self.update_peaks()

    @property
    def peak(self):
        return self._peak

    @peak.setter
    def peak(self, value):
        self._peak = self.fit.peaks[value]
        self.peak_key = value

        # En canviar de pic, seleccionem el primer paràmetre

        if self.parameter_key in self.peak.parameter_names: self._parameter = self.peak.get_parameter(self.parameter_key)
        else: self.parameter_key, self._parameter = next(iter(self.peak.params.items()))

        self.widgets['parameter'].config(state='readonly')
        self.update_params()

    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, value):
        self._parameter = self.peak.get_parameter(value)
        self.parameter_key = value

        self.channel.Z = self._parameter
        self.channel.update_lims()

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

        refs = list(self.fit.peaks)
        peaks = [peak.name for peak in self.fit.peaks.values()]
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

        params = self.peak.parameter_names

        combo = self.widgets["parameter"].widget
        combo.config(values=params)
        combo.options = dict(zip(params, params))

        if self.parameter_key in params:
            combo.set(self.parameter_key)
            self.parameter = self.parameter_key
        else:
            combo.set(params[0])
            self.parameter = params[0]

    def _operand_to_expression(self, value):
        operand = Operand(fit=self.fit_key, peak=self.peak.name, parameter=self.parameter_key)
        self._add_operator(operand)

    def _add_operator(self, operand):
        self.tokens.append(operand)
        self._refresh_expression()

    def _refresh_expression(self):
        display = []
        for token in self.tokens:
            if isinstance(token, Operand):
                display.append(token.label)
            else:
                display.append(token)

        self.widgets['expr'].set(" ".join(display))

    def _clear_expression(self, value = None):
        if not self.tokens: return

        self.tokens.pop()
        self._refresh_expression()

    def calculate(self, value):
        if not self.tokens:
            messagebox.showwarning("Operació", "L'expressió està buida.")
            return

        try:
            self.channel.Z, dim = self.evaluate()

        except Exception as exc:
            messagebox.showerror("Error en l'operació", str(exc))
            return

        self.channel.units = get_units(dim, self.fit.units)
        self.channel.update_lims()
        self.file.view.map.refresh_map(self.channel)

    @staticmethod
    def _apply_operator(
        left: np.ndarray,
        operator: str,
        right: np.ndarray,
    ) -> np.ndarray:
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            if operator == "+":
                result = left + right
            elif operator == "-":
                result = left - right
            elif operator == "*":
                result = left * right
            elif operator == "/":
                result = left / right
            else:
                raise ValueError(f"Operador no vàlid: {operator}")

        # Convertim infinits i altres resultats no finits a NaN.
        result = np.asarray(result, dtype=float)
        result[~np.isfinite(result)] = np.nan
        return result

    def evaluate(self):
        if not self.tokens:
            raise ValueError("L'expressió està buida.")

        values = []

        for token in self.tokens:

            if isinstance(token, Operand):
                try:
                    fit = self.channel.spectra.fits[token.fit]
                    peak = next(
                        p for p in fit.peaks.values()
                        if p.name == token.peak
                    )
                except (KeyError, StopIteration):
                    raise ValueError(
                        f"No s'ha pogut trobar {token.peak} "
                        f"en l'ajust {token.fit}."
                    )

                data = peak.get_parameter(token.parameter)
                dim = DEFAULT_PARAMS[token.parameter]["dim"]

                values.append((data, dim))

            elif token in {"+", "-", "*", "/", "(", ")"}:
                values.append(token)

            else:
                raise ValueError(f"Token desconegut: {token}")

        # ------------------------------------------------------------------
        # Convertim la notació infixa a postfija (shunting-yard)
        # ------------------------------------------------------------------

        precedence = {
            "+": 1,
            "-": 1,
            "*": 2,
            "/": 2,
        }

        output = []
        operators = []

        for token in values:

            # Operand = (array, dim)
            if isinstance(token, tuple):
                output.append(token)

            elif token in {"+", "-", "*", "/"}:
                while (
                        operators
                        and operators[-1] in {"+", "-", "*", "/"}
                        and precedence[operators[-1]] >= precedence[token]
                ):
                    output.append(operators.pop())

                operators.append(token)

            elif token == "(":
                operators.append(token)

            elif token == ")":
                while operators and operators[-1] != "(":
                    output.append(operators.pop())

                if not operators:
                    raise ValueError("Parèntesis desequilibrats.")

                operators.pop()

        while operators:
            op = operators.pop()

            if op in {"(", ")"}:
                raise ValueError("Parèntesis desequilibrats.")

            output.append(op)

        # ------------------------------------------------------------------
        # Avaluació
        # ------------------------------------------------------------------

        stack = []

        for token in output:

            if isinstance(token, tuple):
                stack.append(token)
                continue

            if len(stack) < 2:
                raise ValueError("Expressió aritmètica incorrecta.")

            right_data, right_dim = stack.pop()
            left_data, left_dim = stack.pop()

            result = self._apply_operator(left_data, token, right_data)

            result_dim = self._combine_dimensions(left_dim, token, right_dim)
            stack.append((result, result_dim))

        if len(stack) != 1:
            raise ValueError("Expressió aritmètica incorrecta.")

        return stack[0]

    @staticmethod
    def _combine_dimensions(left: int, operator: str, right: int) -> int:
        if operator in {"+", "-"}:
            if left != right:
                raise ValueError(
                    f"No es poden combinar dimensions {left} i {right} "
                    f"amb '{operator}'."
                )
            return left

        if operator == "*":
            return left + right

        if operator == "/":
            return left - right

        raise ValueError(f"Operador no vàlid: {operator}")

    def _create_widgets(self):
        opts_fits = list(self.channel.spectra.fits)
        self.fit_key = opts_fits[0]
        self._fit = self.channel.spectra.fits[self.fit_key]

        refs_peaks = [peak.name for peak in self.fit.peaks.values()]
        names_peaks = list(self.fit.peaks)
        opts_peaks = dict(zip(refs_peaks, names_peaks))

        self.peak_key = names_peaks[0]
        self._peak = self.fit.peaks[self.peak_key]

        opts_params = self.peak.parameter_names
        self.parameter_key = opts_params[0]
        self._parameter = self.peak.params[self.parameter_key]

        self.widgets = {
            'fit': Widget(key='fit', var_type=str, init=self.fit,
                          text='Ajusts:', widget='cb', widget_kwargs={'options': opts_fits, 'width': 8},
                          setter=self, mode='attr'),

            'peak': Widget(key='peak', var_type=str, init=self.peak,
                           text='Pic:', widget='cb', widget_kwargs={'options': opts_peaks, 'width': 8},
                           setter=self, mode='attr'),

            'parameter': Widget(key='parameter', var_type=str, init=self.parameter,
                                text='Paràmetre:', widget='cb', widget_kwargs={'options': opts_params, 'width': 8},
                                setter=self, mode='attr')
            }