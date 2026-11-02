"""Transformacions de dades relacionades amb espectres."""
import threading
from dataclasses import dataclass
from functools import partial
from tkinter import Menu, messagebox, ttk
from typing import TYPE_CHECKING, Literal, TypedDict, cast

import numpy as np
from pybaselines import Baseline

from classes.fits import FitSpec
from process import converter as conv
from window import BaseWindow, SpecWindow
from window.mixin import SpecWidgets
from window.widgets import Progress, Widget

from .base import BaseMenu

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from classes.data import FitData, SpecData
    from classes.protocols import BaselineProtocol, GestorProtocol


class GestorSpec(BaseMenu):
    """Menú que gestiona les operacions dels mapes d'espectres."""

    def _add_menu(self, menu: Menu) -> None:
        self.add_tab(text="Calcular fons", func=partial(Fons, self))
        self.add_tab(text="Desplaçar dades", func=partial(ShiftX, self))
        self.add_tab(text="Fer ajust", func=partial(FitSpec, self))
        self.add_tab(text="Operar amb paràmetres", func=partial(ParamsOp, self))
        self.add_tab(text="Guardar espectre", func=self.save_spec)

        menu.add_cascade(label="Espectre", menu=self.submenu)

    def save_spec(self) -> None:
        """Guarda la imatge de l'espectre i les dades amb el fons corresponent si existeix."""
        spectra = self.current_file.current_channel.spec
        posy, posx = spectra.coords
        specview = self.current_file.specview

        folder = self.current_file.folder
        folder.with_name(f"{folder.name} - Spectra")
        folder.mkdir(parents=True, exist_ok=True)
        name_txt = folder / f"{folder.stem}_{posx + 1}_{posy + 1}"

        header = "\t".join([f"{'Xdata (' + spectra.units + ')':>12}", f"{'I (a.u.)':>12}", f"{'Bkg (a.u.)':>12}"])
        np.savetxt(f"{name_txt}.txt", np.c_[spectra.x, spectra.y, spectra.bkg],
                    header=header, delimiter="\t", fmt="%12.4f\t%12.2f\t%12.2f")

        specview.figure.savefig(f"{name_txt}.png", bbox_inches="tight")


class FonsWidgets(TypedDict):
    """Ginys de la classe Fons."""

    key: Widget[str]
    percentile: Widget[float]
    spline: Widget[float]
    bkg_map: Widget[str]
    apply: Widget[str]


