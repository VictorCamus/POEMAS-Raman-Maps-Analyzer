from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# =============================================================================
# DADES DE PROVA
# =============================================================================

@dataclass
class ParameterData:
    name: str
    units: str
    data: np.ndarray


@dataclass
class PeakData:
    name: str
    parameters: dict[str, ParameterData]


@dataclass
class FitData:
    name: str
    peaks: dict[str, PeakData]


@dataclass
class ChannelData:
    name: str
    fits: dict[str, FitData]


@dataclass
class FileData:
    name: str
    channels: dict[str, ChannelData]


def create_demo_files() -> dict[str, FileData]:
    """
    Crea uns mapes de prova perquè el prototip siga executable
    sense dependre encara de les classes reals del programa principal.
    """
    ny, nx = 80, 100
    y, x = np.mgrid[0:ny, 0:nx]

    rng = np.random.default_rng(1234)

    # Camps suaus per a simular paràmetres obtinguts d'un ajust.
    fwhm1 = 20 + 3 * np.sin(x / 12) + 2 * np.cos(y / 14)
    fwhm2 = 24 + 2 * np.sin(x / 15 + 0.8) + 2 * np.cos(y / 11)

    area1 = 100 + 25 * np.exp(-((x - 55) ** 2 + (y - 35) ** 2) / 1000)
    area2 = 80 + 20 * np.exp(-((x - 35) ** 2 + (y - 55) ** 2) / 900)

    center1 = 650 + 3 * np.sin(x / 20) + 1.5 * np.cos(y / 13)
    center2 = 656 + 2 * np.sin(x / 18 + 0.5) + 1.0 * np.cos(y / 15)

    intensity1 = 50 + 10 * np.exp(-((x - 60) ** 2 + (y - 30) ** 2) / 850)
    intensity2 = 35 + 8 * np.exp(-((x - 40) ** 2 + (y - 52) ** 2) / 900)

    # Alguns píxels invàlids, com és habitual en mapes reals.
    invalid = rng.random((ny, nx)) < 0.025
    invalid2 = rng.random((ny, nx)) < 0.02

    fwhm1[invalid] = np.nan
    area2[invalid] = np.nan
    intensity1[invalid2] = np.nan

    def p(name, units, data):
        return ParameterData(name, units, data)

    fit1 = FitData(
        "Ajust 1",
        {
            "P1": PeakData(
                "P1",
                {
                    "Center": p("Center", "nm", center1),
                    "FWHM": p("FWHM", "nm", fwhm1),
                    "Area": p("Area", "a.u.", area1),
                    "Intensity": p("Intensity", "a.u.", intensity1),
                },
            ),
            "P2": PeakData(
                "P2",
                {
                    "Center": p("Center", "nm", center2),
                    "FWHM": p("FWHM", "nm", fwhm2),
                    "Area": p("Area", "a.u.", area2),
                    "Intensity": p("Intensity", "a.u.", intensity2),
                },
            ),
            "P3": PeakData(
                "P3",
                {
                    "Center": p("Center", "nm", center1 + 4),
                    "FWHM": p("FWHM", "nm", fwhm1 + 5),
                    "Area": p("Area", "a.u.", area1 * 0.75),
                    "Intensity": p("Intensity", "a.u.", intensity1 * 0.7),
                },
            ),
        },
    )

    # Un segon fit per demostrar que els operands no han d'estar lligats
    # al mateix ajust.
    fit2 = FitData(
        "Ajust 2",
        {
            "P1": PeakData(
                "P1",
                {
                    "Center": p("Center", "nm", center1 + 1.0),
                    "FWHM": p("FWHM", "nm", fwhm1 * 0.95),
                    "Area": p("Area", "a.u.", area1 * 1.10),
                    "Intensity": p("Intensity", "a.u.", intensity1 * 1.15),
                },
            ),
            "P2": PeakData(
                "P2",
                {
                    "Center": p("Center", "nm", center2 - 0.5),
                    "FWHM": p("FWHM", "nm", fwhm2 * 1.08),
                    "Area": p("Area", "a.u.", area2 * 0.90),
                    "Intensity": p("Intensity", "a.u.", intensity2 * 1.20),
                },
            ),
        },
    )

    channel = ChannelData(
        "Spectra",
        {
            fit1.name: fit1,
            fit2.name: fit2,
        },
    )

    file1 = FileData("Mapa de prova 1", {"Spectra": channel})

    # Un segon fitxer amb dades lleugerament diferents.
    fit3 = FitData(
        "Ajust 1",
        {
            "P1": PeakData(
                "P1",
                {
                    "Center": p("Center", "nm", center1 + 2),
                    "FWHM": p("FWHM", "nm", fwhm1 * 1.05),
                    "Area": p("Area", "a.u.", area1 * 0.92),
                    "Intensity": p("Intensity", "a.u.", intensity1 * 0.85),
                },
            ),
            "P2": PeakData(
                "P2",
                {
                    "Center": p("Center", "nm", center2 + 1),
                    "FWHM": p("FWHM", "nm", fwhm2 * 0.90),
                    "Area": p("Area", "a.u.", area2 * 1.10),
                    "Intensity": p("Intensity", "a.u.", intensity2 * 0.90),
                },
            ),
        },
    )

    channel2 = ChannelData("Spectra", {"Ajust 1": fit3})
    file2 = FileData("Mapa de prova 2", {"Spectra": channel2})

    return {
        file1.name: file1,
        file2.name: file2,
    }


