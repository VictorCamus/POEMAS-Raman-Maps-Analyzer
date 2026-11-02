"""Finestra que controla l'ajust d'espectres."""

import threading
from copy import deepcopy
from dataclasses import replace
from functools import partial
from tkinter import messagebox
from tkinter.ttk import Frame, Label
from typing import TYPE_CHECKING, Literal, TypedDict, cast

import numpy as np
from lmfit import Parameters, minimize
from matplotlib.colors import TABLEAU_COLORS

from classes.data import FitData, PeakData, PeakDataConfig
from classes.views import PeakView
from drawing.plots import get_verts
from process.basics import find_nearest
from process.mathfuncs import DEFAULT_FUNCS, linear_combination
from process.statistics import get_r2
from window.builder import BaseWindow
from window.widgets import Progress, Widget

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

    from classes.protocols import GestorProtocol, MinimizerProtocol, ParametersProtocol
    from process.mathfuncs import DefaultParameter


COLORS = cast("list[str]", list(TABLEAU_COLORS.values()))


type FitSpecKey = Literal["name", "add", "fit", "r2", "remove", "fit_map"]


class FitSpecWidgets(TypedDict):
    """Ginys de la finestra d'ajust."""

    name: Widget[str]
    add: Widget[str]
    fit: Widget[str]
    r2: Widget[float]
    remove: Widget[str]
    fit_map: Widget[str]


class PeakSpecWidgets(TypedDict):
    """Ginys de la classe PeakSpec."""

    name: Widget[str]
    function: Widget[str]
    unique: Widget[bool]


class ParSpecWidgets(TypedDict):
    """Ginys dels paràmetres."""

    value: Widget[float]
    min: Widget[float]
    max: Widget[float]
    vary: Widget[bool]


