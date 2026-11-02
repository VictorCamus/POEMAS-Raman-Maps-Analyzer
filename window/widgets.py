"""Ginys de l'aplicació."""

import threading
import tkinter as tk
from collections.abc import Mapping
from functools import partial
from tkinter import ttk
from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict, Unpack, cast

from matplotlib import colors as mcolors

from drawing.plots import PLOT_COLORS

if TYPE_CHECKING:
    from collections.abc import Callable

    from classes.protocols import VariableProtocol

TYPE_MAP: dict[type, type[tk.Variable]] = {
    bool: tk.BooleanVar,
    int: tk.IntVar,
    float: tk.DoubleVar,
    str: tk.StringVar,
}


type VarType = bool | int | float | str | None
type GenericWidgets = Mapping[str, object]

type WidgetType = Literal[
    "button",
    "cb",
    "checkbutton",
    "colorcb",
    "entry",
    "radiobutton",
    "scale",
]

type WidgetInstance = (
    ttk.Button
    | ttk.Checkbutton
    | ttk.Combobox
    | ttk.Entry
    | ttk.Frame
    | tk.Scale
)


class Widget[T: VarType]:
    """Classe que crea i gestiona totes les accions relatives a un ttk.Widget lligat a un tk.Variable."""

    def __init__(
        self,
        key: str,
        var_type: type[VarType] | None = None,
        init: T | None = None,
        text: str = "",
        widget: WidgetType = "entry",
        widget_kwargs: dict[str, object] | None = None,
        setter: Callable[[T], None] | object | None = None,
        mode: Literal["call", "attr", "dict"] = "call") -> None:
        """Crea les característiques del giny abans de lligar-lo a un objecte visual.

        Parameters
        ----------
        key: str
            Clau del giny
        var_type: type[VarType] | None = None
            Tipus de d'objecte tk.Variable que es crearà. Si és None,
            el valor del giny no és modificable i la funció no necessita arguments
        init: T | None = None
            Valor inicial del giny
        text: str = ""
            Text de l'etiqueta que precedeix el giny
        widget: WidgetType = "entry"
            Classe de giny
        widget_kwargs: dict[str, object] | None = None
            Característiqes addicionals del giny
        setter: Callable[[T], None] | object | None = None,
            Funció o objecte que es cridarà quan s'active el callback
        mode: Literal["call", "attr", "dict"] = "call") -> None:
            Classe de d'objecte que és el setter

        Raises
        ------
        TypeError
            Si s'ha cridat un setter sense cap variable i no és una funció (callable)

        """
        self.var_type = var_type
        self.init = init

        self.value: VariableProtocol[T]
        self.callback: Callable[[T], None] | None = None
        self.action: Callable[[], None] | None = None

        self.text: str = text
        self.widget_type: WidgetType = widget
        self.widget_kwargs: dict[str, object] = {} if widget_kwargs is None else widget_kwargs
        self.widget: tk.Widget

        self.label: ttk.Label | None = None
        self.options: dict[str, T] = {}

        self._make_setter(key, setter, mode)

        if var_type is None:
            if mode != "call":
                msg = "Un widget sense variable només admet el mode 'call'."
                raise TypeError(msg)

            if setter is not None and not callable(setter):
                msg = "L'acció ha de ser callable."
                raise TypeError(msg)

            self.action = cast("Callable[[], None] | None", setter)

        else:
            if var_type not in TYPE_MAP:
                msg = (f"Tipus no admés: {var_type.__name__}. Ha de ser bool, int, float o str.")
                raise TypeError(msg)

            self.callback = self._make_setter(key, setter, mode)

        if "options" in self.widget_kwargs:
            options = self.widget_kwargs.pop("options")

            if isinstance(options, dict):
                self.options = cast("dict[str, T]", options)
            else:
                opts_keys = cast("list[str]", options)
                opts_values = cast("list[T]", options)
                self.options = dict(zip(opts_keys, opts_values, strict=False))

    def add(self, frame: ttk.Frame, row: int = 0, col: int = 0, columnspan: int = 1) -> None:
        """Associa un Widget a un entorn visual.

        Parameters
        ----------
        frame: ttk.Frame
            Entorn visual
        row: int = 0
            Fila en què es coloca el Widget
        col: int = 0
            Columna en què es coloca el Widget
        columnspan: int = 1
            Nombre de columnes que ocupa el Widget

        """
        self.value = TYPE_MAP[self.var_type](frame, value=self.init) if self.var_type is not None\
                               else TYPE_MAP[str](frame, value=self.init)

        widget_kwargs = self.widget_kwargs.copy()
        widget_kwargs["set_value"] = self.value

        self.widget = self._create_widget(partial(self._func), frame)

        if self.text:
            self.label = ttk.Label(frame, text=self.text)
            self.label.grid(row=row, column=col, padx=5, pady=4, sticky="nw")
            col += 1

        self.widget.grid(row=row, column=col, columnspan=columnspan, padx=5, pady=4, sticky="nw")

    def set(self, value: T | None) -> None:
        """Dona un nou valor a la variable tkinter i executa el callback.

        Parameters
        ----------
        value: T | None
            Nou valor de tk.Variable

        Raises
        ------
        ValueError
            Si el valor donat és None i els ginys no són comboboxes o entrades, no es permet que es buide el giny.

        """
        if value is None:
            if self.var_type is str:
                cast("VariableProtocol[str]", self.value).set("")
            else:
                msg = "El giny corresponent no accepta None."
                raise ValueError(msg)
        else:
            self.value.set(value)

        if isinstance(self.widget, ttk.Combobox):
            key = next((key for key, val in self.options.items() if val == value), "")
            self.widget.set(key)

        if self.callback is not None:
            self.callback(self.get())

    def get(self) -> T:
        """Obté el valor de tk.Variable.

        Returns
        -------
        value: T
            Estat actual de la variable

        """
        return self.value.get()

    def config(self, *args: object, **kwargs: object) -> None:
        """Configuració del giny.

        Parameters
        ----------
        *args: object
            Paràmetres posicionals donats
        **kwargs: object
            Paràmetres amb la clau fixa donats

        """
        self.widget.config(*args, **kwargs)

    def _create_widget(self, func: partial[None], frame: ttk.Frame) -> WidgetInstance:
        """Crea el giny de tkinter segons el tipus triat.

        Parameters
        ----------
        func: partial[None]
            Funció que s'executa quan s'interactua amb el giny
        frame: ttk.Frame
            Requadre visual on se situarà el giny

        Returns
        -------
        tk.Widget: WidgetInstance
            Objecte giny de tkinter

        """
        kwargs = self.widget_kwargs
        widget: WidgetInstance

        value = cast("tk.Variable", self.value)
        match self.widget_type:
            case "button":
                widget = _add_button(func, frame, value, **cast("ButtonOptions", kwargs))

            case "cb":
                widget = _add_combobox(
                    func, frame, cast("tk.StringVar", value), options=self.options, **cast("ComboboxOptions", kwargs))

            case "checkbutton":
                widget = _add_checkbutton(func, frame, value)

            case "colorcb":
                widget = _add_colorcombobox(func, frame, cast("tk.StringVar", value))

            case "entry":
                widget = _add_entry(func, frame, value, **cast("EntryOptions", kwargs))

            case "radiobutton":
                widget = _add_radiobuttons(func, frame, value, options=self.options, **cast("RadioOptions", kwargs))

            case "scale":
                widget = _add_scale(func, frame, cast("tk.IntVar | tk.DoubleVar", value),
                        **cast("ScaleOptions", kwargs))

        return widget

    def _func(self, display_var: str | None = None) -> None:
        """Retorna la funció corresponent segons si necessita un paràmetre per a cridar-se o no.

        Parameters
        ----------
        display_var: str | None = None
            Text mostrat en pantalla que representa la variable. Només és diferent per als combobox.

        """
        if (isinstance(self.widget, ttk.Combobox) and display_var is not None):
            self.set(value=self.options[display_var])
            return

        if self.action is not None:
            self.action()
        elif self.callback is not None:
            self.callback(self.get())

    @staticmethod
    def _make_setter(key: str, setter: object | None, mode: Literal["call", "attr", "dict"])\
                    -> Callable[[T], None] | None:
        """Converteix qualsevol setter admés en un callable uniforme.

        Parameters
        ----------
        key: str
            Clau del diccionari o l'atribut de classe, si escau
        setter: object | None
            Objecte que controla la crida.
        mode: Literal["call", "attr", "dict"])
            Classe d'operació que segueix el setter segons el seu tipus

        Returns
        -------
        func -> Callable[[T], None] | None
            Funció final que s'assigna al callback. Si no hi ha setter, es retorna None.

        Raises
        ------
        TypeError
            Si el mode i el tipus d'objecte no coincideixen.

        """
        if setter is None:
            return None

        match mode:
            case "call":
                if not callable(setter):
                    msg = "El setter ha de ser callable en mode 'call'."
                    raise TypeError(msg)

                return cast("Callable[[T], None]", setter)

            case "attr":
                target = setter

                def set_attr(value: T) -> None:
                    setattr(target, key, value)

                return set_attr

            case "dict":
                if not isinstance(setter, dict):
                    msg = "El setter ha de ser un mapping en mode 'dict'."
                    raise TypeError(msg)

                mapping = cast("dict[str, T]", setter)

                def set_dict(value: T) -> None:
                    mapping[key] = value

                return set_dict