# =============================================================================
# OPERACIONS
# =============================================================================

@dataclass
class Operand:
    file: str = ""
    channel: str = ""
    fit: str = ""
    peak: str = ""
    parameter: str = ""

    @property
    def label(self) -> str:
        if not self.peak or not self.parameter:
            return "Operand buit"
        return f"{self.peak}.{self.parameter}"


class Operation:
    """
    Constructor i avaluador d'una expressió aritmètica.

    La versió inicial només suporta:
        +, -, *, /
    amb operands i parèntesis.
    """

    VALID_OPERATORS = {"+", "-", "*", "/"}

    def __init__(self, data: dict[str, FileData]):
        self.data = data
        self.tokens: list[Operand | str] = []

    def evaluate_operand(self, operand: Operand) -> np.ndarray:
        file = self.data[operand.file]
        channel = file.channels[operand.channel]
        fit = channel.fits[operand.fit]
        peak = fit.peaks[operand.peak]
        return peak.parameters[operand.parameter].data

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

    def evaluate(self) -> np.ndarray:
        """
        Avalua amb precedence matemàtica normal:
            * i / abans que + i -
        i suporta parèntesis.
        """
        if not self.tokens:
            raise ValueError("L'expressió està buida.")

        values: list[np.ndarray | str] = []

        for token in self.tokens:
            if isinstance(token, Operand):
                values.append(self.evaluate_operand(token))
            elif token in self.VALID_OPERATORS or token in {"(", ")"}:
                values.append(token)
            else:
                raise ValueError(f"Token desconegut: {token}")

        # Shunting-yard molt menut, només per als operadors bàsics.
        precedence = {"+": 1, "-": 1, "*": 2, "/": 2}
        output: list[np.ndarray | str] = []
        operators: list[str] = []

        for token in values:
            if isinstance(token, np.ndarray):
                output.append(token)
            elif token in self.VALID_OPERATORS:
                while (
                    operators
                    and operators[-1] in self.VALID_OPERATORS
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

        stack: list[np.ndarray] = []

        for token in output:
            if isinstance(token, np.ndarray):
                stack.append(token)
            else:
                if len(stack) < 2:
                    raise ValueError("Expressió aritmètica incorrecta.")
                right = stack.pop()
                left = stack.pop()
                stack.append(self._apply_operator(left, token, right))

        if len(stack) != 1:
            raise ValueError("Expressió aritmètica incorrecta.")

        return stack[0]

    def expression_text(self) -> str:
        parts = []
        for token in self.tokens:
            if isinstance(token, Operand):
                parts.append(token.label)
            else:
                parts.append(token)
        return " ".join(parts)


# =============================================================================
# GUI
# =============================================================================

class OperationWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Operacions entre paràmetres")
        self.root.geometry("1180x760")
        self.root.minsize(1050, 680)

        self.data = create_demo_files()

        self.operands: list[dict] = []
        self.expression_tokens: list[Operand | str] = []

        self.current_result: np.ndarray | None = None
        self.current_units = ""

        self._build_ui()
        self._add_operand()
        self._add_operand()

    # -------------------------------------------------------------------------
    # CONSTRUCCIÓ
    # -------------------------------------------------------------------------

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        self.control = ttk.Frame(main)
        self.control.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

        self.preview = ttk.Frame(main)
        self.preview.grid(row=0, column=1, sticky="nsew")

        self.preview.columnconfigure(0, weight=1)
        self.preview.rowconfigure(0, weight=1)

        # ---------------------------------------------------------------------
        # Esquerra: operands
        # ---------------------------------------------------------------------

        ttk.Label(
            self.control,
            text="Operació",
            font=("Arial", 15, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        self.operand_container = ttk.Frame(self.control)
        self.operand_container.pack(fill="x")

        ttk.Button(
            self.control,
            text="+ Afegir operand",
            command=self._add_operand,
        ).pack(fill="x", pady=(8, 4))

        ttk.Label(
            self.control,
            text="Operadors",
            font=("Arial", 11, "bold"),
        ).pack(anchor="w", pady=(12, 4))

        op_frame = ttk.Frame(self.control)
        op_frame.pack(fill="x")

        for op in ("+", "-", "×", "÷", "(", ")"):
            ttk.Button(
                op_frame,
                text=op,
                width=4,
                command=lambda value=op: self._add_operator(value),
            ).pack(side="left", padx=2)

        # ---------------------------------------------------------------------
        # Expressió
        # ---------------------------------------------------------------------

        ttk.Label(
            self.control,
            text="Expressió",
            font=("Arial", 11, "bold"),
        ).pack(anchor="w", pady=(14, 4))

        self.expression_var = tk.StringVar(value="")
        expression_entry = ttk.Entry(
            self.control,
            textvariable=self.expression_var,
            state="readonly",
            width=42,
        )
        expression_entry.pack(fill="x")

        ttk.Button(
            self.control,
            text="← Esborrar expressió",
            command=self._clear_expression,
        ).pack(fill="x", pady=(4, 0))

        # ---------------------------------------------------------------------
        # Resultat
        # ---------------------------------------------------------------------

        ttk.Label(
            self.control,
            text="Resultat",
            font=("Arial", 11, "bold"),
        ).pack(anchor="w", pady=(18, 4))

        ttk.Label(self.control, text="Nom del mapa:").pack(anchor="w")
        self.result_name = tk.StringVar(value="Operació")
        ttk.Entry(
            self.control,
            textvariable=self.result_name,
            width=42,
        ).pack(fill="x", pady=(2, 8))

        self.units_var = tk.StringVar(value="")
        ttk.Label(
            self.control,
            textvariable=self.units_var,
            wraplength=280,
        ).pack(anchor="w")

        button_frame = ttk.Frame(self.control)
        button_frame.pack(fill="x", pady=(18, 0))

        ttk.Button(
            button_frame,
            text="Calcular",
            command=self.calculate,
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        ttk.Button(
            button_frame,
            text="Aplicar",
            command=self.apply,
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # ---------------------------------------------------------------------
        # Dreta: mapa
        # ---------------------------------------------------------------------

        self.figure = Figure(figsize=(6.7, 6.7), dpi=100)
        self.ax = self.figure.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.preview)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value="Configura l'operació.")
        ttk.Label(
            self.preview,
            textvariable=self.status_var,
            anchor="w",
        ).pack(fill="x", pady=(6, 0))

    # -------------------------------------------------------------------------
    # OPERANDS
    # -------------------------------------------------------------------------

    def _add_operand(self):
        if len(self.operands) >= 4:
            messagebox.showinfo(
                "Límit d'operands",
                "Aquesta primera versió permet fins a 4 operands.",
            )
            return

        frame = ttk.LabelFrame(
            self.operand_container,
            text=f"Operand {len(self.operands) + 1}",
            padding=6,
        )
        frame.pack(fill="x", pady=4)

        vars_ = {
            "file": tk.StringVar(),
            "channel": tk.StringVar(),
            "fit": tk.StringVar(),
            "peak": tk.StringVar(),
            "parameter": tk.StringVar(),
        }

        widgets = {}

        def combo(label, key):
            ttk.Label(frame, text=label).pack(anchor="w")
            widget = ttk.Combobox(
                frame,
                textvariable=vars_[key],
                state="readonly",
                width=31,
            )
            widget.pack(fill="x", pady=(1, 4))
            widgets[key] = widget
            return widget

        combo("Fitxer", "file")
        combo("Canal", "channel")
        combo("Ajust", "fit")
        combo("Pic", "peak")
        combo("Paràmetre", "parameter")

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", pady=(3, 0))

        ttk.Button(
            button_row,
            text="Afegir a l'expressió",
            command=lambda index=len(self.operands): self._operand_to_expression(index),
        ).pack(side="left")

        ttk.Button(
            button_row,
            text="×",
            width=3,
            command=lambda index=len(self.operands): self._remove_operand(index),
        ).pack(side="right")

        item = {
            "frame": frame,
            "vars": vars_,
            "widgets": widgets,
        }

        self.operands.append(item)

        widgets["file"].bind(
            "<<ComboboxSelected>>",
            lambda _e, index=len(self.operands) - 1: self._file_changed(index),
        )
        widgets["channel"].bind(
            "<<ComboboxSelected>>",
            lambda _e, index=len(self.operands) - 1: self._channel_changed(index),
        )
        widgets["fit"].bind(
            "<<ComboboxSelected>>",
            lambda _e, index=len(self.operands) - 1: self._fit_changed(index),
        )
        widgets["peak"].bind(
            "<<ComboboxSelected>>",
            lambda _e, index=len(self.operands) - 1: self._peak_changed(index),
        )

        self._set_combo(
            widgets["file"],
            list(self.data),
            vars_["file"],
            next(iter(self.data)),
        )
        self._file_changed(len(self.operands) - 1)

    def _remove_operand(self, index):
        if len(self.operands) <= 1:
            messagebox.showinfo(
                "Operand",
                "Cal deixar almenys un operand.",
            )
            return

        self.operands[index]["frame"].destroy()
        del self.operands[index]

        # Reconstruïm els botons de callbacks perquè els índexs siguen correctes.
        self._rebuild_operands()

    def _rebuild_operands(self):
        states = []

        for item in self.operands:
            states.append({
                key: item["vars"][key].get()
                for key in item["vars"]
            })

        for item in self.operands:
            item["frame"].destroy()

        self.operands.clear()

        old_expression = self.expression_tokens.copy()

        for state in states:
            self._add_operand()
            item = self.operands[-1]

            for key, value in state.items():
                item["vars"][key].set(value)

            self._file_changed(len(self.operands) - 1)
            item["vars"]["channel"].set(state["channel"])
            self._channel_changed(len(self.operands) - 1)
            item["vars"]["fit"].set(state["fit"])
            self._fit_changed(len(self.operands) - 1)
            item["vars"]["peak"].set(state["peak"])
            self._peak_changed(len(self.operands) - 1)
            item["vars"]["parameter"].set(state["parameter"])

        # Manté l'expressió actual. Els objectes Operand originals poden seguir
        # sent vàlids perquè contenen només noms.
        self.expression_tokens = old_expression
        self._refresh_expression()

    # -------------------------------------------------------------------------
    # CASCADES DE COMBOS
    # -------------------------------------------------------------------------

    @staticmethod
    def _set_combo(widget, values, variable, value=None):
        widget.configure(values=values)

        if value in values:
            variable.set(value)
        elif values:
            variable.set(values[0])
        else:
            variable.set("")

    def _file_changed(self, index):
        item = self.operands[index]
        file_name = item["vars"]["file"].get()
        file = self.data[file_name]

        channels = list(file.channels)
        self._set_combo(
            item["widgets"]["channel"],
            channels,
            item["vars"]["channel"],
        )
        self._channel_changed(index)

    def _channel_changed(self, index):
        item = self.operands[index]
        file = self.data[item["vars"]["file"].get()]
        channel_name = item["vars"]["channel"].get()

        if not channel_name:
            return

        fits = list(file.channels[channel_name].fits)
        self._set_combo(
            item["widgets"]["fit"],
            fits,
            item["vars"]["fit"],
        )
        self._fit_changed(index)

    def _fit_changed(self, index):
        item = self.operands[index]
        file = self.data[item["vars"]["file"].get()]
        channel_name = item["vars"]["channel"].get()
        fit_name = item["vars"]["fit"].get()

        if not channel_name or not fit_name:
            return

        peaks = list(file.channels[channel_name].fits[fit_name].peaks)

        self._set_combo(
            item["widgets"]["peak"],
            peaks,
            item["vars"]["peak"],
        )
        self._peak_changed(index)

    def _peak_changed(self, index):
        item = self.operands[index]
        file = self.data[item["vars"]["file"].get()]
        channel_name = item["vars"]["channel"].get()
        fit_name = item["vars"]["fit"].get()
        peak_name = item["vars"]["peak"].get()

        if not channel_name or not fit_name or not peak_name:
            return

        parameters = list(
            file.channels[channel_name]
            .fits[fit_name]
            .peaks[peak_name]
            .parameters
        )

        self._set_combo(
            item["widgets"]["parameter"],
            parameters,
            item["vars"]["parameter"],
        )

    # -------------------------------------------------------------------------
    # EXPRESSIÓ
    # -------------------------------------------------------------------------

    def _operand_to_expression(self, index):
        item = self.operands[index]
        variables = item["vars"]

        if not all(variables[key].get() for key in variables):
            messagebox.showwarning(
                "Operand incomplet",
                "Selecciona fitxer, canal, ajust, pic i paràmetre.",
            )
            return

        operand = Operand(
            file=variables["file"].get(),
            channel=variables["channel"].get(),
            fit=variables["fit"].get(),
            peak=variables["peak"].get(),
            parameter=variables["parameter"].get(),
        )

        self.expression_tokens.append(operand)
        self._refresh_expression()

    def _add_operator(self, operator):
        # En la GUI es mostren × i ÷, però internament guardem * i /.
        operator = {"×": "*", "÷": "/"}.get(operator, operator)

        self.expression_tokens.append(operator)
        self._refresh_expression()

    def _clear_expression(self):
        self.expression_tokens.clear()
        self._refresh_expression()

    def _refresh_expression(self):
        display = []
        for token in self.expression_tokens:
            if isinstance(token, Operand):
                display.append(token.label)
            else:
                display.append({"*": "×", "/": "÷"}.get(token, token))

        self.expression_var.set(" ".join(display))

    # -------------------------------------------------------------------------
    # CÀLCUL
    # -------------------------------------------------------------------------

    def _get_units(self, operand: Operand) -> str:
        file = self.data[operand.file]
        channel = file.channels[operand.channel]
        fit = channel.fits[operand.fit]
        peak = fit.peaks[operand.peak]
        return peak.parameters[operand.parameter].units

    def _validate_basic_units(self):
        """
        Validació deliberadament senzilla:
        - + i - requereixen les mateixes unitats.
        - * i / es permeten sempre en aquesta primera versió.
        """
        units_stack: list[str | None] = []

        for token in self.expression_tokens:
            if isinstance(token, Operand):
                units_stack.append(self._get_units(token))
                continue

            if token == "(":
                continue

            if token == ")":
                continue

            if len(units_stack) < 2:
                # La validació completa de sintaxi la fa Operation.
                continue

            right = units_stack.pop()
            left = units_stack.pop()

            if token in {"+", "-"}:
                if left != right:
                    raise ValueError(
                        f"No es poden combinar amb '{token}' "
                        f"unitats {left!r} i {right!r}."
                    )
                units_stack.append(left)
            else:
                # Producte i divisió: deixem les unitats descrites textualment.
                if token == "*":
                    if left and right:
                        units_stack.append(f"{left}·{right}")
                    else:
                        units_stack.append(left or right)
                else:
                    if left and right:
                        units_stack.append(f"{left}/{right}")
                    else:
                        units_stack.append(left)

        return units_stack[-1] if units_stack else ""

    def calculate(self):
        if not self.expression_tokens:
            messagebox.showwarning(
                "Operació",
                "L'expressió està buida.",
            )
            return

        try:
            operation = Operation(self.data)
            operation.tokens = self.expression_tokens.copy()

            units = self._validate_basic_units()
            result = operation.evaluate()

        except Exception as exc:
            messagebox.showerror(
                "Error en l'operació",
                str(exc),
            )
            return

        self.current_result = result
        self.current_units = units or ""

        finite = np.isfinite(result)
        if np.any(finite):
            vmin = np.nanpercentile(result, 2)
            vmax = np.nanpercentile(result, 98)

            if np.isclose(vmin, vmax):
                delta = 1 if vmin == 0 else abs(vmin) * 0.05
                vmin -= delta
                vmax += delta

        else:
            vmin, vmax = 0, 1

        self.ax.clear()

        image = self.ax.imshow(
            result,
            origin="lower",
            aspect="auto",
            interpolation="none",
            vmin=vmin,
            vmax=vmax,
            cmap="viridis",
        )

        self.ax.set_title(self.expression_var.get())
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")

        if units:
            self.ax.set_title(f"{self.expression_var.get()}   [{units}]")

        self.figure.colorbar(image, ax=self.ax, pad=0.02)
        self.canvas.draw_idle()

        invalid = np.size(result) - np.count_nonzero(finite)

        self.units_var.set(
            f"Unitats/resultat: {units or '—'}    |    "
            f"Píxels no finits: {invalid}"
        )

        self.status_var.set(
            f"Calculat: {result.shape[1]} × {result.shape[0]} píxels."
        )

    def apply(self):
        if self.current_result is None:
            self.calculate()

        if self.current_result is None:
            return

        name = self.result_name.get().strip()
        if not name:
            messagebox.showwarning(
                "Resultat",
                "Especifica un nom per al mapa resultat.",
            )
            return

        # En el prototip, "Aplicar" només mostra què es crearia.
        # En la integració amb el programa principal ací crearíem el
        # ChannelData nou i l'afegiríem al fitxer/canal corresponent.
        messagebox.showinfo(
            "Aplicar",
            f"Mapa creat:\n\n"
            f"Nom: {name}\n"
            f"Expressió: {self.expression_var.get()}\n"
            f"Unitats: {self.current_units or '—'}\n"
            f"Shape: {self.current_result.shape}",
        )


if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass

    OperationWindow(root)
    root.mainloop()
