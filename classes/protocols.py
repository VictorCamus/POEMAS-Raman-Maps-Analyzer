"""Protocols del projecte."""

from typing import TYPE_CHECKING, Literal, Protocol, TypedDict, overload

if TYPE_CHECKING:
    from collections.abc import Callable
    from tkinter import Event, Tk, Widget, ttk

    from matplotlib.backend_bases import MouseEvent, RendererBase
    from numpy import float32
    from numpy.typing import NDArray

    from classes.data import ChannelData, GeometryData, ObjectData
    from classes.views import FileView


type SpecUnits = Literal["nm", "eV", "1/cm"]
type ColorBool = Literal["k", "w"]
type InfSup = Literal["inf", "sup"]


class FileDataDict(TypedDict):
    """Diccionari estàndard necessari per a crear FileData."""

    channel: dict[str, ChannelData]
    geometry: GeometryData
    objects: ObjectData


class GestorProtocol(Protocol):
    """Protocol estàndard dels gestors de les pestanyes dels menús."""

    root: Tk
    notebook: NotebookProtocol
    files: dict[str, FileView]

    @property
    def current_file(self) -> FileView:
        """Retorna el fitxer actual, i no hi ha cap obert, dona error.

        Returns
        -------
        file: FileView
            Fitxer obert i mostrat en pantalla actualment

        Raises
        ------
        RuntimeError
            Si no hi ha cap fitxer obert

        """

    @current_file.setter
    def current_file(self, file: FileView | None) -> None:
        """Assigna un nou fitxer obert actual.

        Parameters
        ----------
        file: FileData
            Nou fitxer. Si no queden més fitxers, llavors és None

        """


class TkCanvasProtocol(Protocol):
    """Defineix la interfície del canvas de Matplotlib integrat en Tkinter."""

    def draw(self) -> None:
        """Redibuixa la figura immediatament."""

    def draw_idle(self) -> None:
        """Programa el redibuix de la figura quan el bucle gràfic estiga disponible."""

    def get_renderer(self) -> RendererBase:
        """Retorna el renderitzador utilitzat per dibuixar la figura."""

    def get_tk_widget(self) -> Widget:
        """Retorna el widget de Tkinter que conté el canvas."""

    def mpl_connect(self, s: str, func: Callable[[MouseEvent], object]) -> int:
        """Connecta una funció a un esdeveniment de Matplotlib i retorna el seu identificador."""


class NotebookProtocol(Protocol):
    """Defineix la interfície del notebook de pestanyes de Tkinter."""

    def add(self, child: Widget, **kw: object) -> None:
        """Afig un giny com a pestanya del notebook."""

    def bind(self, sequence: str, func: Callable[[Event[ttk.Notebook]], object]) -> str:
        """Vincula una funció a un esdeveniment del notebook."""

    def forget(self, tab_id: str | int | Widget) -> None:
        """Retira una pestanya del notebook sense destruir el giny."""

    def grid(self, **kwargs: object) -> None:
        """Col·loca el notebook amb el gestor de geometria grid."""

    def lift(self) -> None:
        """Eleva el notebook per damunt dels altres widgets del mateix nivell."""

    def lower(self) -> None:
        """Envia el notebook darrere dels altres widgets del mateix nivell."""

    def index(self, tab_id: str | int) -> int:
        """Retorna la posició d'una pestanya dins del notebook."""

    def insert(self, pos: int | str, child: Widget | str, **kw: object) -> None:
        """Inserix una pestanya en la posició indicada."""

    def pack(self, **kwargs: object) -> None:
        """Col·loca el notebook amb el gestor de geometria pack."""

    def select(self, tab_id: ttk.Frame | str | int | None = None) -> str:
        """Selecciona una pestanya o retorna la identificació de la seleccionada."""

    @overload
    def tab(self, tab_id: str | int, option: str) -> str: ...

    @overload
    def tab(self, tab_id: str | int, option: None = None) -> dict[str, object]: ...

    def tabs(self) -> tuple[str, ...]:
        """Retorna les identificacions de les pestanyes en l'ordre actual."""


class VariableProtocol[ValueT](Protocol):
    """Protocol per als objectes tk.Variable."""

    def get(self) -> ValueT:
        """Retorna el valor de l'objecte corresponent."""

    def set[T](self, value: ValueT) -> None:
        """Assigna un nou valor a l'objecte."""


class ParameterProtocol(Protocol):
    """Atributs que ha de contindre un objecte de tipus Parameter, d'lmfit."""

    name: str
    value: float
    stderr: float | None
    min: float
    max: float
    vary: bool


type ParametersProtocol = dict[str, ParameterProtocol]


class MinimizerProtocol(Protocol):
    """Atributs que ha tindre el retorn de la funció minimize d'lmfit."""

    success: bool
    params: ParametersProtocol


class BaselineProtocol(Protocol):
    """Funcions que ha de tindre la classe Baseline de pybaselines en el projecte."""

    def mixture_model(self, data: NDArray[float32], lam: float = 1e5) ->\
        tuple[NDArray[float32], dict[str, NDArray[float32]]]:
        """Calcula la línia base d'un espectre mitjançant un model de mescla."""