# ============================================================
# Ginys de tkinter
# ============================================================


class ButtonOptions(TypedDict):
    """Paràmetres amb clau que es permeten modificar d'un ttk.Button."""

    width: NotRequired[int]


def _add_button(
    func: partial[None],
    frame: ttk.Frame,
    set_value: tk.Variable,
    **kwargs: Unpack[ButtonOptions],
    ) -> ttk.Button:

    widget_options: ButtonOptions = {"width": 10, **kwargs}
    return ttk.Button(frame, textvariable=set_value, command=func, style="Custom.TButton", **widget_options)


def _add_checkbutton(func: partial[None], frame: ttk.Frame, set_value: tk.Variable) -> ttk.Checkbutton:
    return ttk.Checkbutton(frame, variable=set_value, command=func, style="Custom.TCheckbutton")


class ComboboxOptions(TypedDict):
    """Paràmetres amb clau que es permeten modificar d'un ttk.Combobox."""

    width: NotRequired[int]


def _add_combobox[T](
    func: partial[None],
    frame: ttk.Frame,
    set_value: tk.StringVar,
    options: dict[str, T],
    **kwargs: Unpack[ComboboxOptions],
) -> ttk.Combobox:

    widget_options: ComboboxOptions = {"width": 12, **kwargs}
    labels = list(options.keys())
    initial_key = next((k for k, v in options.items() if v == set_value.get()), labels[0]) if labels else ""

    display_var = tk.StringVar(frame, value=initial_key)
    combo = ttk.Combobox(frame, values=labels, state="readonly", textvariable=display_var, **widget_options)

    combo.bind("<<ComboboxSelected>>", lambda _: func(display_var.get()))

    return combo


