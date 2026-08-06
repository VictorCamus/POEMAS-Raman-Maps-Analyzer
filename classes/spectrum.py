from numpy import nanmax

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from drawing.plots import base_plot
from window.footers import GestorFooterSpectrum
from window.headers import GestorHeaderSpectrum
from process import images as zoom

class SpectrumView:
    def __init__(self, model):
        self.model = model

        self.header = GestorHeaderSpectrum(self)
        self.figure, self.axis = base_plot(xtitle = 'λ (nm)', ytitle = 'Intensity (cts)')
        self.figure.subplots_adjust(left=0.2, right=0.95, bottom=0.2, top=0.8)
        self.canvas = FigureCanvasTkAgg(self.figure, self.model.content)
        widget = self.canvas.get_tk_widget()
        widget.config(bg="#2e2e2e", highlightthickness=0, bd=0)

        self.footer = GestorFooterSpectrum(self)

        self.header.view.frame.grid(row=0, column=1)
        self.header.view.frame.grid_configure(pady=5)
        widget.grid(row=1, column=1, sticky="nsew")
        self.footer.view.frame.grid(row=2, column=1)
        self.footer.view.frame.grid_configure(pady=5)

        self.line = None

        self.canvas.mpl_connect("key_press_event", lambda e: zoom.copy_figure(self.figure) if e.key == "ctrl+c" else None)

    @property
    def channel(self):
        return self.model.channel

    @property
    def geometry(self):
        return self.model.geometry

    def plot_pixel(self, px, py):
        ch = self.channel
        spec = ch.spectra[py, px]
        view = self.header.view

        if self.line is None:
            self.line, = self.axis.plot(ch.xdata["nm"], spec, color="b")
            view.widgets_ylim["bottom"].value.set(0)
            self.axis.set_xlim(view.widgets_xlim["left"].value.get(), view.widgets_xlim["right"].value.get())
            self.axis.set_ylim(bottom = 0)
        else:
            self.line.set_ydata(spec)
            top = int(1.1*nanmax(spec))
            self.axis.set_ylim(top = top)
            view.widgets_ylim["top"].value.set(top)

        self.axis.set_title(f"X={px + 1} Y={py+1}", fontsize = 16, pad = 10)
        self.canvas.draw_idle()