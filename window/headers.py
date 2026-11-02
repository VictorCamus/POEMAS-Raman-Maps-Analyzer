"""Classes que controlen i creen les capçaleres d'un visor de mapes, espectres..."""

from abc import ABC, abstractmethod
from functools import partial
from tkinter import messagebox
from tkinter.ttk import Frame
from typing import TYPE_CHECKING, Literal, TypedDict

import numpy as np

from drawing.colormap import cmaps
from process.converter import get_units
from process.mathfuncs import DEFAULT_PARAMS
from window import Widget
from window.mixin import SpecMixin, SpecWidgets

if TYPE_CHECKING:
    from classes.data import ChannelData, SpecData
    from classes.protocols import ColorBool, InfSup, SpecUnits
    from classes.views import FigureView, MapView, SpecView


type MapWidgetKey = Literal["cmap_c", "cmap_r", "lim_sup", "lim_inf",
                            "cscale", "col_sup", "col_inf"]

type SpecWidgetKey = Literal["units", "left", "right", "data", "log", "fit",
    "bottom", "top", "bkg", "etiq", "peak",
    "parameter", "del_fit", "CCD"]


class HeaderMapWidgets(TypedDict):
    """Classe TypedDict que determina les anotacions dels ginys de HeaderMap."""

    cmap_c: Widget[str]
    cmap_r: Widget[bool]
    lim_sup: Widget[float]
    lim_inf: Widget[float]
    cscale: Widget[ColorBool]
    col_sup: Widget[ColorBool]
    col_inf: Widget[ColorBool]


class Header[TView: FigureView](Frame, ABC):
    """Classe base general d'una capçalera."""

    def __init__(self, view: TView) -> None:
        """Crea els ginys de la capçalera."""
        super().__init__(view.file.content)
        self.view = view

        self._create_widgets()

    @property
    def channel(self) -> ChannelData:
        """Retorna el canal actual mostrat al visor de mapes.

        Returns
        -------
        channel: ChannelData
            Canal actual

        """
        return self.view.channel

    @abstractmethod
    def _create_widgets(self) -> None:
        """Crea els ginys i els col·loca dins de la capçalera."""