class Fons(BaseWindow):
    """Calcula el fons dels espectres del mapa actual."""

    widgets: FonsWidgets

    def __init__(self, gestor: GestorProtocol) -> None:
        """Crea la finestra amb els ginys corresponents.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        self.spectra = gestor.current_file.current_channel.spec
        self.specview = gestor.current_file.specview
        self.mask = gestor.current_file.objects.mask
        self.dim = gestor.current_file.geometry.dim

        self.bkg_key: Literal["nan", "percentile", "spline"] = "nan"
        self.bkg_map: Literal["one", "different"] = "one"
        self.percentile: int = 0
        self.spline: int = 5

        super().__init__(gestor, "Calcular fons")

        self.bkg = np.full(self.xdata.shape, np.nan)

    @property
    def xdata(self) -> NDArray[np.float32]:
        """Retorna el rang espectral amb les unitats corresponents."""
        return self.spectra.x

    @property
    def ydata(self) -> NDArray[np.float32]:
        """Retorna les dades espectrals del píxel actual dins del rang indicat."""
        return self.spectra.y[self.spectra.xrange]

    @property
    def xrange(self) -> slice[int, int, int]:
        """Retorna el rang seleccionat."""
        return self.spectra.xrange

    @property
    def baseline(self) -> BaselineProtocol:
        """Retorna la línia base de pybaselines."""
        return cast("BaselineProtocol", Baseline(x_data=self.xdata[self.xrange]))

    def _create_widgets(self) -> None:
        opts = {"Cap": "nan", "Percentil": "percentile", "Spline": "spline"}

        opts_bkg = {"Únic": "one", "Un per espectre": "different"}

        self.widgets = {
            "key": Widget(
                key="key",
                var_type=str,
                init="nan",
                text="Classe de fons:",
                widget="radiobutton",
                widget_kwargs={"options": opts},
                setter=self.set_key,
            ),
            "percentile": Widget(
                key="percentile",
                var_type=int,
                init=self.percentile,
                text="Percentil (%):",
                widget="scale",
                widget_kwargs={"state": "disabled"},
                setter=self.set_percentile,
            ),
            "spline": Widget(
                key="spline",
                var_type=int,
                init=self.spline,
                text="Spline:",
                widget="scale",
                widget_kwargs={"from_": 3, "to": 7, "state": "disabled"},
                setter=self.set_spline,
            ),
            "bkg_map": Widget(
                key="bkg_map",
                var_type=str,
                init="one",
                text="Fons del mapa:",
                widget="radiobutton",
                widget_kwargs={"options": opts_bkg},
                setter=self,
                mode="attr",
            ),
            "apply": Widget(
                key="apply",
                init="Aplicar",
                widget="button",
                setter=self.apply_bkg,
            ),
        }

    def set_key(self, bkg_key: Literal["nan", "percentile", "spline"]) -> None:
        """Indica la classe de fons que es vol.

        Parameters
        ----------
        bkg_key: Literal["nan", "percentile", "spline"]
            Clau del fons seleccionat

        """
        self.bkg_key = bkg_key

        match self.bkg_key:
            case "nan":
                self.widgets["percentile"].config(state="disabled")
                self.widgets["spline"].config(state="disabled")
                self.plot_bkg(np.full_like(self.xrange, np.nan))
            case "percentile":
                self.widgets["percentile"].config(state="normal")
                self.widgets["spline"].config(state="disabled")
                self.set_percentile(self.percentile)
            case "spline":
                self.widgets["percentile"].config(state="disabled")
                self.widgets["spline"].config(state="normal")
                self.set_spline(self.spline)

    def set_percentile(self, value: int) -> None:
        """Dona un nou valor de percentil i actualitza el fons.

        value: int
            Nou valor del percentil

        """
        self.percentile = value

        bkg = np.array(np.nanpercentile(self.ydata, value), np.float32)
        self.plot_bkg(bkg)

    def set_spline(self, value: int) -> None:
        """Dona un nou valor d'spline i actualitza el fons.

        value: int
            Nou valor d'spline

        """
        self.spline = value

        baseline, _ = self.baseline.mixture_model(self.ydata, 10**value)
        bkg = np.array(baseline, np.float32)
        self.plot_bkg(bkg)

    def plot_bkg(self, bkg: NDArray[np.float32]) -> None:
        """Dibuixa els fons amb les dades donades.

        bkg: NDArray[np.float32]
            Noves dades del fons

        """
        bkg = np.maximum(bkg, 0)

        self.bkg = np.full(self.xdata.shape, np.nan)
        self.bkg[self.xrange] = bkg

        self.specview.bkg_line.set_ydata(self.bkg)
        self.specview.canvas.draw_idle()

    def apply_bkg(self) -> None:
        """Propaga el fons triat a la matriu sencera d'espectres."""
        fit = self.specview.header.fit_key
        spec_file = self.spectra if fit == "rawdata" else self.spectra.fits[fit]

        if self.bkg_key == "nan":
            spec_file.bkgdata = None
            return

        match self.bkg_map:
            case "one":
                bkg = np.tile(self.bkg, (*self.dim, 1))
                spec_file.bkgdata = np.rint(bkg).astype(np.uint16) if np.nanmax(bkg) <= np.iinfo(np.uint16).max\
                                                                            else np.rint(bkg).astype(np.uint32)

            case "different":
                total = self.dim[0] * self.dim[1]

                progress = Progress(self.window, title="Calculant fons", maximum=total)
                threading.Thread(target=self._calculate_bkg_thread, args=(progress, spec_file), daemon=True).start()

    def _calculate_bkg_thread(self, progress: Progress, spec_file: FitData | SpecData) -> None:
        ydata = self.spectra.ydata
        mask = self.mask

        if self.bkg_key == "nan":
            msg = "Per a calcular el fons, la clau seleccionada ha de ser 'percentile' o 'spline'."
            raise ValueError(msg)

        bkgdata = np.zeros(ydata.shape)

        for i in range(ydata.shape[0]):
            for j in range(ydata.shape[1]):
                if progress.cancelled():
                    progress.finish("Operació cancel·lada")
                    return

                progress.increment()

                if not mask[i, j]:
                    continue

                spectrum = ydata[i, j, :][self.xrange]

                match self.bkg_key:
                    case "percentile":
                        value = np.nanpercentile(spectrum, self.widgets["percentile"].get())
                        bkgdata[i, j, self.xrange] = np.maximum(value, 0)
                    case "spline":
                        values, _ = self.baseline.mixture_model(spectrum, lam=10 ** self.widgets["spline"].get())
                        bkgdata[i, j, self.xrange] = np.maximum(values, 0)

        spec_file.bkgdata = np.rint(bkgdata).astype(np.uint16) if np.nanmax(bkgdata) <= np.iinfo(np.uint16).max\
                                                                else np.rint(bkgdata).astype(np.uint32)

        progress.finish()


