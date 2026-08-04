from tkinter.ttk import Frame
from .labels import build_grid
from math import floor

class GestorFooterAFM:
    def __init__(self, map_view):
        self.map = map_view
        self.view = CrearFooterAFM(parent=self.map.frame, controller=self)

        self.map.canvas.mpl_connect('motion_notify_event', self.track_mouse)

    @property
    def channel(self):
        return self.map.channel

    def track_mouse(self, event):
        if event.inaxes == self.map.axis:
            x_pixel, y_pixel = self.event_to_pixel(event)

            self.view.widgets['track_x'].value.set(x_pixel)
            self.view.widgets['track_y'].value.set(y_pixel)
            self.view.widgets['track_z'].value.set(float(f"{self.channel.Z[y_pixel - 1, x_pixel - 1]:.2f}"))

        else:
            for key in ['track_x', 'track_y', 'track_z']: self.view.widgets[key].value.set('')

    def event_to_pixel(self, event):
        geo = self.map.geometry
        x_pixel = floor(geo.N[0] / geo.midaBase[0] * event.xdata) + 1
        y_pixel = floor(geo.N[1] / geo.midaBase[1] * event.ydata) + 1
        return x_pixel, y_pixel

class CrearFooterAFM:
    def __init__(self, parent, controller):
        self.controller = controller

        self.frame = Frame(parent)
        self.frame.columnconfigure(0, weight=1)

        self._trackers()

    @property
    def channel(self):
        return self.controller.channel

    def _trackers(self): # Afegeix controls per canviar el color del mapa i de l'escala.
        def _grid_track():

            return [
                (("track_x", str, None),
                 ("X:", 'entry', {"state": 'readonly'}),
                 (None, "args", {""})),
                (("track_y", str, None),
                 ("Y:", 'entry', {"state": 'readonly'}),
                 (None, "args", {})),
                (("track_z", str, None),
                 (f"{self.channel.name} ({self.channel.units}):", 'entry', {"state": 'readonly'}),
                 (None, "args", {})),
            ]

        self.widgets = build_grid(self.frame, _grid_track(), row=0, col=1, button=False, vertical = False)