class HeaderMap(Header["MapView"]):
    """Controla la capçalera dels mapes."""

    def _create_widgets(self) -> None:
        self.widgets: HeaderMapWidgets = {
            "cmap_c": Widget(
                key="cmap_c",
                var_type=str,
                init=self.channel.name,
                text="Color mapa:",
                widget="cb",
                widget_kwargs={"options": cmaps, "width": "10"},
                setter=self._change_cmap_c,
            ),
            "cmap_r": Widget(
                key="cmap_r",
                var_type=bool,
                init=False,
                widget="radiobutton",
                widget_kwargs={"options": {"N": False, "R": True}, "direction": "h"},
                setter=lambda value: self._change_cmap_r(cmap_r=value),
            ),
            "lim_sup": Widget(
                key="lim_sup",
                var_type=float,
                init=self.channel.lims[1],
                text="Valor màxim:",
                widget="entry",
                widget_kwargs={"width": 10},
                setter=partial(self._change_lims, key="sup"),
            ),
            "lim_inf": Widget(
                key="lim_inf",
                var_type=float,
                init=self.channel.lims[0],
                text="Valor mínim:",
                widget="entry",
                widget_kwargs={"width": 10},
                setter=partial(self._change_lims, key="inf"),
            ),
            "cscale": Widget(
                key="cscale",
                var_type=str,
                init="w",
                text="Color escala:",
                widget="radiobutton",
                widget_kwargs={"options": {"B": "w", "N": "k"}, "direction": "h"},
                setter=self._change_scale,
            ),
            "col_sup": Widget(
                key="col_sup",
                var_type=str,
                init=self.channel.color.lim_sup,
                widget="radiobutton",
                widget_kwargs={"options": {"B": "w", "N": "k"}, "direction": "h"},
                setter=partial(self._change_col_lims, key="sup"),
            ),
            "col_inf": Widget(
                key="col_inf",
                var_type=str,
                init=self.channel.color.lim_inf,
                widget="radiobutton",
                widget_kwargs={"options": {"B": "w", "N": "k"}, "direction": "h"},
                setter=partial(self._change_col_lims, key="inf"),
            ),
        }

        layout: list[tuple[int, int, MapWidgetKey]] = [
        (0, 1, "cmap_c"), (0, 3, "cmap_r"), (0, 4, "lim_sup"), (0, 6, "col_sup"),
        (1, 1, "cscale"), (1, 4, "lim_inf"), (1, 6, "col_inf")]

        for row, col, key in layout:
            self.widgets[key].add(self, row, col)

    def set_channel(self, ch: ChannelData) -> None:
        """Actualitza els ginys de la capçalera i redibuixa el mapa amb les dades del nou canal.

        Parameters
        ----------
        ch: ChannelData
            Canal actualitzat

        """
        self.widgets["cmap_c"].set(ch.color.cmap_c)
        self.widgets["cmap_r"].set(ch.color.cmap_r)

        # ---- 2. Actualitzar els combobox dels colors de l'escala ----
        self.widgets["cscale"].set(ch.color.scale)
        self.widgets["col_sup"].set(ch.color.lim_sup)
        self.widgets["col_inf"].set(ch.color.lim_inf)

        # ---- 3. Actualitzar els camps d'entrada dels límits ----
        self.widgets["lim_inf"].set(ch.lims[0])
        self.widgets["lim_sup"].set(ch.lims[1])

        label = self.view.footer.widgets["track_z"].label
        if label is not None:
            label.config(text=f"{ch.name} ({ch.units})")

        self.view.redraw(cmap=True, lims=True)

    def _change_cmap_c(self, cmap_c: str) -> None:
        """Canvia el color del mapa.

        cmap_c: str
            Nom del color del mapa.

        """
        self.channel.color.cmap_c = cmap_c
        self.view.redraw(cmap=True)

    def _change_cmap_r(self, *, cmap_r: bool) -> None:
        """Reverteix el gradient del color del mapa.

        Parameters
        ----------
        cmap_r: bool
            True si està invertit, False si és normal.

        """
        ch = self.channel
        if ch.color.cmap_r != cmap_r and ch.color.lim_sup != ch.color.lim_inf:
            ch.color.lim_inf, ch.color.lim_sup = ch.color.lim_sup, ch.color.lim_inf
            self.widgets["col_inf"].set(ch.color.lim_inf)
            self.widgets["col_sup"].set(ch.color.lim_sup)

        ch.color.cmap_r = cmap_r
        self.view.redraw(cmap=True)

    def _change_lims(self, value: float, key: InfSup) -> None:
        """Canvia els límits del mapa de colors.

        Parameters
        ----------
        value: float
            Nou valor del límit
        key: InfSup
            Clau que indica sobre quin límit s'aplica

        Raises
        ------
        ValueError
            Si en cap moment el límit superior no és major de l'inferior


        """
        match key:
            case "inf":
                if value >= self.channel.lims[1]:
                    msg = "El límit inferior ha de ser menor que el superior."
                    messagebox.showerror("Error en actualitzar la gràfica")
                    raise ValueError(msg)

                self.channel.lims[0] = value
            case "sup":
                if value <= self.channel.lims[0]:
                    msg = "El límit inferior ha de ser menor que el superior."
                    messagebox.showerror("Error en actualitzar la gràfica")
                    raise ValueError(msg)
                self.channel.lims[1] = value

        self.view.redraw(lims=True)

    def _change_col_lims(self, value: ColorBool, key: InfSup) -> None:
        """Canvia el color dels límits de la barra de colors.

        Parameters
        ----------
        value: ColorBool
            Nou color dels límits
        key: InfSup
            Clau que indica sobre quin límit s'aplica

        """
        match key:
            case "inf":
                self.channel.color.lim_inf = value
            case "sup":
                self.channel.color.lim_sup = value

        self.view.redraw(cmap=True)

    def _change_scale(self, cscale: ColorBool) -> None:
        """Canvia el color de l'escala del mapa.

        cscale: ColorBool
            Nou color de l'escala

        """
        self.channel.color.scale = cscale
        self.view.redraw(scale=True)