class ShiftWidgets(TypedDict):
    """Ginys de la classe ShiftX."""

    shift: Widget[float]
    apply: Widget[str]


class ShiftX(BaseWindow):
    """Desplaça el rang espectral d'un mapa. Especialment útil si les dades estan descalibrades."""

    widgets: ShiftWidgets

    def __init__(self, gestor: GestorProtocol) -> None:
        """Obri la finestra amb els ginys corresponents.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        self.spectra = gestor.current_file.current_channel.spec
        self.specview = gestor.current_file.specview

        super().__init__(gestor, "Desplaçar dades")

    def shift_x(self, shift: float) -> None:
        """Desplaça l'espectre actual i actualitza la gràfica.

        Parameters
        ----------
        shift: float
            Valor del desplaçament

        """
        x = self.spectra.x - shift
        self.specview.line.set_xdata(x)
        self.specview.bkg_line.set_xdata(x)

        self.specview.canvas.draw_idle()

    def apply(self) -> None:
        """Aplica el desplaçament a tota la matriu d'espectres."""
        xdata = self.spectra.xdata
        x = xdata[self.spectra.units] - self.widgets["shift"].get()

        units = self.spectra.units
        laser = self.spectra.laser

        match units:
            case "nm":
                xdata["nm"] = x
                xdata["eV"] = conv.nm_to_energy(x)
                xdata["1/cm"] = conv.nm_to_raman(x, laser)

            case "eV":
                xdata["eV"] = x
                xdata["nm"] = conv.energy_to_nm(x)
                xdata["1/cm"] = conv.energy_to_raman(x, laser)

            case "1/cm":
                xdata["1/cm"] = x
                xdata["nm"] = conv.raman_to_nm(x, laser)
                xdata["eV"] = conv.raman_to_energy(x, laser)

        self.widgets["shift"].set(0)

    def _create_widgets(self) -> None:
        self.widgets = {
            "shift": Widget(
                key="shift",
                var_type=float,
                init=0,
                text=f"Desplaçament ({self.spectra.units}):",
                widget="entry",
                setter=self.shift_x,
            ),
            "apply": Widget(
                key="key",
                init="Aplicar",
                widget="button",
                setter=self.apply,
            ),
        }


@dataclass
class ParInfo:
    """Classe que conté les claus per a poder cridar el paràmetre triat en l'expressió aritmètica."""

    fit: str
    peak_ref: str
    peak_name: str
    parameter: str

    @property
    def label(self) -> str:
        """Determina el text que es mostrarà en l'expressió."""
        return f"{self.peak_name}.{self.parameter}"


type Dimension = tuple[int, int]
type ParameterValue = tuple[NDArray[np.float32], Dimension]


class ParamsWidgets(SpecWidgets, total=False):
    """Ginys de la classe ParamsOp."""

    plus: Widget[str]
    minus: Widget[str]
    mult: Widget[str]
    div: Widget[str]
    left_bracket: Widget[str]
    right_bracket: Widget[str]

    expr: Widget[str]
    add_par: Widget[str]
    delete: Widget[str]
    calc: Widget[str]


type OperatorKey = Literal["plus", "minus", "mult", "div", "left_bracket", "right_bracket"]


