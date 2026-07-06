import numpy as np
from math import floor

from matplotlib.patheffects import withStroke
from matplotlib.patches import FancyArrowPatch
from process import perfil as prf

class FletxaBase:
    def __init__(self, ax, start, end, mida, text, color):
        self.ax = ax
        self.start = start
        self.end = end
        self.mida = mida
        self.text = text
        self.color = color

        self.arrow = None
        self.text_obj = None
        self.background = None  # Per blitting

    def dibuixa(self):
        if self.start is None or self.end is None:
            return  # No dibuixem fins que hi hagi coordenades vàlides

        if self.arrow is None: self._crear_fletxa()
        else: self._actualitzar_fletxa()

    def elimina(self):
        if self.arrow:
            self.arrow.remove()
            self.arrow = None

        if self.text_obj:
            self.text_obj.remove()
            self.text_obj = None

        self.ax.figure.canvas.draw_idle()

    def desconnecta(self):
        canvas = self.ax.figure.canvas
        if hasattr(self, "cid_click"):
            canvas.mpl_disconnect(self.cid_click)
        if hasattr(self, "cid_move"):
            canvas.mpl_disconnect(self.cid_move)

    def _actualitzar_fletxa(self):
        if self.background is None:
            return  # Esperem que la fletxa inicial sigui creada

        canvas = self.ax.figure.canvas
        canvas.restore_region(self.background)

        xp1, yp1 = self.start
        xp2, yp2 = self.end
        self.arrow.set_positions((xp1, yp1), (xp2, yp2))

        text_x, text_y, angle = self._calcular_text()
        self.text_obj.set_position((text_x, text_y))
        self.text_obj.set_rotation(angle)

        self.ax.draw_artist(self.arrow)
        self.ax.draw_artist(self.text_obj)
        canvas.blit(self.ax.bbox)

    def _calcular_text(self):
        xp1, yp1 = self.start
        xp2, yp2 = self.end

        dx, dy = xp2 - xp1, yp2 - yp1
        length = np.hypot(dx, dy)

        if dx == 0:
            angle = 90 if dy > 0 else -90
        else:
            angle = np.degrees(np.arctan(dy / dx))

        modmid = np.hypot(*self.mida)
        d = 0.02 * modmid

        if length > 0:
            text_x = (xp2 + xp1) / 2 + d * dy / length
            text_y = (yp2 + yp1) / 2 - d * dx / length
        else:
            text_x = (xp2 + xp1) / 2
            text_y = (yp2 + yp1) / 2

        return text_x, text_y, angle

    def _crear_fletxa(self):
        if self.start is None or self.end is None: return

        self.background = self.ax.figure.canvas.copy_from_bbox(self.ax.bbox) # Guarda el background.

        text_x, text_y, angle = self._calcular_text()

        self.arrow = FancyArrowPatch(
            posA=self.start,
            posB=self.end,
            arrowstyle='-|>',
            linewidth=3,
            color=self.color,
            mutation_scale=15,
            path_effects=[withStroke(linewidth=6, foreground='black')]
        )
        
        self.ax.add_patch(self.arrow)

        self.text_obj = self.ax.text(
            text_x,
            text_y,
            self.text,
            rotation=angle,
            color=self.color,
            fontsize=15,
            fontweight='bold',
            va='center',
            ha='center',
            path_effects=[withStroke(linewidth=4, foreground='black')]
        )

class FletxaInteractiva(FletxaBase):

    def __init__(self, ax, Z, text, mida, color="r", on_fletxa_finalitzada=None):
        super().__init__(ax, None, None, mida, text, color)

        self.Z = Z
        self.Ny, self.Nx = Z.shape
        self.midaX, self.midaY = mida

        self.stop = False
        self.on_fletxa_finalitzada = on_fletxa_finalitzada

        canvas = ax.figure.canvas
        self.cid_click = canvas.mpl_connect("button_press_event", self.on_click)
        self.cid_move = canvas.mpl_connect("motion_notify_event", self.on_motion)

        self.ax.set_autoscale_on(False)

    def _snap_to_pixel(self, xdata, ydata):
        col = int(round(xdata * self.Nx / self.midaX))
        row = int(round(ydata * self.Ny / self.midaY))

        if col < 0 or col >= self.Nx or row < 0 or row >= self.Ny:
            return None

        x_phys = (col + 0.5) * self.midaX / self.Nx
        y_phys = (row + 0.5) * self.midaY / self.Ny
        return x_phys, y_phys

    def on_click(self, event):
        if event.inaxes != self.ax or self.stop:
            return

        point = self._snap_to_pixel(event.xdata, event.ydata)
        if point is None:
            return

        if self.start is None:
            self.start = point
            self.end = point  # assignem provisionalment la mateixa posició
            self._crear_fletxa()  # dibuixar fletxa inicial sense blitting
            return

        self.end = point
        self.stop = True
        self.dibuixa()
    # si cal, cridar on_fletxa_finalitzada

        if self.on_fletxa_finalitzada:
            p1, p2 = self._calcular_pixels()
            get_line = prf.get_line(p1, p2)
            get_length = np.hypot(
                self.end[0] - self.start[0],
                self.end[1] - self.start[1]
            )

            self.on_fletxa_finalitzada(
                get_line,
                get_length,
                self.start,
                self.end
            )

            self.desconnecta()

    def on_motion(self, event):
        if (
            self.start is None
            or self.stop
            or event.inaxes != self.ax
            or event.xdata is None
            or event.ydata is None
        ):
            return

        end = self._snap_to_pixel(event.xdata, event.ydata)
        if end is None:
            return

        self.end = end
        self._actualitzar_fletxa()

    def _calcular_pixels(self):
        p1 = [floor(self.start[0] * self.Nx / self.midaX), floor(self.start[1] * self.Ny / self.midaY)]
        p2 = [floor(self.end[0] * self.Nx / self.midaX), floor(self.end[1] * self.Ny / self.midaY)]
        return p1, p2

class FletxaEstatica(FletxaBase):
    def __init__(self, ax, lims, mida, text, color):
        start, end = lims
        super().__init__(ax, start, end, mida, text, color)
        self.dibuixa()  # Dibuixa la fletxa un cop
