from tkinter import Button, filedialog
from window import BaseFigureWindow
from pathlib import Path
import numpy as np
from process.statistics import hist, boxplot, remove_boxplot
from .base import BaseMenu

class GestorEstadistica(BaseMenu):  # Classe que gestiona les accions relacionades amb els perfils de fletxes.
    ordre = 50 # Atribut per a ordenar els menús (opcional)
    
    def __init__(self, app, get_current, set_current):
        super().__init__(app, get_current, set_current)  # Inicialitza la classe base

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
        
        self.fig_frame.grid(row=14, column=2, pady=10)

        btn_prev = Button(self.fig_frame, text="◀", command = self.toggle_plot, font=("Arial", 16))
        btn_prev.pack(side="left", padx=2)

        btn_next = Button(self.fig_frame, text="▶", command = self.toggle_plot, font=("Arial", 16))
        btn_next.pack(side="left", padx=2)
        
    def plot_file(self, value):
        self.file = value
        self.set_widgets()
        
    def plot_channel(self, value):
        self.channel = value
        self.set_widgets()

    def plot_lims(self, inf=None, sup=None):
        if inf is not None: self.lims = (inf, self.lims[1])
        if sup is not None: self.lims = (self.lims[0], sup)
        
        match self.mode:
            case "Hist": self.ax.set_xlim(self.lims)
            case "Box": self.ax.set_ylim(self.lims)
        
        self.fig.tight_layout()
        self.fig.canvas.draw_idle()
        
    def plot_remove(self):
        match self.mode:
            case "Hist": self.plot.remove()
            case "Box": remove_boxplot(self.plot)
    
    def plot_color(self, value):
        match self.mode:
            case "Hist": self.plot.set_color(value)
            case "Box": 
                for element in self.plot['boxes']: element.set_facecolor(value)
        
        self.fig.canvas.draw()
    
    def toggle_plot(self):
        self.plot_remove()
        match self.mode:
            case "Hist": self.mode = "Box" 
            case "Box": self.mode = "Hist"
                
        self.actualitza_plot()
    
    def actualitza_plot(self):
        color = self.widgets['cb_color'].value.get()
        
        match self.mode:
            case "Hist": self.plot, self.hist_data, _ = hist(self.ax, self.data, self.lims, xlabel=self.channel.dades.title, color=color)
            case "Box": self.plot = boxplot(self.ax, self.data, self.lims, name=self.channel.name, ylabel=self.channel.dades.title, color=color)

        self.fig.tight_layout()
        self.fig.tight_layout()
        self.fig.canvas.draw_idle()
    
    def guardar(self, value):
        ruta = filedialog.asksaveasfilename(
            parent = self.win_notebook,
            defaultextension=".png",
            initialfile=f"{self.file.name} - {self.channel.name} {self.mode}.png",
            filetypes=[("PNG", "*.png")]
        )

        if ruta: 
            self.fig.savefig(ruta)
            p = Path(ruta)
            txt_ruta = p.with_name(f"{self.file.name} - {self.channel.name} Data.txt")

            with open(txt_ruta, "w", encoding="utf-8") as f:
                for item in self.widgets.values():
                    if getattr(item, "_widget_type", None) == "entry" and item.cget("state") == "readonly":
                        f.write(f"{item._label.cget('text'):<30} {item.value.get():>10}\n")
        
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
        x0, x1, y0, y1 = self.file.limit_pixels
        data = self.channel.Z[y0:y1, x0:x1].ravel()
        mean = data.mean()
        std = data.std()

        if std == 0: skew = kurt = 0
        else:
            norm = (data - mean) / std
            skew = (norm**3).mean()
            kurt = (norm**4).mean()

        lw, q1, q2, q3, tw = np.percentile(data, [5, 25, 50, 75, 95])

        if hasattr(self, "plot"): self.plot_remove()
        
        self.lims = (np.percentile(data, 0.5), np.percentile(data, 99.5))
        self.data = data

        return mean, std, skew, kurt, lw, q1, q2, q3, tw

    def _grid(self):
        files = list(self.files.keys())
        channels = list(self.file.channel.keys())
        mean, std, skew, kurt, lw, q1, q2, q3, tw = self.compute_stats()
        
        return [
            (("file", str, self.file.name), ("Arxiu:", 'cb', {"options": files}), (self.plot_file, "args")),
            (("channel", str, self.channel.name), ("Canal:", 'cb', {"options": channels}), (self.plot_channel, "args")),
            (("cb_color", str, 'blue'), ("Color de l'histograma:", 'colorcb'), (self.plot_color, "args")),
            (("inf", float, round(self.lims[0], 3)), ("Límit inferior:", 'entry'), (self.plot_lims, "kwargs")),
            (("sup", float, round(self.lims[1], 3)), ("Límit superior:", 'entry'), (self.plot_lims, "kwargs")),
            (("mean", float, round(mean, 3)), ("Mitjana:", 'entry', {"state": "readonly"}), (self, "attr")),
            (("stderr", float, round(std, 3)), ("Desviació estàndard RMS:", 'entry', {"state": "readonly"}), (self, "attr")),
            (("skewness", float, round(skew, 3)), ("Asimetria:", 'entry', {"state": "readonly"}), (self, "attr")),
            (("kurtosis", float, round(kurt, 3)), ("Curtosi:", 'entry', {"state": "readonly"}), (self, "attr")),
            (("lower", float, round(lw, 3)), ("Llindar inferior (5%):", 'entry', {"state": "readonly"}), (self, "attr")),
            (("q1", float, round(q1, 3)), ("Primer quartil (25%):", 'entry', {"state": "readonly"}), (self, "attr")),
            (("q2", float, round(q2, 3)), ("Mediana (50%):", 'entry', {"state": "readonly"}), (self, "attr")),
            (("q3", float, round(q3, 3)), ("Tercer quartil (75%):", 'entry', {"state": "readonly"}), (self, "attr")),
            (("upper", float, round(tw, 3)), ("Llindar superior (95%):", 'entry', {"state": "readonly"}), (self, "attr")),
            (("save", str, "Guardar"), ("Guardar dades i imatge:", 'button'), (self.guardar, "args"))
            ]