class ParamsOp(SpecWindow):
    """Opera amb els paràmetres dels ajustos per a obtindre nous mapes."""

    widgets: ParamsWidgets

    def __init__(self, gestor: GestorProtocol) -> None:
        """Crea la finestra amb els ginys corresponents.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        super().__init__(gestor, "Operar amb paràmetres")

        self.tokens: list[ParInfo | str] = []
        self.refresh_map = gestor.current_file.mapview.refresh_map
        self.channel = gestor.current_file.current_channel

        op_frame = ttk.Frame(self.control_frame)
        row = len(self.widgets)
        op_frame.grid(row=0, column=2, rowspan=3)
        op_dict: dict[OperatorKey, str] = {"plus": "+", "minus": "-", "mult": "*", "div": "/",
                                    "left_bracket": "(", "right_bracket": ")"}
        self._create_widgets()

        for op, value in op_dict.items():
            widget = Widget(
                key=op,
                var_type=str,
                init=value,
                widget="button",
                widget_kwargs={"width": 3},
                setter=self.add_operator,
            )

            cast("dict[str, Widget[str]]", self.widgets)[op] = widget

        self.widgets["expr"] = Widget(
            key="expr",
            init="",
            widget="entry",
            widget_kwargs={"width": 45, "state": "readonly"},
        )
        self.widgets["expr"].add(self.control_frame, row=row + 1, col=0, columnspan=3)
        self.widgets["expr"].config(font=("Helvetica", 12))

        self.widgets["add_par"] = Widget(
            key="add_par",
            init="Afegir paràmetre",
            widget="button",
            setter=self.add_parameter,
        )
        self.widgets["add_par"].add(self.control_frame, row=row + 2, col=0)

        self.widgets["delete"] = Widget(
            key="delete",
            init="Esborrar",
            widget="button",
            widget_kwargs={"width": 12},
            setter=self.clear_expression,
        )
        self.widgets["delete"].add(self.control_frame, row=row + 2, col=1)

        self.widgets["calc"] = Widget(
            key="calc",
            init="Calcular",
            widget="button",
            widget_kwargs={"width": 12},
            setter=self.calculate,
        )
        self.widgets["calc"].add(self.control_frame, row=row + 2, col=2)

    def _create_widgets(self) -> None:
        opts_fits = list(self.spectra.fits)
        self.fit_key = opts_fits[0]
        self._fit = self.spectra.fits[self.fit_key]

        opts_peaks = {peak.name: key for key, peak in self.fit.peaks.items()}

        self.peak_key = next(iter(opts_peaks))
        self._peak = self.fit.peaks[self.peak_key]

        opts_params = self.peak.parameter_names
        self.parameter_key = opts_params[0]
        self._parameter = self.peak.params[self.parameter_key]

        self.widgets = {
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
                widget_kwargs={"options": opts_params, "width": 8},
                setter=self,
                mode="attr",
            ),
        }

    def add_operator(self, operand: ParInfo | str) -> None:
        """Afig un paràmetre (Operand) o un operador a la llista amb els objectes."""
        self.tokens.append(operand)
        self.refresh_expression()

    def add_parameter(self) -> None:
        """Afig el paràmetre actual a l'expressió si existeix.

        Raises
        ------
        ValueError
            Si no existeix el paràmetre seleccionat del pic

        """
        if self.parameter_key is None:
            msg = "No hi ha cap paràmetre seleccionat"
            raise ValueError(msg)

        operand = ParInfo(
            fit=self.fit_key,
            peak_ref=self.peak.ref,
            peak_name=self.peak.name,
            parameter=self.parameter_key)

        self.add_operator(operand)

    def refresh_expression(self) -> None:
        """Mostra l'expressió de l'operació en l'etiqueta corresponent."""
        display = []
        for token in self.tokens:
            if isinstance(token, ParInfo):
                display.append(token.label)
            else:
                display.append(token)

        self.widgets["expr"].set(" ".join(display))

    def clear_expression(self) -> None:
        """Neteja l'últim element de l'expressió."""
        if not self.tokens:
            return

        self.tokens.pop()
        self.refresh_expression()

    def calculate(self) -> None:
        """Calcula el resultat de l'expressió aritmètica i actualitza el mapa visual."""
        if not self.tokens:
            messagebox.showwarning("Operació", "L'expressió està buida.")
            return

        self.channel.data, (dim, au) = self.evaluate()
        self.channel.units = conv.get_units(dim=dim, units=self.fit.units, au=au)
        self.channel.update_lims()

        self.refresh_map(self.channel)

    def evaluate(self) -> ParameterValue:
        """Avalua l'expressió i retorna les dades calculades i les dimensions.

        Returns
        -------
        ParameterValue: data, (dim, au)
            Element amb les dades de l'expressió i la informació necessària per a obtindre les unitats

        Raises
        ------
        ValueError
            Si l'expressió està buida

        """
        if not self.tokens:
            msg = "L'expressió està buida."
            raise ValueError(msg)

        values = self._resolve_tokens()
        output = self._to_postfix(values)

        return self._evaluate_postfix(output)

    def _resolve_tokens(self) -> list[ParameterValue | str]:
        """Resol els operands i valida els tokens de l'expressió.

        Returns
        -------
        list[ParameterValue | Str]
            Llista que conté els paràmetres amb què s'opera i les operacions aritmètiques.

        """
        values: list[ParameterValue | str] = []

        for token in self.tokens:
            if isinstance(token, ParInfo):
                values.append(self._resolve_parameter(token))
            elif token in {"+", "-", "*", "/", "(", ")"}:
                values.append(token)

        return values

    def _resolve_parameter(self, par: ParInfo) -> ParameterValue:
        """Obté les dades i les dimensions del paràmetre corresponent.

        Parameters
        ----------
        par: ParInfo
            Claus per a accedir al paràmetre

        Returns
        -------
        ParameterValue
            Dades i dimensions del paràmetre

        """
        fit = self.spectra.fits[par.fit]
        peak = fit.peaks[par.peak_ref]

        data = peak.get_parameter(par.parameter)
        dim = fit.config[peak.ref].params[par.parameter].dim

        au = 1 if dim == 0 else 0

        return data, (dim, au)

    @staticmethod
    def _to_postfix(values: list[ParameterValue | str]) -> list[ParameterValue | str]:
        """Converteix una expressió infixa a notació postfixa.

        Implementa l'algoritme Shunting-yard, que permet transformar una
        expressió matemàtica respectant la prioritat dels operadors i els
        parèntesis, sense necessitat d'avaluar-la durant la conversió.

        Els operands es representen mitjançant tuples de tipus
        ParameterValue, mentre que els operadors i els parèntesis es
        representen mitjançant cadenes de text.

        Parameters
        ----------
        values: list[ParameterValue | str]
            Elements de l'expressió en notació infixa, en l'ordre
            en què apareixen. Els operands han d'estar resolts prèviament.

        Returns
        -------
            Llista d'elements equivalents en notació postfija, en què cada
            operador apareix després dels operands sobre els quals actua.

        Raises
        ------
        ValueError
            Si l'expressió conté parèntesis desequilibrats.

        Notes
        -----
            La prioritat dels operadors es defineix de la manera següent:
            - Suma i resta: prioritat 1.
            - Multiplicació i divisió: prioritat 2.

            Els operadors de la mateixa prioritat s'avaluen d'esquerra a
            dreta. Per això, quan es troba un operador nou, es retiren de
            la pila els operadors pendents amb prioritat igual o superior.

            Per exemple, l'expressió A + B * C es transforma en
            A B C * +, de manera que la multiplicació s'efectua abans
            que la suma.

        """
        # Prioritat relativa dels operadors aritmètics.
        precedence = {"+": 1, "-": 1, "*": 2, "/": 2}

        # Contindrà l'expressió convertida a notació postfija.
        output: list[ParameterValue | str] = []

        # Pila temporal d'operadors i parèntesis pendents de processar.
        operators: list[str] = []

        for item in values:
            # Els operands passen directament a la sortida perquè no
            # necessiten cap tractament per a determinar-ne la prioritat.
            if isinstance(item, tuple):
                output.append(item)

            # Quan trobem un operador, processem primer els operadors
            # pendents que tinguen una prioritat igual o superior.
            elif item in precedence:
                while (
                    operators
                    and operators[-1] in precedence
                    and precedence[operators[-1]] >= precedence[item]
                ):
                    output.append(operators.pop())

                # L'operador actual queda pendent fins que trobem un
                # operador de prioritat igual o inferior, o acabem.
                operators.append(item)

            # El parèntesi d'obertura delimita un subgrup. Es guarda
            # en la pila per impedir que els operadors externs es
            # processen abans que els del seu interior.
            elif item == "(":
                operators.append(item)

            # El parèntesi de tancament indica que hem acabat de llegir
            # el subgrup i que cal traure'n els operadors pendents.
            elif item == ")":
                ParamsOp._close_parenthesis(operators, output)

        # En acabar de recórrer l'expressió, processem els operadors
        # que encara queden pendents en la pila.
        while operators:
            operator = operators.pop()

            # Un parèntesi d'obertura que continue en la pila indica
            # que no s'ha tancat correctament.
            if operator in {"(", ")"}:
                msg = "Parèntesis desequilibrats."
                raise ValueError(msg)

            output.append(operator)

        return output

    @staticmethod
    def _close_parenthesis(operators: list[str], output: list[ParameterValue | str]) -> None:
        """Processa un parèntesi de tancament durant la conversió a postfixa.

        Trau de la pila els operadors pendents fins a trobar el parèntesi
        d'obertura corresponent, que s'elimina sense afegir-lo a la sortida.

        Parameters
        ----------
        operators: list[str]
            Pila d'operadors pendents.
        output: list[ParameterValue | str]
            Expressió que s'està construint en notació postfixa.

        Raises
        ------
        ValueError: Si no hi ha cap parèntesi d'obertura corresponent.

        """
        while operators and operators[-1] != "(":
            output.append(operators.pop())

        if not operators:
            msg = "Parèntesis desequilibrats."
            raise ValueError(msg)

        operators.pop()

    @staticmethod
    def _evaluate_postfix(output: list[ParameterValue | str]) -> ParameterValue:
        """Avalua una expressió matemàtica en notació postfija.

        Recorre els elements de l'expressió d'esquerra a dreta i utilitza
        una pila per emmagatzemar els operands i els resultats parcials.
        Com que els operadors apareixen després dels operands, no cal
        gestionar explícitament la prioritat dels operadors ni els
        parèntesis durant l'avaluació.

        Cada operand i cada resultat parcial es representa mitjançant
        un ParameterValue, que conté les dades numèriques i la dimensió
        associada al resultat.

        Parameters
        ----------
        output: list[ParameterValue | str]
            Expressió en notació postfixa, obtinguda prèviament mitjançant _to_postfix().
            Els operands han d'estar resolts i els operadors han de ser vàlids.

        Returns
        -------
        result: ParameterValue
            Tupla formada per les dades numèriques del resultat i la
            dimensió corresponent.

        Raises
        ------
        ValueError:
            Si no hi ha prou operands per a executar una
            operació o si, en acabar, l'expressió no produeix
            un únic resultat.

        Notes
        -----
            Per a cada operador, els dos últims operands de la pila
            s'extrauen en l'ordre correcte: primer l'operand dret i
            després l'esquerre.

            Les dades numèriques es calculen mitjançant conv.apply_operator,
            mentre que les dimensions es determinen mitjançant
            conv.combine_dimensions.

        """
        # Pila d'operands i resultats parcials. Cada element conté
        # tant les dades numèriques com les dimensions corresponents.
        stack: list[ParameterValue] = []

        for item in output:
            # Els operands es guarden en la pila fins que apareix
            # un operador que en necessita dos per a calcular un resultat.
            if isinstance(item, tuple):
                stack.append(item)
                continue

            # Les operacions aritmètiques binàries necessiten dos operands.
            # Si no n'hi ha prou, l'expressió postfija és incorrecta.
            if len(stack) < 2:
                msg = "Es necessiten almenys dos operands per a calcular una expressió."
                raise ValueError(msg)

            # L'últim operand introduït és el dret i el penúltim és
            # l'esquerre. Mantindre aquest ordre és essencial per a
            # operacions no commutatives, com ara la resta i la divisió.
            right_data, right_dim = stack.pop()
            left_data, left_dim = stack.pop()

            # Calculem el resultat numèric i les dimensions per separat.
            # La primera funció aplica l'operació a les dades; la segona
            # comprova i combina les dimensions dels dos operands.
            result = conv.apply_operator(left_data, item, right_data)
            result_dim = conv.combine_dimensions(left_dim, item, right_dim)

            # El resultat es converteix en un operand nou que podrà
            # participar en operacions posteriors.
            stack.append((result, result_dim))

        # Una expressió correcta ha de produir exactament un resultat.
        # Si en queden zero o més d'un, l'expressió és incorrecta.
        if len(stack) != 1:
            msg = "Expressió aritmètica incorrecta."
            raise ValueError(msg)

        return stack[0]