class PeakSpec(PeakDataConfig):
    """Controla la creació dels requadres destinats a l'operació amb pics de l'ajust."""

    widgets: PeakSpecWidgets

    def __init__(self, config: PeakDataConfig, frame: Frame,
                update_label: Callable[[str, str, float], None],
                update_func_plot: Callable[[str, bool, bool], None],
                refresh_plot: Callable[[], None]) -> None:
        """Crea un nou requadre per a un pic o fons de la funció.

        config: PeakDataConfig:
            Configuració del pic
        frame: Frame
            Nou requadre dins de la finestra principal
        update_label: Callable[[str, str, float], None]
            Funció que s'activa quan es canvia el nom del pic
        update_func_plot: Callable[[str, bool, bool], None]
            Funció que s'activa quan es canvia la funció del pic
        refresh_plot: Callable[[], None]
            Actualització genèrica de la gràfica

        """
        super().__init__(**vars(config))

        self.frame = frame
        self.update_label = update_label
        self.update_func_plot = update_func_plot
        self.refresh_plot = refresh_plot

        self.par_widgets: dict[str, ParSpecWidgets] = {}

        self._create_widgets()
        self._create_parameters()

    def _create_widgets(self) -> None:
        self.widgets: PeakSpecWidgets = {
            "name": Widget(
                key="name",
                var_type=str,
                init=self.name,
                widget="entry",
                widget_kwargs={"width": 8},
                setter=self,
                mode="attr",
            ),
            "function": Widget(
                key="function",
                var_type=str,
                init=self.function,
                widget="cb",
                widget_kwargs={"options": DEFAULT_FUNCS.keys(), "width": 10},
                setter=self.update_func,
            ),
            "unique": Widget(
                key="unique",
                var_type=bool,
                init=self.unique,
                text="Resoluble:",
                widget="checkbutton",
                setter=self,
                mode="attr",
            ),
        }

        self.widgets["name"].add(self.frame, row=0, col=0)
        self.widgets["function"].add(self.frame, row=0, col=1)
        self.widgets["unique"].add(self.frame, row=0, col=2, columnspan=2)

        if self.func.is_bkg:
            self.widgets["unique"].config(state="disabled")

        # Capçalera dels paràmetres
        Label(self.frame, text="Value").grid(row=1, column=1)
        Label(self.frame, text="Min").grid(row=1, column=2)
        Label(self.frame, text="Max").grid(row=1, column=3)
        Label(self.frame, text="Vary").grid(row=1, column=4)

    def add_parameter(self, parameter: DefaultParameter, name: str, row: int) -> None:
        """Afig un paràmetre al requadre.

        Parameters
        ----------
        parameter: DefaultParameter
            Valors inicials del paràmetre
        name: str
            Nom del paràmetre
        row: int
            Fila que ocupa en el requadre

        """
        self.par_widgets[name] = {
            "value": Widget(
                key="value",
                var_type=float,
                init=parameter.value,
                text=f"{name}:",
                widget="entry",
                widget_kwargs={"width": 10},
                setter=partial(self.update_value, par=self.params[name]),
                ),
            "min": Widget(
                key="min",
                var_type=float,
                init=parameter.min,
                widget="entry",
                widget_kwargs={"width": 8},
                setter=parameter,
                mode="attr",
            ),
            "max": Widget(
                key="max",
                var_type=float,
                init=parameter.max,
                widget="entry",
                widget_kwargs={"width": 8},
                setter=parameter,
                mode="attr",
            ),
            "vary": Widget(
                key="vary",
                var_type=bool,
                init=parameter.vary,
                widget="checkbutton",
                setter=parameter,
                mode="attr")}

        par = self.par_widgets[name]
        par["value"].add(self.frame, row=row, col=0)
        par["min"].add(self.frame, row=row, col=2)
        par["max"].add(self.frame, row=row, col=3)
        par["vary"].add(self.frame, row=row, col=4)

    def _create_parameters(self) -> None:
        """Crea els ginys dels paràmetres de la funció triada."""
        for row, name in enumerate(self.func.params, start=2):
            self.add_parameter(self.params[name], name, row)

    def _clear_parameters(self) -> None:
        """Destrueix els ginys dels paràmetres actuals.

        Raises
        ------
        TypeError
            Si cap giny triat no és del tipus Widget.

        """
        for widgets in self.par_widgets.values():
            for widget in widgets.values():
                if not isinstance(widget, Widget):
                    msg = "El giny triat no és un objecte Widget."
                    raise TypeError(msg)

                if widget.label is not None:
                    widget.label.destroy()

                widget.widget.destroy()

        self.par_widgets.clear()

    def _rebuild_parameters(self) -> None:
        """Reconstrueix els paràmetres de la nova funció seleccionada."""
        self._clear_parameters()

        if self.func.is_bkg:
            self.unique = False
            self.widgets["unique"].set(False)
            self.widgets["unique"].config(state="disabled")
        else:
            self.widgets["unique"].config(state="normal")

        self._create_parameters()

    def update_name(self, name: str) -> None:
        """Actualitza el nom del pic i l'etiqueta sobre el gràfic, si no és fons.

        Parameters
        ----------
        name: str
            Nom del pic

        """
        self.name = name
        if not self.func.is_bkg:
            self.update_label(self.ref, name, self.params["x0"].value)

    def update_func(self, func: str) -> None:
        """Actualitza la funció i conserva els paràmetres que siguen compatibles.

        Parameters
        ----------
        func: str
            Funció triada

        """
        old_bkg = self.func.is_bkg
        self.update_function(func)

        self._rebuild_parameters()
        self.update_func_plot(self.ref, old_bkg, self.func.is_bkg)

    def update_value(self, value: float, par: DefaultParameter) -> None:
        """Actualitza el valor del paràmetre i la gràfica.

        Parameters
        ----------
        value: float
            Nou valor del paràmetre
        par: DefaultParameter
            Classe del paràmetre

        """
        par.value = value
        self.refresh_plot()