def _add_colorcombobox(func: partial[None], frame: ttk.Frame, set_value: tk.StringVar) -> ttk.Button:
    value = mcolors.to_hex(set_value.get())

    style = ttk.Style()
    style_name = f"Color{id(frame)}.TButton"

    style.configure(style_name, background=value, borderwidth=1)
    style.map(style_name, background=[("active", value), ("pressed", value)])

    def open_palette() -> None:
        popup = tk.Toplevel(frame)
        popup.wm_overrideredirect(boolean=True)

        x = main_btn.winfo_rootx()
        y = main_btn.winfo_rooty() + main_btn.winfo_height()
        popup.geometry(f"+{x}+{y}")

        def select_color(color: str) -> None:
            set_value.set(color)

            style.configure(style_name, background=color)
            style.map(style_name, background=[("active", color), ("pressed", color)])

            popup.destroy()
            func()

        cols = 8

        for i, color in enumerate(PLOT_COLORS):
            row = i // cols
            col = i % cols

            btn = tk.Button(popup, bg=color, width=2, height=1, command=partial(select_color, color=color))
            btn.grid(row=row, column=col, padx=1, pady=1)

        popup.bind("<FocusOut>", lambda _: popup.destroy())
        popup.focus_set()

    main_btn = ttk.Button(frame, width=4, style=style_name, command=open_palette)

    return main_btn


class EntryOptions(TypedDict, total=False):
    """Paràmetres amb clau que es permeten modificar d'un ttk.Entry."""

    width: int
    justify: Literal["left", "right", "center"]
    state: Literal["normal", "disabled", "readonly"]


def _add_entry(
    func: partial[None],
    frame: ttk.Frame,
    set_value: tk.Variable,
    **kwargs: Unpack[EntryOptions],
) -> ttk.Entry:
    widget_options: EntryOptions = {"width": 18, **kwargs}

    entry = ttk.Entry(frame, textvariable=set_value, **widget_options)
    entry.bind("<Return>", lambda _: func())
    return entry


class RadioOptions(TypedDict):
    """Paràmetres amb clau que es permeten modificar d'un ttk.Radiobutton."""

    direction: NotRequired[Literal["h", "v"]]


def _add_radiobuttons[T](
    func: partial[None],
    frame: ttk.Frame,
    set_value: tk.Variable,
    options: dict[str, T],
    **kwargs: Unpack[RadioOptions],
) -> ttk.Frame:
    container = ttk.Frame(frame)

    widget_options: RadioOptions = {"direction": "v", **kwargs}
    direction = widget_options.pop("direction")

    for i, (text, value) in enumerate(options.items()):
        match direction:
            case "v":
                row, column = i, 0
            case "h":
                row, column = 0, i

        rb = ttk.Radiobutton(
            container,
            text=text,
            variable=set_value,
            value=value,
            command=func,
            style="Custom.TRadiobutton",
        )
        rb.grid(row=row, column=column, sticky="w")

    return container


