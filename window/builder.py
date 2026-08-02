from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import Toplevel
from tkinter.ttk import Frame
from drawing import mapdraw as map
from drawing.plots import base_plot
from process.images import copy_figure
from window.labels import build_grid

# Arxiu que gestiona els builders principals dels menús de l'aplicació, així com les finestres i funcionalitats comunes a tots els builders.

class BaseWindow:
    def __init__(self, gestor, title):
        self._file, self._channel = gestor.element_obert()
        self.files = gestor.files

        self.notebook = gestor.notebook
        self.label_inici = gestor.label_inici

        self.file_key = self.file.name; self.channel_key = self.channel.name

        self._file_ref = None
        self.intersect = True
        self.update = True

        window = Toplevel(gestor.root)
        window.title(title)
        self.main_frame = Frame(window)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.control_frame = Frame(self.main_frame)
        self.control_frame.pack(side="left", fill="y", expand=True, padx=10, pady=10)

        self.widgets = build_grid(self.control_frame, self._grid(), button = False)
    
    @property
    def file(self):
        return self._file
    
    @file.setter
    def file(self, value):
        if value != "Tots els mapes": self._file = self.files[value]
        self.file_key = value
        self.update_channels()

    @property
    def file_ref(self):
        return self._file_ref
    
    @file_ref.setter
    def file_ref(self, value):
        self._file_ref = self.files[value]
        self.update_channels()
        
    @property
    def channel(self):
        return self._channel
    
    @channel.setter
    def channel(self, value):
        if value is None: return
        if value in self.file.channel: self._channel = self.file.channel[value]
        self.channel_key = value

        if self.file_key == "Tots els mapes": return
        
        if self.update: self.file.notebook.select(self.channel.frame)

    def files_list(self):
        if self.file_key == "Tots els mapes":
            files = list(self.files.values())
        else:
            files = [self.file]
            if self.file_ref and self.file_ref not in files: files.append(self.file_ref)
            if self.update: self.notebook.select(self.file.frame)

        return files
    
    def compare_files(self):
        list_files = ["Tots els mapes"] + list(self.files.keys())
        self._file_ref = self.files[list_files[1]]
        
        channels = self.file_ref.channel.keys() & self.file.channel.keys()
        
        if self.channel.name in channels: initCh = self.channel.name
        else: initCh = channels[0]

        return list_files, channels, initCh
    
    def update_channels(self):
        if not hasattr(self, 'file') or not hasattr(self, 'widgets'): return
        if not "channel" in self.widgets: return

        files = self.files_list()
        channels = list(files[0].channel)

        if self.intersect:
            common = set.intersection(*(set(f.channel) for f in files))
            channels = [ch for ch in channels if ch in common]
        else:
            for f in files[1:]:
                for ch in f.channel:
                    if ch not in channels:
                        channels.append(ch)

        self.update_channel_combobox(channels)

    def update_files(self, files):
        comboFile = self.widgets["file"]
        comboFile.config(values=files)
        comboFile.set(self.file.name)

    def update_channel_combobox(self, channels):
        comboCh = self.widgets["channel"]
        current = self.channel

        comboCh.config(values=channels)
        comboCh.options = dict(zip(channels, channels))
        
        if current.name in channels:
            comboCh.set(current.name)
            self.channel = current.name
            return
        
        elif channels:
            comboCh.set(channels[0])
            self.channel = channels[0]
            return
        else:
            comboCh.set("")
            return

    @staticmethod
    def _init_figure(main_frame, figure):
        frame = Frame(main_frame)
        frame.pack(side='right', fill="both", expand=True)
        frame.bind("<Control-c>", lambda e: copy_figure(figure))

        canvas = FigureCanvasTkAgg(figure, master=frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        canvas.draw()

        return frame, canvas

class BaseMapWindow(BaseWindow):
    def __init__(self, gestor, nom):
        super().__init__(gestor, nom)
        
        self.update = False
        ch = self.channel
        self.lims = ch.lims
        self.z = ch.Z
        self.units = ch.units

        self.figure, self.axis, self.image, self.cbar = map.create_map(ch.color.cmap, self.z, self.lims, self.units, self.file.midaBase, ch.color.lims)
        w, h = self.figure.get_size_inches()   # mida actual

        factor = 0.8
        self.figure.set_size_inches(w*factor, h*factor)
        self.escala = map.Escala(self.axis, color = ch.color.scale)
        self.axis.set_anchor('W')
        self.figure.subplots_adjust(left=0.02, right=0.8, top=1, bottom=0)
        
        self.image.set_clim(self.lims)

        self.fig_frame, self.canvas = self._init_figure(self.main_frame, self.figure)
        self.canvas.get_tk_widget().config(bg='#2e2e2e', highlightthickness=0, bd=0)
        
        rect = self.file.midaBase[1]/self.file.midaBase[0]
        dimensions = map.get_dimensions(self.axis, rect)
        map.set_dimensions(self.canvas, self.escala, self.cbar, rect, *dimensions)

    def file_changed(self, value):
        self.file = value
        self.channel_changed(self.widgets['channel'].get())
        
        midaX, midaY = self.file.midaBase
        self.image.set_extent([0, midaX, 0, midaY])
        self.axis.set_xlim(0, midaX)
        self.axis.set_ylim(0, midaY)
        self.escala.actualitza(*self.file.zoom.xylims)
        rect = self.file.midaBase[1] / self.file.midaBase[0]
        dimensions = map.get_dimensions(self.axis, rect)
        map.set_dimensions(self.canvas, self.escala, self.cbar, rect, *dimensions)
        self.canvas.draw_idle()
        
    def channel_changed(self, value):
        ch = self.file.channel[value]
        self.z = ch.Z
        self.lims = ch.lims
        self.units = ch.units

        self.cbar.limInf.set_color(ch.color.limInf)
        self.cbar.limSup.set_color(ch.color.limSup)

        map.update_map(self.image, ch.color.cmap, ch.Z, ch.lims, ch.units, mida = self.file.midaBase, colLims = ch.color.lims, cbar = self.cbar)
        self.escala.color = ch.color.scale
        self.image.set_clim(ch.lims)
        self.canvas.draw_idle()
    
    def update_fig(self):
        self.image.set_data(self.z)
        self.image.set_clim(*self.lims)
        self.image.set_clim(*self.lims)
        
        self.cbar.limInf.set_text(f'{self.lims[0]} {self.units}')
        self.cbar.limSup.set_text(f'{self.lims[1]} {self.units}')
        self.canvas.draw_idle() 
        
    def aplicar(self, value):
        ch = self.file.channel[self.widgets['channel'].get()]
        ch.Z = self.z
        ch.lims = self.lims
        current_chframe = self.file.notebook.select()

        self.notebook.select(self.file.frame)
        self.file.notebook.select(ch.frame)
        
        if current_chframe == str(ch.frame):
            self.file.capçalera.set_channel(ch)
            self.file.redraw()

class BaseFigureWindow(BaseWindow):
    def __init__(self, gestor, nom, dim=(4,4)):
        super().__init__(gestor, nom)

        self.figure, self.ax = base_plot(dim=dim)
        self.figure.tight_layout()

        self.fig_frame, self.canvas = self._init_figure(self.main_frame, self.figure)