class FitSpec(BaseWindow):
    """Finestra que permet ajustar els espectres a una funció formada per pics i fons."""

    widgets: FitSpecWidgets

    def __init__(self, gestor: GestorProtocol) -> None:
        """Crea la finestra de treball amb l'ajust actual, si existeix.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        self.spectra = gestor.current_file.current_channel.spec
        self.specview = gestor.current_file.specview
        self.dim = gestor.current_file.geometry.dim
        self.mask = gestor.current_file.objects.mask

        super().__init__(gestor, "Ajust espectral")

        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        self.main_frame.pack_configure(fill="none", expand=False)
        self.control_frame.pack_configure(side="top", anchor="w")
        self.peaks: dict[str, PeakSpec] = {}

        self.specview.fit_line.set_data(self.xdata, np.full_like(self.xdata, 0))

        self.fit_frame = Frame(self.main_frame)
        self.fit_frame.pack(side="bottom", fill="both", expand=True, pady=2)

        if self.specview.header.fit_key != "rawdata":
            self.widgets["name"].set(self.specview.header.fit_key)

            for config in deepcopy(self.specview.header.fit.config).values():
                self.add_peak(config=config, new=False)

        layout: list[tuple[int, int, FitSpecKey]] = [
            (0, 1, "name"),
            (0, 3, "add"),
            (0, 4, "fit"),
            (1, 1, "r2"),
            (1, 3, "remove"),
            (1, 4, "fit_map"),
        ]

        for row, col, key in layout:
            widget = self.widgets[key]
            widget.widget.grid_configure(row=row, column=col)

            if widget.label is not None:
                widget.label.grid_configure(row=row, column=col - 1)

    @property
    def xdata(self) -> NDArray[np.float32]:
        """Retorna les dades de l'eix X dins del rang triat."""
        return self.spectra.x[self.xrange]

    @property
    def ydata(self) -> NDArray[np.float32]:
        """Retorna les dades de l'eix Y dins del rang triat."""
        return self.spectra.y[self.xrange]

    @property
    def bkg(self) -> NDArray[np.float32]:
        """Retorna les dades del fons si està actiu. Si no, retorna un vector nul."""
        bkg = np.zeros_like(self.ydata, dtype=np.float32)

        if self.spectra.bkg_active:
            bkg = self.spectra.bkg[self.xrange].copy()\
                if self.specview.header.fit_key == "rawdata"\
                else self.specview.header.fit.bkg(self.spectra.coords, len(self.spectra.y))[self.xrange].copy()

            for peak in self.peaks.values():
                if peak.func.is_bkg:
                    bkg += peak.ydata(self.xdata)

        return bkg

    @property
    def xrange(self) -> slice[int, int, int]:
        """Retorna el rang de dades triat."""
        return self.spectra.xrange

    def _create_widgets(self) -> None:
        name = f"Fit{len(self.spectra.fits) + 1}"

        self.widgets = {
            "name": Widget(
                key="name",
                var_type=str,
                init=name,
                text="Nom:",
                widget="entry",
                widget_kwargs={"width": 10},
            ),
            "add": Widget(
                key="add",
                init="Afegir pic",
                widget="button",
                widget_kwargs={"width": 12},
                setter=self.add_peak,
            ),
            "fit": Widget(
                key="fit",
                init="Ajustar pic",
                widget="button",
                widget_kwargs={"width": 12},
                setter=self.fit_data,
            ),
            "r2": Widget(
                key="r2",
                var_type=float,
                text="R²",
                widget="entry",
                widget_kwargs={"state": "readonly", "width": 10},
            ),
            "remove": Widget(
                key="remove",
                init="Eliminar pic",
                widget="button",
                widget_kwargs={"width": 12},
                setter=self.remove_peak,
            ),
            "fit_map": Widget(
                key="fit_map",
                init="Ajustar mapa complet",
                widget="button",
                widget_kwargs={"width": 12},
                setter=self.fit_map,
            ),
        }

    def close_window(self) -> None:
        """Elimina els objectes relacionats amb l'ajust del gràfic d'espectres."""
        for peak_plot in self.specview.fit_peaks.values():
            peak_plot.remove()

        self.specview.fit_line.set_data([], [])

        self.specview.canvas.draw_idle()
        self.window.destroy()

    def add_peak(self, config: PeakDataConfig | None = None, *, new: bool = True) -> None:
        """Afig un nou requadre que conté les dades del pic donat. Si no, crea un nou pic.

        Parameters
        ----------
        config: PeakDataConfig | None = None
            Dades de la configuració de l'ajust actual, si existeix.
        new: bool = True
            True: Nou pic. False: Pic ja existent a l'ajust.

        """
        i = len(self.peaks)

        if config is None:
            config = PeakDataConfig(ref=f"P{i + 1}", name=f"P{i + 1}")

        row = i % 3
        col = i // 3

        frame = Frame(self.fit_frame)
        frame.grid(row=row, column=col, padx=5, pady=5, sticky="nw")

        peak = PeakSpec(
            config=config,
            frame=frame,
            update_label=self.update_label,
            update_func_plot=lambda ref, old_bkg, new_bkg: self.update_func_plot(ref, old_bkg=old_bkg, new_bkg=new_bkg),
            refresh_plot=self.refresh_plot)
        self.peaks[config.ref] = peak

        if new:
            self.specview.fit_peaks[config.ref] = PeakView(self.specview.axis, color=COLORS[i])
            self.set_peak_plot(peak)
            self.update_fit()

    def remove_peak(self) -> None:
        """Elimina el pic triat i els objectes associats."""
        if not self.peaks:
            return

        _, peak = self.peaks.popitem()
        peak.frame.destroy()

        if peak.func.is_bkg:
            self.refresh_plot()
        else:
            _, peak_plot = self.specview.fit_peaks.popitem()
            peak_plot.remove()
            self.update_fit()

        self.specview.canvas.draw_idle()

    def get_label_coords(self, params: dict[str, DefaultParameter]) -> tuple[float, float]:
        """Obté les coordenades de l'etiqueta del segons els paràmetres del pic donat.

        Parameters
        ----------
        params: dict[str, DefaultParameter]
            Diccionari de paràmetres del pic

        Returns
        -------
        x0, y0: tuple[float, float]
            Coordenades de l'etiqueta en la gràfica.

        """
        x0 = params["x0"].value
        idx = find_nearest(self.xdata, x0)
        amp = params["amp"].value

        y0 = amp + float(self.bkg[idx])

        return x0, y0

    def set_peak_plot(self, peak: PeakSpec) -> None:
        """Actualitza els vèrtexs de l'àrea acolorida d'un pic.

        Parameters
        ----------
        peak: PeakSpec
            Dades del pic

        """
        ydata = np.asarray(peak.ydata(self.xdata), dtype=np.float32)

        self.specview.fit_peaks[peak.ref].update(
            verts=get_verts(self.xdata, ydata, self.bkg),
            label_text=peak.name,
            label_coords=self.get_label_coords(peak.params))

    def update_label(self, ref: str, name: str, value: float) -> None:
        """Actualitza l'etiqueta del pic cada vegada que es canvia de nom.

        Parameters
        ----------
        ref: str
            Referència del pic
        name: str
            Nom del pic
        value: float
            Valor del centre del pic

        """
        self.specview.fit_peaks[ref].update_text(name, value)

    def update_func_plot(self, ref: str, *, old_bkg: bool, new_bkg: bool) -> None:
        """Actualitza la gràfica quan un pic canvia de tipus.

        Parameters
        ----------
        ref: str
            Referència del pic
        old_bkg: bool
            True: Fons (Abans de canviar de funció). False: Pic (Abans de canviar de funció)
        new_bkg: bool
            True: Fons (Després de canviar de funció). False: Pic (Després de canviar de funció)

        """
        if new_bkg != old_bkg:
            if new_bkg:
                peak_plot = self.specview.fit_peaks.pop(ref)
                peak_plot.remove()
            else:
                self.specview.fit_peaks[ref] = PeakView(self.specview.axis, color=COLORS[len(self.peaks)])

        self.refresh_plot()

    def update_bkg(self) -> None:
        """Actualitza el fons de la gràfica."""
        background = np.zeros_like(self.spectra.y, dtype=np.float32)
        background[self.xrange] = self.bkg
        self.specview.bkg_line.set_ydata(background)

    def update_fit(self) -> None:
        """Actualitza les dades de la línia d'ajust."""
        ydata = np.full(self.xdata.shape, 0, dtype=np.float32)

        for peak in self.peaks.values():
            ydata += peak.ydata(self.xdata)

        self.specview.fit_line.set_data(self.xdata, ydata)
        self.specview.canvas.draw_idle()

    def refresh_plot(self) -> None:
        """Refresca el fons, les àrees dels pics i la suma de l'ajust."""
        self.update_bkg()

        for peak in self.peaks.values():
            if peak.func.is_bkg:
                continue

            self.set_peak_plot(peak)

        self.update_fit()
        self.specview.canvas.draw_idle()

    def fit_data(self) -> None:
        """Ajusta l'espectre actual i actualitza els paràmetres dels pics.

        Raises
        ------
        RuntimeError
            Si l'ajust ha fallat

        """
        model, init_params = self.fit_init(self.peaks)
        spec = self.spectra
        fit = self.specview.header.fit_key

        bkg = spec.bkg if fit == "rawdata" else spec.fits[fit].bkg(spec.coords, len(spec.y)).copy()

        ydata = self.ydata - bkg[self.xrange]
        params = self.fit(self.xdata, ydata, model, init_params)

        if params is None:
            self.widgets["r2"].set(None)

            msg = "L'ajust ha fallat. Prova a introduir uns altres paràmetres inicials."
            messagebox.showerror("Error", msg)
            raise RuntimeError(msg)

        yfit = model(self.xdata, params)
        r2 = get_r2(ydata, yfit)

        for ref, peak in self.peaks.items():
            for par_name, par in peak.params.items():
                par.value = round(params[f"{ref}_{par_name}"].value, 3)
                peak.par_widgets[par_name]["value"].set(par.value)

        self.widgets["r2"].set(round(r2, 4))
        self.refresh_plot()

    def fit_map(self) -> None:
        """Inicia l'ajust dels espectres de tots els píxels del mapa."""
        total = self.dim[0] * self.dim[1]
        fit_name = self.widgets["name"].get()

        progress = Progress(self.window, title="Ajustant mapa", maximum=total)
        threading.Thread(target=self._fit_map_thread, args=(fit_name, progress), daemon=True).start()

    def _fit_map_thread(self, fit_name: str, progress: Progress) -> None:
        """Crea i calcula el resultat de l'ajust del mapa d'espectres.

        Parameters
        ----------
        fit_name: str
            Nom de l'ajust
        progress: Progress
            Classe que conté la barra de progrés

        Raises
        ------
        ValueError
            Si pics marcats com a resolubles tenen límits del centre (x0) infinits

        """
        model, init_params = self.fit_init(self.peaks)
        params = init_params.copy()
        peakrange = self._create_peak_ranges(params)

        if peakrange is None:
            msg = "Els pics marcats com a resolubles no poden tindre els límits del centre (x0) infinits."
            messagebox.showerror("Error en l'ajust", msg)
            progress.finish()
            raise ValueError(msg)

        fit_result = self._obtain_fit_data(init_params, model, peakrange, progress)

        if fit_result is None:
            return

        self.spectra.fits[fit_name] = fit_result
        self.window.after(0, self._fit_map_finish, fit_name, progress)

    def _create_fit_result(self) -> FitData:
        """Crea l'objecte que conté les dades de l'ajust.

        Returns
        -------
        fit_result: FitData
            Classe de l'ajust

        """
        fit = self.specview.header.fit_key
        bkgdata = self.spectra.bkgdata if fit == "rawdata" else self.spectra.fits[fit].bkgdata

        peaks: dict[str, PeakData] = {}

        for peak in self.peaks.values():
            peaks[peak.ref] = PeakData(
                ref=peak.ref,
                name=peak.name,
                function=peak.function,
                is_bkg=peak.func.is_bkg)

            for par in peak.params:
                peaks[peak.ref].params[par] = np.full(self.spectra.ydata.shape[:2], np.nan, dtype=float)

        r2_value = np.full(self.spectra.ydata.shape[:2], np.nan, dtype=float)

        config = {peak.ref: PeakDataConfig(
            ref=peak.ref,
            name=peak.name,
            function=peak.function,
            unique=peak.unique,
            params={key: replace(param) for key, param in peak.params.items()})
            for peak in self.peaks.values()}

        return FitData(
            name=self.widgets["name"].get(),
            units=self.spectra.units,
            r2=r2_value,
            xrange=self.xrange,
            config=config,
            bkgdata=bkgdata,
            peaks=peaks)

    def _create_peak_ranges(self, init_params: ParametersProtocol)\
                             -> dict[str, slice[int, int, int]] | None:
        """Valida els pics resolubles i determina els seus rangs dins de l'espectre.

        Parameters
        ----------
        init_params: ParametersProtocol
            Paràmetres inicials

        Returns
        -------
        peak_ranges: dict[str, slice] | None
            Rang dels pics resolubles. Retorna None si cap límit és infinit

        """
        peak_ranges: dict[str, slice[int, int, int]] = {}

        for key, peak in self.peaks.items():
            if peak.func.is_bkg or not peak.unique:
                continue

            x0 = peak.params["x0"]

            if np.isinf(x0.min) or np.isinf(x0.max):
                return None

            left, right = sorted(find_nearest(self.xdata, [init_params[f"{key}_x0"].min, init_params[f"{key}_x0"].max]))

            peak_ranges[key] = slice(left, right)

        return peak_ranges

    def _init_unique_peaks(self, params: ParametersProtocol, peakrange: dict[str, slice[int, int, int]],
                            ydata: NDArray[np.float32], bkg: float) -> None:
        """Assigna els paràmetres inicials als pics resolubles.

        Parameters
        ----------
        params: ParametersProtocol
            Paràmetres actuals
        peakrange: dict[str, slice[int, int ,int]]
            Rang dels pics resolubles
        ydata: NDArray[np.float32]
            Dades de l'espectre corresponent
        bkg: float
            Correcció de fons per a l'amplitud

        """
        for key, p_range in peakrange.items():
            imax = np.argmax(ydata[p_range])

            amp = float(ydata[p_range][imax]) - bkg
            x0 = float(self.xdata[p_range][imax])

            params[f"{key}_amp"].value = amp
            params[f"{key}_x0"].value = x0

    def _obtain_fit_data(self,
        init_params: ParametersProtocol,
        model: Callable[[NDArray[np.float32], ParametersProtocol], NDArray[np.float32]],
        peakrange: dict[str, slice[int, int, int]],
        progress: Progress) -> FitData | None:
        """Calcula les dades de l'ajust per al mapa d'espectres.

        Parameters
        ----------
        init_params: ParametersProtocol
            Paràmetres inicials
        model: Callable[[NDArray[np.float32], ParametersProtocol], NDArray[np.float32]]
            Funció a què s'ajusten les dades
        peakrange: dict[str, slice[int, int, int]]
            Diccionari que conté el rang dels pics resolubles
        progress: Progress
            Objecte que conté la barra de progrés

        Returns
        -------
        fit_result: FitData | None
            Classe amb els resultats de l'ajust. Si es cancel·la el procés a meitat, retorna None

        """
        fit_result = self._create_fit_result()
        spectra = self.spectra.ydata

        params = init_params.copy()

        for i in range(spectra.shape[0]):
            for j in range(spectra.shape[1]):
                # Comprovar cancel·lació
                if progress.cancelled():
                    progress.finish("Operació cancel·lada")
                    return None

                progress.increment()

                if not self.mask[i, j]:
                    continue

                if fit_result.bkgdata is None:
                    ydata = spectra[i, j][self.xrange]
                    bkg_setpoint = np.nanpercentile(ydata, 5)
                else:
                    ydata = spectra[i, j][self.xrange] - fit_result.bkgdata[i, j][self.xrange]
                    bkg_setpoint = 0

                self._init_unique_peaks(params, peakrange, ydata, bkg_setpoint)
                fit_params = self.fit(self.xdata, ydata, model, params)

                if fit_params is None:
                    params = init_params.copy()
                    continue

                yfit = model(self.xdata, fit_params)
                r2 = get_r2(ydata, yfit)

                if r2 < 0.5:
                    params = init_params.copy()
                    continue

                params = fit_params

                for name, peak in self.peaks.items():
                    for par_name in peak.params:
                        fit_result.peaks[peak.ref].params[par_name][i, j] = params[f"{name}_{par_name}"].value

                fit_result.r2[i, j] = r2

        return fit_result

    def _fit_map_finish(self, name: str, progress: Progress) -> None:
        """Selecciona el nou ajust per a mostrar-lo en pantalla i tanca la finestra de progrés.

        Parameters
        ----------
        name: str
            Nom de l'ajust
        progress: Progress
            Objecte que conté la barra de congrés

        """
        combofit = self.specview.header.widgets["fit"]

        combofit.options[name] = name
        combofit.config(values=list(combofit.options.keys()))

        self.specview.header.fit = name
        progress.finish()

    @staticmethod
    def fit_init(peaks: dict[str, PeakSpec]) ->\
                 tuple[Callable[[NDArray[np.float32], ParametersProtocol], NDArray[np.float32]],
                           ParametersProtocol]:
        """Inicia la funció model i el paràmetres amb què es faran l'ajust.

        Parameters
        ----------
        peaks: dict[str, PeakSpec]
            Diccionari amb els pics creats.

        Returns
        -------
        model: tuple[Callable[[NDArray[np.float32], ParametersProtocol], NDArray[np.float32]]
            Funció model formada a partir de la combinació lineal de les funcions de cada pic
        params: ParametersProtocol
            Paràmetres lmfit per a fer la funció

        """
        funcs = {ref: peak.func for ref, peak in peaks.items()}

        model = linear_combination(funcs)

        params = Parameters()
        for ref, peak in peaks.items():
            for par_name, par in peak.params.items():
                params.add(
                    f"{ref}_{par_name}",
                    value=par.value,
                    min=par.min,
                    max=par.max,
                    vary=par.vary,
                )

        return model, cast("ParametersProtocol", params)

    @staticmethod
    def fit(x: NDArray[np.float32], y: NDArray[np.float32],
            model: Callable[[NDArray[np.float32], ParametersProtocol], NDArray[np.float32]],
            params: ParametersProtocol) -> ParametersProtocol | None:
        """Ajusta les dades al model dins del rang seleccionat.

        Parameters
        ----------
        x: NDArray[np.float32]
            Rang sobre el que s'avalua l'ajust
        y: NDArray[np.float32]
            Conjunt de dades que s'ajusta
        model: Callable[[NDArray[np.float32], ParametersProtocol], NDArray[np.float32]]
            Funció sobre la que s'ajusten les dades
        params: ParametersProtocols
            Paràmetres de la funció que s'optimitzen

        Returns
        -------
        params: ParametersProtocol | None
            Paràmetres obtinguts de l'ajust. Si l'ajust no és satisfactori, retorna None

        """
        def residual(params: ParametersProtocol) -> NDArray[np.float32]:
            return model(x, params) - y

        result = cast("MinimizerProtocol", minimize(residual, params, method="least_squares", diff_step=1e-4))

        if not result.success or any(p.stderr is None for p in result.params.values()):
            return None

        return result.params