class DirectionMean(BaseFigureWindow):
    def __init__(self, gestor):
        self._direction = True
        self._units = True
        self._freq = 0.5
        super().__init__(gestor, "Mostrar mitjana direccional", dim=(6,4))

        self.plot, = self.ax.plot([], [], color='blue')
        self.ax.set_xlabel(r'Length ($\mu$m)')
        self.ax.set_ylabel(self.channel.dades.title)
        self.set_widgets()
        
        self.fig_frame.grid(row=14, column=2, pady=10)

    def plot_file(self, value):
        if value != 'Tots els fitxers': self.file = value
        self.set_widgets()
        
    def plot_channel(self, value):
        self.channel = value
        self.ax.set_ylabel(self.channel.dades.title)
        self.set_widgets()

    def set_widgets(self, **kwargs):
        self.compute_values(**kwargs)
        self.widgets['inf'].value.set(round(self.lims[0], 3))
        self.widgets['sup'].value.set(round(self.lims[1], 3))
        self.update_plot()
    
    def plot_lims(self, inf=None, sup=None):
        if inf is not None: self.lims = (inf, self.lims[1])
        if sup is not None: self.lims = (self.lims[0], sup)

        self.ax.set_ylim(self.lims)
        self.fig.tight_layout()
        self.fig.canvas.draw_idle()
    
    def direction(self, value):
        self._direction = value
        self.set_widgets()

    def units(self, value):
        self._units = value
        if value: 
            self.ax.set_xlabel(r'Length ($\mu$m)')
            self.widgets['freq'].configure(state='readonly')
        else: 
            self.ax.set_xlabel('Time (min)')
            self.widgets['freq'].configure(state='normal')

        self.set_widgets()

    def freq(self, value):
        self._freq = value
        self.set_widgets()
        
    def plot_color(self, value):
        self.plot.set_color(value)
        self.fig.canvas.draw()
    
    def guardar(self, value):
        ruta = filedialog.asksaveasfilename(
            parent = self.win_notebook,
            defaultextension=".png",
            initialfile=f"{self.widgets['file'].value.get()} - {self.widgets['channel'].value.get()} Mitjana.png",
            filetypes=[("PNG", "*.png")]
        )

        if ruta: 
            self.fig.savefig(ruta)
            p = Path(ruta)
            np.savetxt(f"{p.parent}/{p.stem}.txt", np.column_stack((self.xval, self.mean)), fmt="%.4f")

    def compute_values(self):
        file_case = self.widgets['file'].value.get()
        self.mean = np.array([])
        self.xval = np.array([])
        
        if file_case == 'Tots els fitxers': files = self.files.values()
        else: files = [self.file]
            
        for file in files:
            x0, x1, y0, y1 = file.limit_pixels
            z = file.channel[self.widgets['channel'].value.get()].Z[y0:y1, x0:x1]
            N = (x1-x0, y1-y0)

            if self._direction:
                Npixels = N[0]; xlength = file.midaBase[0]
                for a in range(Npixels): self.mean = np.append(self.mean, np.mean(z[0:,a]))

            else:
                Npixels = N[1]; xlength = file.midaBase[1]
                for a in range(Npixels): self.mean = np.append(self.mean, np.mean(z[a,0:]))

            if len(self.xval) == 0: start = 0
            else: start = self.xval[-1]

            if self._units: self.xval = np.append(self.xval, np.linspace(start, xlength+start, Npixels))
            else: 
                interval = 1/self._freq * 1/60 # Expressat en minuts. El nombre de línies és la meitat de la freqüència, ja que l'AIST fa dues passades en KPFM.
                self.xval = np.append(self.xval, np.linspace(start, Npixels*interval+start, Npixels))

        self.lims = (self.mean.min(), self.mean.max())
    
    def update_plot(self):
        self.ax.set_xlim(self.xval.min(), self.xval.max())
        self.ax.set_ylim(self.lims)

        self.plot.set_data(self.xval, self.mean)

        self.fig.tight_layout()
        self.fig.tight_layout()
        self.fig.canvas.draw_idle()

    def _grid(self):
        files = ['Tots els fitxers'] + list(self.files.keys())
        channels = list(self.file.channel.keys())

        optxunits = {r'Longitud ($\mu$m)': True, 'Temps (min)': False}

        return [
            (("file", str, self.file.name), ("Arxiu:", 'cb', {"options": files}), (self.plot_file, "args")),
            (("channel", str, self.channel.name), ("Canal:", 'cb', {"options": channels}), (self.plot_channel, "args")),
            (("cb_color", str, 'blue'), ("Color de l'histograma:", 'colorcb'), (self.plot_color, "args")),
            (("inf", float, 0), ("Límit inferior:", 'entry'), (self.plot_lims, "kwargs")),
            (("sup", float, 1), ("Límit superior:", 'entry'), (self.plot_lims, "kwargs")),
            (("direction", float, True), ("Direcció:", 'radiobutton', {"options": {'H': True, 'V': False}, "vertical": False}), (self.direction, "args")),
            (("units", float, True), ("Unitats:", 'radiobutton', {"options": optxunits}), (self.units, "args")),
            (("freq", float, 0.5), ("Freqüència (Hz):", 'entry', {'state': 'readonly'}), (self.freq, "args")),
            (("save", str, "Guardar"), ("Guardar dades i imatge:", 'button'), (self.guardar, "args"))
            ]