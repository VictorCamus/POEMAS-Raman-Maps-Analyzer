"""Classes que determinen el funcionament de les fletxes gràfiques."""

from typing import TYPE_CHECKING

import numpy as np
from matplotlib.patches import FancyArrowPatch
from matplotlib.patheffects import withStroke

from process.converter import pixel_center

if TYPE_CHECKING:
    from collections.abc import Callable

    from matplotlib.axes import Axes
    from matplotlib.backend_bases import MouseEvent
    from matplotlib.text import Text


class FletxaBase:
    """Classe base per a la creació de fletxes com a objectes visuals del mapa."""

    def __init__(self, axis: Axes, start: tuple[float, float] | None, end: tuple[float, float] | None,
                base_size: tuple[float, float], text: str, color: str) -> None:
        """Creació de la fletxa base.

        axis: Axes
            Objecte eix de Matplotlib
        start: tuple[float, float] | None
            Punt inicial de la fletxa. Si és None, no es crea encara (cas de FletxaInteractiva)
        end: tuple[float, float] | None
            Punt final de la fletxa. Si és None, no es crea encara (cas de FletxaInteractiva)
        base_size: tuple[float, float]
            Mida base de la figura
        text: str
            Número al centre de la fletxa
        color: str
            Color del perfil

        """
        self.axis = axis
        self.start = start
        self.end = end
        self.base_size = base_size
        self.text = text
        self.color = color

        if self.start is not None and self.end is not None:
            self.create(self.start, self.end)

    def create(self, start: tuple[float, float], end: tuple[float, float]) -> None:
        """Creació de l'objecte fletxa i el text corresponent.

        Parameters
        ----------
        start: tuple[float, float]
            Punt inicial de la fletxa
        end: tuple[float, float]
            Punt final de la fletxa

        """
        self.start = start
        self.end = end

        pos, angle = self._text_position(start, end, self.base_size)

        self.arrow: FancyArrowPatch = FancyArrowPatch(posA=start, posB=end, arrowstyle="-|>", linewidth=3,
                                                      color=self.color, mutation_scale=15,
                                                      path_effects=[withStroke(linewidth=6, foreground="black")])

        self.axis.add_patch(self.arrow)

        self.text_obj: Text = self.axis.text(
            pos[0],
            pos[1],
            self.text,
            rotation=angle,
            color=self.color,
            fontsize=15,
            fontweight="bold",
            va="center",
            ha="center",
            path_effects=[withStroke(linewidth=4, foreground="black")],
        )

    def update(self, start: tuple[float, float], end: tuple[float, float]) -> None:
        """S'actualitza la nova posició de la fletxa i del text.

        Parameters
        ----------
        start: tuple[float, float]
            Punt inicial de la fletxa
        end: tuple[float, float]
            Punt final de la fletxa

        """
        self.start = start
        self.end = end
        self.arrow.set_positions(posA=self.start, posB=self.end)

        pos, angle = self._text_position(start, end, self.base_size)
        self.text_obj.set_position(pos)
        self.text_obj.set_rotation(angle)

        self.axis.figure.canvas.draw_idle()

    def delete(self) -> None:
        """S'elimina la fletxa i la referència de text associada."""
        self.arrow.remove()
        self.text_obj.remove()

    @staticmethod
    def _text_position(start: tuple[float, float], end: tuple[float, float],
                       base_size: tuple[float, float]) -> tuple[tuple[float, float], float]:
        """Calcula i retorna la posició i l'angle del número de la fletxa corresponent que serveix com a referència.

        Parameters
        ----------
        start: tuple[float, float]
            Extrem inicial de la fletxa
        end: tuple[float, float]
            Extrem final de la fletxa
        base_size: tuple[float, float]
            Mida base de la imatge

        Returns
        -------
        pos: tuple[float, float]
            Posició del text
        angle: float
            Angle que forma el text respecte l'eix horitzontal.

        """
        xp1, yp1 = start
        xp2, yp2 = end

        dx, dy = xp2 - xp1, yp2 - yp1
        length = float(np.hypot(dx, dy))

        angle = (float(90) if dy > 0 else float(-90)) if dx == 0 else float(np.degrees(np.arctan(dy / dx)))
        modmid = float(np.hypot(*base_size))
        d = 0.02 * modmid

        pos = (xp2 + xp1) / 2, (yp2 + yp1) / 2
        if length != 0:
            pos = pos[0] + d * dy / length, pos[1] - d * dx / length

        return pos, angle


class FletxaInteractiva(FletxaBase):
    """Creació de fletxes interactives."""

    def __init__(self, axis: Axes, dim: tuple[int, int], base_size: tuple[float, float], text: str, color: str,
                 on_fletxa_finalitzada: Callable[[], None]) -> None:
        """S'hereta l'inici de FletxaBase i s'activen les funcions interactives.

        Parameters
        ----------
        axis: Axes
            Objecte eix de Matplotlib.
        dim: tuple[int, int]
            Dimensions de la figura.
        base_size: tuple[float, float]
            Mida base de la figura
        text: str
            Número al centre de la fletxa
        color: str
            Color del perfil
        on_fletxa_finalitzada: Callable[[], None],
            Funció que s'executa en fer el segon clic.

        """
        super().__init__(axis, None, None, base_size, text, color)

        self.dim: tuple[int, int] = dim

        self.stop: bool = False
        self.on_fletxa_finalitzada = on_fletxa_finalitzada

        canvas = axis.figure.canvas
        self.cid_click: int = canvas.mpl_connect("button_press_event", self._on_click)
        self.cid_move: int = canvas.mpl_connect("motion_notify_event", self._on_motion)

    def _on_click(self, event: MouseEvent) -> None:
        """En el primer clic, inicia la fletxa. En el segon, la fixa a la imatge i guarda el perfil.

        Parameters
        ----------
        event: MouseEvent
            Interacció del ratolí sobre la imatge

        """
        if (event.inaxes != self.axis or self.stop
           or event.xdata is None or event.ydata is None):
            return

        point = pixel_center([(event.xdata, event.ydata)], self.dim, self.base_size)[0]

        if self.start is None or self.end is None:
            self.create(point, point)
            return

        self.stop = True
        self.update(self.start, point)

        self._disconnect()
        self.on_fletxa_finalitzada()

    def _on_motion(self, event: MouseEvent) -> None:
        """Actualitza la fletxa mentre es mou el ratolí.

        Parameters
        ----------
        event: MouseEvent
            Interacció del ratolí sobre la imatge

        """
        if (self.start is None or self.stop or event.inaxes != self.axis
            or event.xdata is None or event.ydata is None):
            return

        end = pixel_center([(event.xdata, event.ydata)], self.dim, self.base_size)[0]

        self.end = end
        self.update(self.start, self.end)

    def _disconnect(self) -> None:
        """Desactiva les interaccions de la fletxa una vegada s'ha creada."""
        canvas = self.axis.figure.canvas
        canvas.mpl_disconnect(self.cid_click)
        canvas.mpl_disconnect(self.cid_move)
