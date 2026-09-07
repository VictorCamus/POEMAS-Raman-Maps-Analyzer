from tkinter import Button, filedialog, Frame
from pathlib import Path
import numpy as np

from window import BaseFigureWindow
from window.widgets import Widget
from process.statistics import hist, boxplot, remove_boxplot
from .base import BaseMenu

class GestorEstadistica(BaseMenu):  # Classe que gestiona les accions relacionades amb els perfils de fletxes.
    ordre = 50 # Atribut per a ordenar els menús (opcional)
    
    def __init__(self, app):
        super().__init__(app)  # Inicialitza la classe base

    def registrar_menu(self, menu):
        accions = [
            ('Mostrar histogrames', lambda: self.obrir_classe(Histogrames), None),
            ('Mitjana direccional', lambda: self.obrir_classe(DirectionMean), None)
        ]
        
        self.create_menu("Estadística", menu, accions)  # Crida a la funció comuna d'afegir menú

    def obrir_classe(self, classe):
        if not self.comprova_fitxer(): return
        classe(self)

class Histogrames(BaseFigureWindow):
    def __init__(self, gestor):
        super().__init__(gestor, "Mostrar histogrames")
        
        self.mode = "Hist"
        self.actualitza_plot()

        buttons = Frame(self.fig_frame)
        buttons.pack(anchor="center", pady=5)

        btn_prev = Button(buttons, text="◀", command = self.toggle_plot, font=("Arial", 16))
        btn_prev.pack(side="left", padx=2)

        btn_next = Button(buttons, text="▶", command = self.toggle_plot, font=("Arial", 16))
        btn_next.pack(side="left", padx=2)

    @property
    def data(self):
        mask = (self.lims[0] < self._data) & (self._data < self.lims[1])
        return self._data[mask]

    @property
    def nbins(self):
        return self.widgets['nbins'].get()

    @property
    def color(self):
        return self.widgets['cb_color'].value.get()

    def plot_file(self, value):
        self.file = value
        self.set_widgets()
        
    def plot_channel(self, value):
        self.channel = value
        self.set_widgets()

    def plot_lims(self, inf=None, sup=None):
        if inf is not None: self.lims = (inf, self.lims[1])
        if sup is not None: self.lims = (self.lims[0], sup)

        self.actualitza_plot()

    def plot_remove(self):
        match self.mode:
            case "Hist": self.plot.remove()
            case "Box": remove_boxplot(self.plot)

        delattr(self, 'plot')

    def plot_color(self, value):
        match self.mode:
            case "Hist": self.plot.set_color(value)
            case "Box": 
                for element in self.plot['boxes']: element.set_facecolor(value)
        
        self.figure.canvas.draw()
    
    def toggle_plot(self):
        self.plot_remove()

        match self.mode:
            case "Hist":
                self.mode = "Box"
                self.widgets['nbins'].config(state = 'disabled')
            case "Box":
                self.mode = "Hist"
                self.widgets['nbins'].config(state = 'normal')

        self.actualitza_plot()
    
    def actualitza_plot(self, value = None):
        if hasattr(self, "plot"): self.plot_remove()

        match self.mode:
            case "Hist":
                self.plot, self.hist_data, _ = hist(self.axis, self.data, self.lims, nbins = self.nbins, xlabel=self.channel.ax_title, color=self.color)
            case "Box":
                self.plot = boxplot(self.axis, self.data, self.lims, name=self.channel.name, ylabel=self.channel.ax_title, color=self.color)

        self.figure.tight_layout()
        self.figure.tight_layout()
        self.figure.canvas.draw_idle()
    
    def guardar(self, value):
        ruta = filedialog.asksaveasfilename(
            parent = self.main_frame,
            defaultextension=".png",
            initialfile=f"{self.file.name} - {self.channel.name} {self.mode}.png",
            filetypes=[("PNG", "*.png")]
        )

        if ruta: 
            self.figure.savefig(ruta)
            p = Path(ruta)
            txt_ruta = p.with_name(f"{self.file.name} - {self.channel.name} Data.txt")

            with open(txt_ruta, "w", encoding="utf-8") as f:
                for item in self.widgets.values():
                    if item.widget_type == "entry" and item.widget.cget("state") == "readonly":
                        f.write(f"{item.label.cget('text'):<30} {item.value.get():>10}\n")

                f.write("\n")
                f.write(f"{'Bin':<10}{'Count':<8}\n")

                for bin_, count in self.hist_data:
                    f.write(f"{bin_:<10.2f}{count:<8.5f}\n")

    def set_widgets(self):
        mean, std, skew, kurt, lw, q1, q2, q3, tw = self.compute_stats()
        self.widgets['mean'].value.set(round(mean, 3))
        self.widgets['stderr'].value.set(round(std, 3))
        self.widgets['skewness'].value.set(round(skew, 3))
        self.widgets['kurtosis'].value.set(round(kurt, 3))
        self.widgets['q1'].value.set(round(q1, 3))
        self.widgets['q2'].value.set(round(q2, 3))
        self.widgets['q3'].value.set(round(q3, 3))
        self.widgets['lower'].value.set(round(lw, 3))
        self.widgets['upper'].value.set(round(tw, 3))
        self.widgets['inf'].value.set(round(self.lims[0], 3))
        self.widgets['sup'].value.set(round(self.lims[1], 3))
        
        self.actualitza_plot()
    
    def compute_stats(self):
        x0, x1, y0, y1 = self.file.geometry.limit_pixels()
        data = self.channel.Z[y0:y1, x0:x1].ravel()
        data = data[np.isfinite(data)]

        mean = data.mean()
        std = data.std()

        if std == 0: skew = kurt = 0
        else:
            norm = (data - mean) / std
            skew = (norm**3).mean()
            kurt = (norm**4).mean()

        lw, q1, q2, q3, tw = np.percentile(data, [5, 25, 50, 75, 95])
        
        self.lims = (np.percentile(data, 0.5), np.percentile(data, 99.5))
        self._data = data

        return mean, std, skew, kurt, lw, q1, q2, q3, tw

    def _create_widgets(self):
        files = list(self.files.keys())
        channels = list(self.file.channel.keys())
        mean, std, skew, kurt, lw, q1, q2, q3, tw = self.compute_stats()

        self.widgets = {
            "file": Widget(key="file", var_type=str, init=self.file.name,
                       text="Arxiu:", widget="cb", widget_kwargs={"options": files},
                       setter=self.plot_file),

            "channel": Widget(key="channel", var_type=str, init=self.channel.name,
                              text="Canal:", widget="cb", widget_kwargs={"options": channels},
                              setter=self.plot_channel),

            "cb_color": Widget(key="cb_color", var_type=str, init="blue",
                               text="Color de l'histograma:", widget="colorcb",
                               setter=self.plot_color),

            "inf": Widget(key="inf", var_type=float, init=round(self.lims[0], 3),
                          text="Límit inferior:", widget="entry",
                          setter=self.plot_lims, mode="kwargs"),

            "sup": Widget(key="sup", var_type=float, init=round(self.lims[1], 3),
                          text="Límit superior:", widget="entry",
                          setter=self.plot_lims, mode="kwargs"),

            "nbins": Widget(key="nbins", var_type=int, init=50,
                   text="Nombre de barres:", widget="entry",
                   setter=self.actualitza_plot, mode="args"),

            "mean": Widget(key="mean", var_type=float, init=round(mean, 3),
                           text="Mitjana:", widget="entry", widget_kwargs={"state": "readonly"},
                           setter=self, mode="attr"),

            "stderr": Widget(key="stderr", var_type=float, init=round(std, 3),
                             text="Desviació estàndard RMS:", widget="entry", widget_kwargs={"state": "readonly"},
                             setter=self, mode="attr"),

            "skewness": Widget(key="skewness", var_type=float, init=round(skew, 3),
                               text="Asimetria:", widget="entry", widget_kwargs={"state": "readonly"},
                               setter=self, mode="attr"),

            "kurtosis": Widget(key="kurtosis", var_type=float, init=round(kurt, 3),
                               text="Curtosi:", widget="entry", widget_kwargs={"state": "readonly"},
                               setter=self, mode="attr"),

            "lower": Widget(key="lower", var_type=float, init=round(lw, 3),
                            text="Llindar inferior (5%):", widget="entry", widget_kwargs={"state": "readonly"},
                            setter=self, mode="attr"),

            "q1": Widget(key="q1", var_type=float, init=round(q1, 3),
                         text="Primer quartil (25%):", widget="entry", widget_kwargs={"state": "readonly"},
                         setter=self, mode="attr"),

            "q2": Widget(key="q2", var_type=float, init=round(q2, 3),
                         text="Mediana (50%):", widget="entry", widget_kwargs={"state": "readonly"},
                         setter=self, mode="attr"),

            "q3": Widget(key="q3", var_type=float, init=round(q3, 3),
                         text="Tercer quartil (75%):", widget="entry", widget_kwargs={"state": "readonly"},
                         setter=self, mode="attr"),

            "upper": Widget(key="upper", var_type=float, init=round(tw, 3),
                            text="Llindar superior (95%):", widget="entry", widget_kwargs={"state": "readonly"},
                            setter=self, mode="attr"),

            "save": Widget(key="save", var_type=str, init="Guardar",
                           text="Guardar dades i imatge:", widget="button",
                           setter=self.guardar)}