class HeaderSpecWidgets(SpecWidgets):
    """Classe que determina les anotacions dels ginys de HeaderSpec i hereta d'SpecWidgets."""

    units: Widget[str]
    left: Widget[float]
    right: Widget[float]
    data: Widget[bool]
    log: Widget[bool]
    bottom: Widget[float]
    top: Widget[float]
    bkg: Widget[bool]
    etiq: Widget[bool]
    del_fit: Widget[str]
    CCD: Widget[bool]


class HeaderSpec(Header["SpecView"], SpecMixin):
    """Controla la capçalera dels mapes."""

    include_rawdata: bool = True
    include_r2: bool = True
    widgets: HeaderSpecWidgets

    def __init__(self, view: SpecView) -> None:
        """Inicia les dues classes importades."""
        SpecMixin.__init__(self, view.channel.spec)
        super().__init__(view)

    @property
    def spec(self) -> SpecData:
        """Retorna l'espectre actual."""
        return self.channel.spec

    @property
    def mapview(self) -> MapView:
        """Retorna l'objecte visor del mapa actual."""
        return self.view.file.mapview

    def _create_widgets(self) -> None:
        opts_fits = [self.fit_key, *self.spec.fits]
        opts_peaks: list[str] = []
        opts_pars: list[str] = []

        self.widgets = {
            "units": Widget(
                key="units",
                var_type=str,
                init=self.spec.units,
                text="Unitats",
                widget="cb",
                widget_kwargs={"options": ["nm", "eV", "1/cm"], "width": 8},
                setter=self._change_units,
            ),
            "left": Widget(
                key="left",
                var_type=float,
                init=self.spec.lims[0],
                text="Eix X",
                widget="entry",
                widget_kwargs={"width": 10},
                setter=self._change_left,
            ),
            "right": Widget(
                key="right",
                var_type=float,
                init=self.spec.lims[1],
                widget="entry",
                widget_kwargs={"width": 10},
                setter=self._change_right,
            ),
            "data": Widget(
                key="data",
                var_type=bool,
                init=True,
                text="Dades:",
                widget="checkbutton",
                setter=lambda value: self._show_data(data_visible=value),
            ),
            "log": Widget(
                key="log",
                var_type=bool,
                init=False,
                text="Log Y:",
                widget="checkbutton",
                setter=lambda value: self._change_log(log_scale=value),
            ),
            "fit": Widget(
                key="fit",
                var_type=str,
                init=self.fit_key,
                text="Ajusts:",
                widget="cb",
                widget_kwargs={"options": opts_fits, "width": 8},
                setter=self,
                mode="attr",
            ),
            "bottom": Widget(
                key="bottom",
                var_type=float,
                init=0,
                text="Eix Y",
                widget="entry",
                widget_kwargs={"width": 10},
                setter=self._change_bot,
            ),
            "top": Widget(
                key="top",
                var_type=float,
                init=1,
                widget="entry",
                widget_kwargs={"width": 10},
                setter=self._change_top,
            ),
            "bkg": Widget(
                key="bkg",
                var_type=bool,
                init=self.spec.bkg_active,
                text="Fons:",
                widget="checkbutton",
                setter=lambda value: self._show_bkg(bkg_active=value),
            ),
            "etiq": Widget(
                key="etiq",
                var_type=bool,
                init=True,
                text="Etiquetes:",
                widget="checkbutton",
                setter=lambda value: self._show_labels(etiquette=value),
            ),
            "peak": Widget(
                key="peak",
                var_type=str,
                init=self.peak_key,
                text="Pic:",
                widget="cb",
                widget_kwargs={"options": opts_peaks, "width": 8},
                setter=self,
                mode="attr",
            ),
            "parameter": Widget(
                key="parameter",
                var_type=str,
                init=self.parameter_key,
                text="Paràmetre:",
                widget="cb",
                widget_kwargs={"options": opts_pars, "width": 8},
                setter=self,
                mode="attr",
            ),
            "del_fit": Widget(
                key="del_fit",
                init="Eliminar",
                widget="button",
                setter=self._delete_fit,
            ),
            "CCD": Widget(
                key="CCD",
                var_type=bool,
                init=self.spec.ccd_active,
                text="CCD:",
                widget="checkbutton",
                setter=lambda value: self._change_ccd(ccd_active=value),
            ),
        }

        layout: list[tuple[int, int, SpecWidgetKey]] = [
            (0, 1, "units"), (0, 3, "left"), (0, 5, "right"), (0, 6, "data"), (0, 8, "log"),
            (1, 1, "fit"), (1, 3, "bottom"), (1, 5, "top"), (1, 6, "bkg"), (1, 8, "etiq"),
            (2, 1, "peak"), (2, 3, "parameter"), (2, 5, "del_fit"), (2, 6, "CCD")]

        for row, col, key in layout:
            self.widgets[key].add(self, row, col)

    def _update_map(self, channel: ChannelData) -> None:
        if self.fit_key != "rawdata":
            return

        lim_inf, lim_sup = self.spec.lims
        mask = (self.spec.x >= lim_inf) & (self.spec.x <= lim_sup)

        channel.data = np.nansum(self.spec.ydata[:, :, mask], axis=2, dtype=float) if self.spec.bkg_active\
            else np.nansum(np.maximum(self.spec.ydata[:, :, mask] - self.view.bkg[mask], 0), axis=2, dtype=float)

        channel.update_lims()

        self.mapview.header.widgets["lim_inf"].set(channel.lims[0])
        self.mapview.header.widgets["lim_sup"].set(channel.lims[1])

        self.mapview.refresh_map()

    def _select_fit(self) -> None:
        spec = self.spec
        spec.units = self.fit.units

        self.widgets["units"].set(spec.units)
        self.widgets["units"].config(state="disabled")

        start = round(spec.x[self.fit.xrange.start], 3)
        stop = round(spec.x[self.fit.xrange.stop], 3)

        spec.lims = [start, stop] if start < stop else [stop, start]

        self.widgets["left"].set(spec.lims[0])
        self.widgets["right"].set(spec.lims[1])

        self.widgets["peak"].config(state="readonly")
        self.widgets["parameter"].config(state="readonly")

        self.view.axis.set_xlim(*spec.lims)

    def _select_rawdata(self) -> None:
        self.widgets["units"].config(state="readonly")
        self.widgets["peak"].config(state="disabled")
        self.widgets["parameter"].config(state="disabled")

        self.channel.color.cmap_c = "SpecData"
        self.channel.units = "a.u"

        label = self.mapview.footer.widgets["track_z"].label
        if label is not None:
            label.config(text=f"{self.channel.name} ({self.channel.units})")

        self._update_map(self.channel)

    def _select_peak(self) -> None:
        self.widgets["parameter"].config(state="readonly")

    def _select_r2(self) -> None:
        self.channel.data = self.fit.r2
        self.channel.update_lims()

        self.channel.color.cmap_c = "jet"
        self.channel.units = ""

        self.widgets["parameter"].config(state="disabled")

        label = self.mapview.footer.widgets["track_z"].label
        if label is not None:
            label.config(text="r2")

        self.mapview.refresh_map()

    def _select_parameter(self) -> None:
        if self.parameter_key is None:
            msg = "No hi ha cap paràmetre seleccionat"
            raise ValueError(msg)

        self.channel.data = self.parameter
        self.channel.update_lims()

        param = DEFAULT_PARAMS[self.parameter_key]

        au = 1 if param.dim == 0 else 0

        self.channel.units = get_units(dim=param.dim, units=self.spec.units, au=au)
        self.channel.color.cmap_c = param.color

        z_label = self.mapview.footer.widgets["track_z"].label
        if z_label is not None:
            z_label.config(text=f"{self.parameter_key} ({self.channel.units})")

        self.mapview.refresh_map()

    def _change_left(self, left: float) -> None:
        """Canvia el límit superior de l'eix X.

        Parameters
        ----------
        left: float
            Nou valor

        """
        self.spec.lims[0] = left
        self.view.axis.set_xlim(left=left)
        self.view.canvas.draw_idle()
        self._update_map(self.channel)

    def _change_right(self, right: float) -> None:
        """Canvia el límit superior de l'eix X.

        Parameters
        ----------
        right: float
            Nou valor

        """
        self.spec.lims[1] = right
        self.view.axis.set_xlim(right=right)
        self.view.canvas.draw_idle()
        self._update_map(self.channel)

    def _change_bot(self, bottom: float) -> None:
        """Canvia el límit inferior de l'eix Y.

        Parameters
        ----------
        bottom: float
            Nou valor

        """
        self.view.axis.set_ylim(bottom=bottom)
        self.view.canvas.draw_idle()

    def _change_top(self, top: float) -> None:
        """Canvia el límit superior de l'eix Y.

        Parameters
        ----------
        top: float
            Nou valor

        """
        self.view.axis.set_ylim(top=top)
        self.view.canvas.draw_idle()

    def _change_units(self, units: SpecUnits) -> None:
        """Canvia les unitats actuals de l'espectre.

        Parameters
        ----------
        units: SpecUnits
            Noves unitats

        """
        self.spec.units = units
        self.view.axis.set_xlabel(self.view.xlabels[units])
        xdata = self.spec.x

        self.view.line.set_xdata(xdata)
        self.view.bkg_line.set_xdata(xdata)

        self.spec.lims = [round(float(np.min(xdata)), 3), round(float(np.max(xdata)), 3)]
        self.view.axis.set_xlim(*self.spec.lims)

        self.widgets["left"].set(self.spec.lims[0])
        self.widgets["right"].set(self.spec.lims[1])

        label = self.view.footer.widgets["track_x"].label
        if label is not None:
            label.config(text=self.view.xlabels[units])

        self.view.canvas.draw_idle()
        self._update_map(self.channel)

    def _show_data(self, *, data_visible: bool) -> None:
        """Mostra o amaga les dades espectrals.

        Parameters
        ----------
        data_visible: bool
            True: Mostrar. False: Amagar.

        """
        if not hasattr(self.view, "line"):
            return

        self.view.line.set_visible(data_visible)
        self.view.canvas.draw_idle()

    def _change_log(self, *, log_scale: bool) -> None:
        """Canvia l'eix Y de la figura de lineal a logarítmic.

        Parameters
        ----------
        log_scale: bool
            True: Logarítmic. False: Lineal.

        """
        if not hasattr(self.view, "line"):
            return

        if log_scale:
            self.view.axis.set_yscale("log")
            self.widgets["bottom"].set(1)
            self.view.axis.set_ylim(bottom=1)
        else:
            self.view.axis.set_yscale("linear")
            self.widgets["bottom"].set(0)
            self.view.axis.set_ylim(bottom=0)

        self.view.canvas.draw_idle()

    def _show_bkg(self, *, bkg_active: bool) -> None:
        """Mostra o amaga el fons espectral i corregeix les dades mostrades.

        Parameters
        ----------
        bkg_active: bool
            True: Mostrar. False: Amagar.

        """
        self.view.bkg_line.set_visible(bkg_active)
        self.spec.bkg_active = bkg_active
        self.view.plot_data()

        self.view.canvas.draw_idle()

        self._update_map(self.channel)

    def _show_labels(self, *, etiquette: bool) -> None:
        """Mostra o amaga les etiquetes relacionades amb cada pic sobre la figura.

        Parameters
        ----------
        etiquette: bool
            True: Mostrar. False: Amagar.

        """
        for peak in self.view.fit_peaks.values():
            peak.label.set_visible(etiquette)

        self.view.canvas.draw_idle()

    def _delete_fit(self) -> None:
        """Elimina l'ajust actual."""
        if self.fit_key == "rawdata":
            return

        self.spec.fits.pop(self.fit_key)
        self.update_fits()

    def _change_ccd(self, *, ccd_active: bool) -> None:
        """Activa o desactiva la correcció espectral de CCD.

        Parameters
        ----------
        ccd_active: bool
            True: Activat. False: Desactivat.

        """
        self.spec.ccd_active = ccd_active

        self._update_map(self.channel)
        self.view.plot_data()
