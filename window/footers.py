from tkinter.ttk import Frame
from .widgets import Widget
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

            self.view.widgets['track_x'].set(x_pixel+1)
            self.view.widgets['track_y'].set(y_pixel+1)
            self.view.widgets['track_z'].set(float(f"{self.channel.Z[y_pixel, x_pixel]:.2f}"))

        else:
            for key in ['track_x', 'track_y', 'track_z']: self.view.widgets[key].set('')

class ViewFooterMap:
    def __init__(self, parent, controller):
        self.controller = controller

        self.frame = Frame(parent)
        self.frame.columnconfigure(0, weight=1)

        self._create_widgets()

    @property
    def channel(self):
        return self.controller.channel

    def _create_widgets(self): # Afegeix controls per canviar el color del mapa i de l'escala.
        self.widgets = {
            'track_x': Widget(key='track_x', var_type=str,
                       text="X", widget='entry', widget_kwargs={"state": 'readonly', "width": 10}),
            'track_y': Widget(key='track_y', var_type=str,
                       text="Y", widget='entry', widget_kwargs={"state": 'readonly', "width": 10}),
            'track_z': Widget(key='track_z', var_type=str,
                       text=f"{self.channel.name} ({self.channel.units})", widget='entry', widget_kwargs={"state": 'readonly', "width": 10})}

        for i, widget in enumerate(self.widgets.values()): widget.add(self.frame, row = 0, col = 2*i + 1)

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
            self.view.widgets['track_x'].set(round(event.xdata, 2))
            self.view.widgets['track_y'].set(int(event.ydata))

        else:
            for key in ['track_x', 'track_y']: self.view.widgets[key].set('')

class ViewFooterSpec:
    def __init__(self, parent, controller):
        self.controller = controller

        self.frame = Frame(parent)
        self.frame.columnconfigure(0, weight=1)

        self._create_widgets()

    @property
    def channel(self):
        return self.controller.channel

    def _create_widgets(self): # Afegeix controls per canviar el color del mapa i de l'escala.
        self.widgets = {
            'track_x': Widget(key='track_x', var_type=str,
                              text=self.controller.spec.xlabels[self.channel.spectra.units], widget='entry', widget_kwargs={"state": 'readonly', "width": 10}),
            'track_y': Widget(key='track_y', var_type=str,
                              text="Intensity (cts)", widget='entry', widget_kwargs={"state": 'readonly', "width": 10}),
            'laser': Widget(key='laser', var_type=str, init=self.controller.spec.model.controller.objects.laser,
                           text='λ₀ (nm):', widget='entry', widget_kwargs={"state": 'readonly', "width": 10})}

        for i, widget in enumerate(self.widgets.values()): widget.add(self.frame, row = 0, col = 2*i + 1)