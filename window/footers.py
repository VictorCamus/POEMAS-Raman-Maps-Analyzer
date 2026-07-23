from tkinter.ttk import Frame
from .labels import build_grid
from math import floor

class GestorFooterAFM:
    def __init__(self, filedata):
        self.filedata = filedata
        self.view = CrearFooterAFM(parent=filedata.frame, controller=self)

        self.filedata.canvas.mpl_connect('motion_notify_event', self.track_mouse)

    def track_mouse(self, event):
        if event.inaxes == self.filedata.axis:
            x_pixel, y_pixel = self.event_to_pixel(event)

            self.view.widgets['track_x'].value.set(x_pixel)
            self.view.widgets['track_y'].value.set(y_pixel)
            self.view.widgets['track_z'].value.set(float(f"{self.filedata.current_channel.Z[y_pixel - 1, x_pixel - 1]:.2f}"))

        else:
            for key in ['track_x', 'track_y', 'track_z']: self.view.widgets[key].value.set('')

    def event_to_pixel(self, event):
        x_pixel = floor(self.filedata.N[0] / self.filedata.midaBase[0] * event.xdata) + 1
        y_pixel = floor(self.filedata.N[1] / self.filedata.midaBase[1] * event.ydata) + 1
        return x_pixel, y_pixel

class CrearFooterAFM:
    def __init__(self, parent, controller):
        self.frame = Frame(parent)
        self.controller = controller
        self.channel = self.controller.filedata.current_channel

        self.frame.grid(row=4, column=0, sticky='ew', pady=5)
        self.frame.columnconfigure(0, weight = 1)
        self.frame.columnconfigure(8, weight = 1)

        self._trackers()

    def _trackers(self): # Afegeix controls per canviar el color del mapa i de l'escala.
        def _grid_track():
            channel = self.controller.filedata.current_channel

            return [
                (("track_x", str, None),
                 ("X:", 'entry', {"state": 'readonly'}),
                 (None, "args", {""})),
                (("track_y", str, None),
                 ("Y:", 'entry', {"state": 'readonly'}),
                 (None, "args", {})),
                (("track_z", str, None),
                 (f"{channel.name} ({channel.units}):", 'entry', {"state": 'readonly'}),
                 (None, "args", {})),
            ]

        self.widgets = build_grid(self.frame, _grid_track(), row=0, col=1, button=False, vertical = False)