class DirectionMean(BaseFigureWindow):
    def __init__(self, gestor):
        self._direction = True
        self._units = True
        self._freq = 0.5
        super().__init__(gestor, "Mostrar mitjana direccional", dim=(6,4))

        self.plot, = self.axis.plot([], [], color='blue')
        self.axis.set_xlabel(r'Length ($\mu$m)')
        self.axis.set_ylabel(self.channel.ax_title)
        self.set_widgets()

    def plot_file(self, value):
        if value != 'Tots els fitxers': self.file = value
        self.set_widgets()
        
    def plot_channel(self, value):
        self.channel = value
        self.axis.set_ylabel(self.channel.ax_title)
        self.set_widgets()

    def set_widgets(self):
        self.compute_values()
        self.widgets['inf'].value.set(round(self.lims[0], 3))
        self.widgets['sup'].value.set(round(self.lims[1], 3))
        self.update_plot()
    
    def plot_lims(self, inf=None, sup=None):
        if inf is not None: self.lims = (inf, self.lims[1])
        if sup is not None: self.lims = (self.lims[0], sup)

        self.axis.set_ylim(self.lims)
        self.figure.tight_layout()
        self.figure.canvas.draw_idle()
    
    def direction(self, value):
        self._direction = value
        self.set_widgets()

    def units(self, value):
        self._units = value
        if value: 
            self.axis.set_xlabel('Length (μm)')
            self.widgets['freq'].config(state='readonly')
        else: 
            self.axis.set_xlabel('Time (min)')
            self.widgets['freq'].config(state='normal')

        self.set_widgets()

    def freq(self, value):
        self._freq = value
        self.set_widgets()
        
    def plot_color(self, value):
        self.plot.set_color(value)
        self.figure.canvas.draw()
    
    def guardar(self, value):
        ruta = filedialog.asksaveasfilename(
            parent = self.main_frame,
            defaultextension=".png",
            initialfile=f"{self.widgets['file'].value.get()} - {self.widgets['channel'].value.get()} Mitjana.png",
            filetypes=[("PNG", "*.png")]
        )

        if ruta: 
            self.figure.savefig(ruta)
            p = Path(ruta)
            np.savetxt(f"{p.parent}/{p.stem}.txt", np.column_stack((self.xval, self.mean)), fmt="%.4f")

    def compute_values(self):
        file_case = self.widgets['file'].value.get()
        self.mean = np.array([])
        self.xval = np.array([])
        
        if file_case == 'Tots els fitxers': files = self.files.values()
        else: files = [self.file]
            
        for file in files:
            x0, x1, y0, y1 = file.geometry.limit_pixels()
            z = file.channel[self.widgets['channel'].value.get()].Z[y0:y1, x0:x1]
            N = (x1-x0, y1-y0)

            if self._direction:
                Npixels = N[0]; xlength = file.geometry.midaBase[0]
                for a in range(Npixels): self.mean = np.append(self.mean, np.nanmean(z[0:,a]))

            else:
                Npixels = N[1]; xlength = file.geometry.midaBase[1]
                for a in range(Npixels): self.mean = np.append(self.mean, np.nanmean(z[a,0:]))

            if len(self.xval) == 0: start = 0
            else: start = self.xval[-1]

            if self._units: self.xval = np.append(self.xval, np.linspace(start, xlength+start, Npixels))
            else: 
                interval = 1/self._freq * 1/60 # Expressat en minuts. El nombre de línies és la meitat de la freqüència, ja que l'AIST fa dues passades en KPFM.
                self.xval = np.append(self.xval, np.linspace(start, Npixels*interval+start, Npixels))

        self.lims = (np.nanmin(self.mean), np.nanmax(self.mean))
    
    def update_plot(self):
        self.axis.set_xlim(self.xval.min(), self.xval.max())
        self.axis.set_ylim(self.lims)

        self.plot.set_data(self.xval, self.mean)

        self.figure.tight_layout()
        self.figure.tight_layout()
        self.figure.canvas.draw_idle()

    def _create_widgets(self):
        files = ['Tots els fitxers'] + list(self.files.keys())
        channels = list(self.file.channel.keys())

        optxunits = {'Longitud (μm)': True, 'Temps (min)': False}

        self.widgets = {
            "file": Widget(key="file", var_type=str, init=self.file.name,
                    text="Arxiu:", widget="cb", widget_kwargs={"options": files},
                    setter=self.plot_file),

            "channel": Widget(key="channel", var_type=str, init=self.channel.name,
                       text="Canal:", widget="cb", widget_kwargs={"options": channels},
                       setter=self.plot_channel),

            "cb_color": Widget(key="cb_color", var_type=str, init="blue",
                        text="Color de l'histograma:", widget="colorcb",
                        setter=self.plot_color),

            "inf": Widget(key="inf", var_type=float, init=0,
                   text="Límit inferior:", widget="entry",
                   setter=self.plot_lims, mode="kwargs"),

            "sup": Widget(key="sup", var_type=float, init=1,
                   text="Límit superior:", widget="entry",
                   setter=self.plot_lims, mode="kwargs"),

            "direction": Widget(key="direction", var_type=bool, init=True,
                         text="Direcció:", widget="radiobutton",
                         widget_kwargs={"options": {"H": True, "V": False}, "direction": "h"},
                         setter=self.direction),

            "units": Widget(key="units", var_type=bool, init=True,
                     text="Unitats:", widget="radiobutton", widget_kwargs={"options": optxunits},
                     setter=self.units),

            "freq": Widget(key="freq", var_type=float, init=0.5,
                    text="Freqüència (Hz):", widget="entry", widget_kwargs={"state": "readonly"},
                    setter=self.freq),

            "save": Widget(key="save", var_type=str, init="Guardar",
                    text="Guardar dades i imatge:", widget="button",
                    setter=self.guardar)}