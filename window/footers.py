"""Classes que creen i controlen els peus de figura de l'aplicació."""

from abc import ABC, abstractmethod
from tkinter.ttk import Frame
from typing import TYPE_CHECKING, TypedDict

from process.converter import coords_to_pixel

from .widgets import Widget

if TYPE_CHECKING:
    from matplotlib.backend_bases import MouseEvent

    from classes.views import FigureView, MapView, SpecView  # ruff: ignore[unused-import]
    from window.widgets import GenericWidgets


class Footer[TView: FigureView](Frame, ABC):
    """Classe base general d'un peu de figura."""

    widgets: GenericWidgets

    def __init__(self, view: TView) -> None:
        """Crea els ginys i connecta les interaccions de passada de ratolí sobre la figura corresponent."""
        super().__init__(view.file.content)

        self.view = view
        self.widgets: dict[str, Widget[str]]

        self._create_widgets()

        self.view.canvas.mpl_connect("motion_notify_event", self._track_mouse)

    @abstractmethod
    def _track_mouse(self, event: MouseEvent) -> None:
        """Indica els valors de la figura en els ginys del peu.

        Parameters
        ----------
        event: MouseEvent
            Interacció del ratolí amb la figura

        """

    @abstractmethod
    def _create_widgets(self) -> None:
        """Crea els ginys i els col·loca dins del peu de la figura."""


class FooterMapWidgets(TypedDict):
    """Ginys principals dels peus de figura."""

    track_x: Widget[str]
    track_y: Widget[str]
    track_z: Widget[str]


class FooterMap(Footer["MapView"]):
    """Controla el peu de figura dels mapes."""

    widgets: FooterMapWidgets

    def _track_mouse(self, event: MouseEvent) -> None:
        if event.xdata is None or event.ydata is None or event.inaxes != self.view.axis:
            self.widgets["track_x"].set(None)
            self.widgets["track_y"].set(None)
            self.widgets["track_z"].set(None)
            return

        x_pixel, y_pixel = coords_to_pixel([(event.xdata, event.ydata)],
        self.view.file.geometry.dim, self.view.file.geometry.base_size)[0]

        self.widgets["track_x"].set(f"{x_pixel + 1}")
        self.widgets["track_y"].set(f"{y_pixel + 1}")
        self.widgets["track_z"].set(f"{self.view.channel.data[y_pixel, x_pixel]:.3f}")

    def _create_widgets(self) -> None:  # Afegeix controls per canviar el color del mapa i de l'escala.
        self.widgets = {
            "track_x": Widget(
                key="track_x",
                var_type=str,
                text="X",
                widget="entry",
                widget_kwargs={"state": "readonly", "width": 10},
            ),
            "track_y": Widget(
                key="track_y",
                var_type=str,
                text="Y",
                widget="entry",
                widget_kwargs={"state": "readonly", "width": 10},
            ),
            "track_z": Widget(
                key="track_z",
                var_type=str,
                text=f"{self.view.channel.name} ({self.view.channel.units})",
                widget="entry",
                widget_kwargs={"state": "readonly", "width": 10},
            ),
        }

        for i, widget in enumerate(self.widgets.values()):
            if not isinstance(widget, Widget):
                msg = "La variable donada no és un objecte de tipus Widget."
                raise TypeError(msg)

            widget.add(self, row=0, col=2 * i + 1)


class FooterSpecWidgets(TypedDict):
    """Ginys principals dels peus de figura."""

    track_x: Widget[str]
    track_y: Widget[str]
    laser: Widget[float]


class FooterSpec(Footer["SpecView"]):
    """Controla el peu de figura dels espectres."""

    widgets: FooterSpecWidgets

    def _track_mouse(self, event: MouseEvent) -> None:
        if event.xdata is None or event.ydata is None or event.inaxes != self.view.axis:
            self.widgets["track_x"].set(None)
            self.widgets["track_y"].set(None)
            return

        self.widgets["track_x"].set(f"{event.xdata:.3f}")
        self.widgets["track_y"].set(f"{event.ydata}")

    def _create_widgets(self) -> None:  # Afegeix controls per canviar el color del mapa i de l'escala.
        self.widgets = {
            "track_x": Widget(
                key="track_x",
                var_type=str,
                text=self.view.xlabels[self.view.channel.spec.units],
                widget="entry",
                widget_kwargs={"state": "readonly", "width": 10},
            ),
            "track_y": Widget(
                key="track_y",
                var_type=str,
                text="Intensity (cts)",
                widget="entry",
                widget_kwargs={"state": "readonly", "width": 10},
            ),
            "laser": Widget(
                key="laser",
                var_type=float,
                init=self.view.channel.spec.laser,
                text="λ₀ (nm):",
                widget="entry",
                widget_kwargs={"state": "readonly", "width": 10},
            ),
        }

        for i, widget in enumerate(self.widgets.values()):
            if not isinstance(widget, Widget):
                msg = "La variable donada no és un objecte de tipus Widget."
                raise TypeError(msg)

            widget.add(self, row=0, col=2 * i + 1)