class ScaleOptions(TypedDict, total=False):
    """Paràmetres amb clau que es permeten modificar d'un tk.Scale."""

    state: Literal["normal", "active", "disabled"]
    orient: Literal["horizontal", "vertical"]
    from_: float
    to: float
    resolution: float


def _add_scale(func: partial[None], frame: ttk.Frame, set_value: tk.IntVar | tk.DoubleVar,
               **kwargs: Unpack[ScaleOptions]) -> tk.Scale:

    widget_options: ScaleOptions = {
        "state": "normal",
        "orient": "horizontal",
        "from_": 0,
        "to": 100,
        "resolution": 1,
        **kwargs}

    return tk.Scale(frame, command=func, variable=set_value, **widget_options)


# ============================================================
# Barra de progrés
# ============================================================


class Progress:
    """Classe que crea una barra de progrés en una finestra flotant per a un procés executat i iteratiu."""

    def __init__(self, root: tk.Toplevel | tk.Tk, title: str = "Processant", maximum: float = 100) -> None:
        """Crea la finestra que conté la barra de progrés i inicialitza els paràmetres.

        Parameters
        ----------
        root: tk.Toplevel | tk.Tk
            Objecte al que se subordina la classe
        title: str = "Processant"
            Títol de la finestra
        maximum: float = 100
            Percentatge màxim de la barra progrés

        """
        self._root: tk.Toplevel | tk.Tk = root
        self._value: int = 0
        self._maximum: float = maximum
        self._last_percent: int = 0

        self._cancel_event: threading.Event = threading.Event()

        self._win: tk.Toplevel = tk.Toplevel(root)
        self._win.title(title)
        self._win.resizable(width=False, height=False)
        self._win.transient(self._root)
        self._win.lift()
        self._win.geometry("400x120")

        self._label: ttk.Label = ttk.Label(self._win, text="Preparant...", font=("Arial", 12))
        self._label.pack(pady=10)

        frame_barra: ttk.Frame = ttk.Frame(self._win)
        frame_barra.pack(fill="x", padx=20, pady=10)

        self._bar: ttk.Progressbar = ttk.Progressbar(frame_barra,
                                     style="Green.Horizontal.TProgressbar", mode="determinate")
        self._bar.pack(side="left", fill="x", expand=True)

        self._percent_label: ttk.Label = ttk.Label(frame_barra, text="0 %", width=5)
        self._percent_label.pack(side="right", padx=(10, 0))

        self._cancel_button: ttk.Button = ttk.Button(self._win, text="Cancel·lar", command=self.cancel)
        self._cancel_button.pack(anchor="e", padx=20, pady=5)

        self._bar["maximum"] = maximum

        self._win.protocol("WM_DELETE_WINDOW", self.cancel)

    def update(self) -> None:
        """Actualitza la barra de progrés cada 5% obtingut."""
        percent = int((self._value / self._maximum) * 100)

        percent = min(percent, 100)
        reported_percent = (percent // 5) * 5

        if reported_percent == self._last_percent:
            return

        self._last_percent = reported_percent

        def _update() -> None:
            if not self._win.winfo_exists():
                return

            self._bar["value"] = self._value
            self._percent_label.config(text=f"{reported_percent} %")
            self._label.config(text=f"Calculant: {self._value}/{self._maximum}")

        self._root.after(0, _update)

    def increment(self) -> None:
        """Indica que s'avança a la iteració següent."""
        self._value += 1
        self.update()

    def cancel(self) -> None:
        """Cancel·la el procés complet."""
        self._cancel_event.set()

        self._label.config(text="Cancel·lant...")
        self._cancel_button.config(state="disabled")

    def cancelled(self) -> bool:
        """Indica que el procés s'ha cancel·lat.

        Returns
        -------
        cancel: bool
            True si està cancel·lat, False si continua

        """
        return self._cancel_event.is_set()

    def finish(self, text: str = "Finalitzat ✔") -> None:
        """Indica que el procés s'ha completament exitosament.

        Parameters
        ----------
        text: str = "Finalitzat ✔"
            Text mostrat en finalitzar.

        """
        def _finish() -> None:
            if not self._win.winfo_exists():
                return

            self._label.config(text=text)
            self._cancel_button.config(state="disabled")
            self._win.after(500, self._win.destroy)

        self._root.after(0, _finish)
