from tkinter.ttk import Frame
from .labels import build_grid
from process.converter import coords_to_pixel

class FooterMap:
    def __init__(self, map_view):
        self.map = map_view
        self.view = ViewFooterMap(parent=self.map.model.content, controller=self)

        self.map.canvas.mpl_connect('motion_notify_event', self.track_mouse)

    @property
    def channel(self):
        return self.map.channel

    @property
    def frame(self):
        return self.view.frame

    def track_mouse(self, event):
        if event.inaxes == self.map.axis:
            x_pixel, y_pixel = coords_to_pixel([(event.xdata, event.ydata)], self.map.geometry.N, self.map.geometry.midaBase)[0]

            self.view.widgets['track_x'].value.set(x_pixel+1)
            self.view.widgets['track_y'].value.set(y_pixel+1)
            self.view.widgets['track_z'].value.set(float(f"{self.channel.Z[y_pixel, x_pixel]:.2f}"))

        else:
            for key in ['track_x', 'track_y', 'track_z']: self.view.widgets[key].value.set('')

class ViewFooterMap:
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
                 ("X:", 'entry', {"state": 'readonly'})),
                (("track_y", str, None),
                 ("Y:", 'entry', {"state": 'readonly'})),
                (("track_z", str, None),
                 (f"{self.channel.name} ({self.channel.units}):", 'entry', {"state": 'readonly'}))
            ]

        self.widgets = build_grid(self.frame, _grid_track(), row=0, col=1, button=False, vertical = False)

class FooterSpec:
    def __init__(self, spec_view):
        self.spec = spec_view
        self.view = ViewFooterSpec(parent=self.spec.model.content, controller=self)

        self.spec.canvas.mpl_connect('motion_notify_event', self.track_mouse)

    @property
    def channel(self):
        return self.spec.channel

    @property
    def frame(self):
        return self.view.frame

    def track_mouse(self, event):
        if event.inaxes == self.spec.axis:
            self.view.widgets['track_x'].value.set(round(event.xdata, 2))
            self.view.widgets['track_y'].value.set(int(event.ydata))

        else:
            for key in ['track_x', 'track_y']: self.view.widgets[key].value.set('')

class ViewFooterSpec:
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
                 (f"λ (nm):", 'entry', {"state": 'readonly'})),
                (("track_y", str, None),
                 ("Intensity (cts):", 'entry', {"state": 'readonly'}))
            ]

        self.widgets = build_grid(self.frame, _grid_track(), row=0, col=1, button=False, vertical = False)