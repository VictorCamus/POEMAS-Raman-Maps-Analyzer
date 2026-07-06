import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import TABLEAU_COLORS
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import scipy.optimize as scopt
import tkinter as tk
from pathlib import Path
import tkinter.ttk as ttk

from classes.peaks import Pic, Fons
from drawing import mapdraw as mapa
from classes.filechannel import InteraccioFigura
from fileio.adapters import open_file
from drawing.colormap import cmaps_matplotlib
from drawing.plots import plot_peak
from process.basics import find_nearest
from process.statistics import lims_outliers

#Variables inicials
default_text_map = "Posició del cursor al mapa (punts)"
default_text_spec = "Posició del cursor a l'espectre"
colorsT = list(TABLEAU_COLORS.values())[1:]
font = ("DejaVu Sans", 25)
peakAttr = ["PeakCenter", "FWHM", "Area", "Intensity", "NormInt"]
ops = {'P2-P1': lambda a, b: a - b, 'P2/P1': lambda a, b: a / b}

class AltresMags:
    def __init__(self, pics, magnituds, operacio):
        self.pics = pics # Put the file names of the peak fitting parameters
        self.magnituds = magnituds # Choose one of the following peak magnitudes: ["Peak center", "FWHM", "Intensity", "Normalized Intensity"]
        self.operacio = operacio # Define the operation to do with the magnitudes

#Altres Variables
rangeSpec650a700 = AltresMags(
    [],  # File names of the peak fitting parameters
    [], # Peak magnitudes to combine
    {"Range": [650, 700]}) # Operation to do with the magnitudes

#IMPORTANT: only magnitudes added to this vector will be considered:
VectorExtraMags = {"SpectralRangeInt650-700": rangeSpec650a700}

class SpecType:
    def __init__(self, name, xdata, units, xtitle):
        self.name = name
        self.xdata = xdata
        self.xtitle = xtitle
        
        self.units = units
        
    @property
    def units(self):
        return self._units
    
    @units.setter
    def units(self, value):
        self._units = {"PeakCenter": value,
            "FWHM": value,
            "Area": value,
            "Intensity": 'uA',
            "NormInt": ''}
        
class PintaMapesInterficie:
    def __init__(self):
        self.root = tk.Tk()
        self.root.option_add("*Font", font)
        self.root.winfo_toplevel().title('Mapa interactiu')
        self.root.geometry("2000x1000")

        self.color = {"PeakCenter": "viridis", 
                      "FWHM": "cividis",
                      "Area": "inferno",
                      "Intensity": 'calent', 
                      "NormInt": 'calent'}
        
        nomsFmapes = tk.filedialog.askopenfilenames(filetypes = [("AIST", "*.aist"), ("TXT", "*.txt")])
        self.nomsMapes = {Path(nom).stem: Path(nom) for nom in nomsFmapes}
        nomsLlista = list(self.nomsMapes.keys())
        self.file = self.nomsMapes[nomsLlista[0]]
        self.folder = self.file.with_suffix('')
        self.format = self.file.suffix
        self.label = {}; self.object = {}

        marcTop = tk.Frame(self.root)
        marcTop.grid(row = 0, column = 0, sticky = 'ew')
        
        self.label['file'] = tk.Label(marcTop, text = 'Fitxer:')
        self.label['file'].grid(row = 0, column = 2, pady = 5, padx = 10, sticky = 'e')
        self.object['file'] = ttk.Combobox(marcTop, textvariable = tk.StringVar(self.root, value = nomsLlista[0]), values = nomsLlista, state = 'readonly', width = 30)
        self.object['file'].grid(row=0, column = 3, pady = 5, padx = 0, columnspan = 10, sticky = 'w')
        self.object['file'].bind("<<ComboboxSelected>>", self.change_map)
        self.object['file'].current(0)
        
        opcionsMap = ["Intensitat", "Pics", "P2-P1", "P2/P1", *VectorExtraMags.keys()]
        self.nommap = opcionsMap[0]
        self.label['map'] = tk.Label(marcTop, text = 'Mapa:')
        self.label['map'].grid(row = 1, column = 1, pady = 10, padx = 10, sticky = 'e')
        self.object['map'] = ttk.Combobox(marcTop, textvariable = tk.StringVar(self.root, value = self.nommap), values = opcionsMap, state = 'readonly', width = 8)
        self.object['map'].grid(row = 1, column = 2, pady = 10, padx = 0, sticky = 'w')
        self.object['map'].bind("<<ComboboxSelected>>", lambda event: self.plt_map(event, attr = 'nommap'))
        self.object['map'].current(0)
        
        self.label['fits'] = tk.Label(marcTop, text = 'Ajust:')
        self.label['fits'].grid(row = 1, column = 3, pady = 10, padx = 10, sticky = 'e')
        self.object['fits'] = ttk.Combobox(marcTop, textvariable = tk.StringVar(self.root, value = []), values = [], state = 'readonly', width = 12)
        self.object['fits'].grid(row = 1, column = 4, pady = 10, padx = 0, sticky = 'w')
        self.object['fits'].bind("<<ComboboxSelected>>", lambda event: self.plt_map(event, attr = 'nomfit'))
        
        self.label['pic1'] = tk.Label(marcTop, text = 'P1:', width = 3)
        self.label['pic1'].grid(row = 1, column = 5, pady = 10, padx = 5, sticky = 'e')
        self.object['pic1'] = ttk.Combobox(marcTop, textvariable = tk.StringVar(self.root, value = []), values = [], state = 'readonly', width = 5)
        self.object['pic1'].grid(row = 1, column = 6, pady = 10, padx = 0, sticky = 'w')
        self.object['pic1'].bind("<<ComboboxSelected>>", lambda event: self.plt_map(event, attr = 'pic1'))
        
        self.label['pic2'] = tk.Label(marcTop, text = 'P2:', width = 3)
        self.label['pic2'].grid(row = 1, column = 7, pady = 10, padx = 5, sticky = 'e')
        self.object['pic2'] = ttk.Combobox(marcTop, textvariable = tk.StringVar(self.root, value = []), values = [], state = 'readonly', width = 5)
        self.object['pic2'].grid(row = 1, column = 8, pady = 10, padx = 0, sticky = 'w')
        self.object['pic2'].bind("<<ComboboxSelected>>", lambda event: self.plt_map(event, attr = 'pic2'))
        
        self.nommag = "Intensity"
        self.label['mag'] = tk.Label(marcTop, text = 'Magnitud:')
        self.label['mag'].grid(row = 1, column = 12, pady = 10, padx = 10)
        self.object['mag'] = ttk.Combobox(marcTop, textvariable = tk.StringVar(self.root, value = self.nommag), values = [self.nommag], state = 'readonly', width = 10)
        self.object['mag'].grid(row = 1, column = 13, pady = 10, padx = 0)
        self.object['mag'].bind("<<ComboboxSelected>>", lambda event: self.plt_map(event, attr = 'nommag'))
        self.object['mag'].current(0)
        
        marcTop.grid_columnconfigure(0, minsize = 200)
        marcTop.grid_columnconfigure(9, minsize = 100)
        
        marcTrack = tk.Frame(self.root)
        marcTrack.grid(row = 1, column = 0, sticky = 'ew')
        
        self.label['track_map'] = tk.Label(marcTrack, text = default_text_map)
        self.label['track_map'].grid(row = 0, column = 1, columnspan = 6)
        
        self.label['track_spec'] = tk.Label(marcTrack, text = default_text_spec)
        self.label['track_spec'].grid(row = 0, column = 8, columnspan = 4)
        
        marcTrack.grid_columnconfigure(0, minsize = 200)
        marcTrack.grid_columnconfigure(7, minsize = 200)
        
        set_valuex = tk.IntVar(marcTrack, value = '')
        self.label['track_x'] = tk.Label(marcTrack, text = 'X:', width = 3)
        self.label['track_x'].grid(row = 1, column = 1, pady = 10, padx = 5, sticky = 'e')
        self.object['track_x'] = tk.Entry(marcTrack, textvariable=set_valuex, state = 'readonly', width = 3)
        self.object['track_x'].grid(row = 1, column = 2, pady = 10, padx = 0, sticky = 'w')
        self.object['track_x'].value = set_valuex
        
        set_valuey = tk.IntVar(marcTrack, value = '')
        self.label['track_y'] = tk.Label(marcTrack, text = 'Y:', width = 3)
        self.label['track_y'].grid(row = 1, column = 3, pady = 10, padx = 5, sticky = 'e')
        self.object['track_y'] = tk.Entry(marcTrack, textvariable=set_valuey, state = 'readonly', width = 3)
        self.object['track_y'].grid(row = 1, column = 4, pady = 10, padx = 0, sticky = 'w')
        self.object['track_y'].value = set_valuey
        
        set_valuez = tk.DoubleVar(marcTrack, value = '')
        self.label['track_z'] = tk.Label(marcTrack, text = f'{self.nommag}:', width = 10)
        self.label['track_z'].grid(row = 1, column = 5, pady = 10, padx = 5, sticky = 'e')
        self.object['track_z'] = tk.Entry(marcTrack, textvariable=set_valuez, state = 'readonly', width = 10)
        self.object['track_z'].grid(row = 1, column = 6, pady = 10, padx = 0, sticky = 'w')
        self.object['track_z'].value = set_valuez
        
        set_valuexax = tk.IntVar(marcTrack, value = '')
        self.label['track_xaxis'] = tk.Label(marcTrack, text = 'λ (nm)', width = 6)
        self.label['track_xaxis'].grid(row = 1, column = 8, pady = 10, padx = 5, sticky = 'e')
        self.object['track_xaxis'] = tk.Entry(marcTrack, textvariable=set_valuexax, state = 'readonly', width = 5)
        self.object['track_xaxis'].grid(row = 1, column = 9, pady = 10, padx = 0, sticky = 'w')
        self.object['track_xaxis'].value = set_valuexax
        
        set_valueyax = tk.IntVar(marcTrack, value = '')
        self.label['track_yaxis'] = tk.Label(marcTrack, text = 'Intensity (uA):', width = 10)
        self.label['track_yaxis'].grid(row = 1, column = 10, pady = 10, padx = 5, sticky = 'e')
        self.object['track_yaxis'] = tk.Entry(marcTrack, textvariable=set_valueyax, state = 'readonly', width = 5)
        self.object['track_yaxis'].grid(row = 1, column = 11, pady = 10, padx = 0, sticky = 'w')
        self.object['track_yaxis'].value = set_valueyax

        marcLims = tk.Frame(self.root)
        marcLims.grid(row = 2, column = 0, sticky = "nsew")
        
        set_valueCM = tk.DoubleVar(marcLims, value = 'hot')
        self.label['cmap'] = tk.Label(marcLims, text = 'Color:', width = 5)
        self.label['cmap'].grid(row = 0, column = 1, pady = 10, padx = 5, sticky = 'e')
        self.object['cmap'] =  ttk.Combobox(marcLims, textvariable = set_valueCM, values = cmaps_matplotlib, state = 'readonly', width = 8)
        self.object['cmap'].grid(row = 0, column = 2, pady = 10, padx = 0, sticky = 'w')
        self.object['cmap'].bind("<<ComboboxSelected>>", self.new_cmap)
        self.object['cmap'].value = set_valueCM

        set_valueMS = tk.DoubleVar(marcLims, value = '')
        self.label['map_limSup'] = tk.Label(marcLims, text = 'Límit superior:', width = 12)
        self.label['map_limSup'].grid(row = 0, column = 3, pady = 10, padx = 5, sticky = 'e')
        self.object['map_limSup'] = tk.Entry(marcLims, textvariable=set_valueMS, width = 6)
        self.object['map_limSup'].grid(row = 0, column = 4, pady = 10, padx = 0, sticky = 'w')
        self.object['map_limSup'].bind('<Return>', lambda e: self.map_lims(e, lim = 'Sup'))
        self.object['map_limSup'].value = set_valueMS
        
        set_valueMI = tk.DoubleVar(marcLims, value = '')
        self.label['map_limInf'] = tk.Label(marcLims, text = 'Límit inferior:', width = 12)
        self.label['map_limInf'].grid(row = 1, column = 3, pady = 10, padx = 5, sticky = 'e')
        self.object['map_limInf'] = tk.Entry(marcLims, textvariable=set_valueMI, width = 6)
        self.object['map_limInf'].grid(row = 1, column = 4, pady = 10, padx = 0, sticky = 'w')
        self.object['map_limInf'].bind('<Return>', lambda e: self.map_lims(e, lim = 'Inf'))
        self.object['map_limInf'].value = set_valueMI
        
        set_valueL = tk.DoubleVar(marcLims, value = '')
        self.label['laser'] = tk.Label(marcLims, text = 'λ₀ (nm):', width = 7)
        self.label['laser'].grid(row = 0, column = 6, pady = 10, padx = 5, sticky = 'e')
        self.object['laser'] = tk.Entry(marcLims, textvariable=set_valueL, width = 6, state = 'readonly')
        self.object['laser'].grid(row = 0, column = 7, pady = 10, padx = 0, sticky = 'w')
        self.object['laser'].value = set_valueL
        
        self.spec_type = 'nm'
        set_valueST = tk.DoubleVar(marcLims, value = 'nm')
        self.label['spec_type'] = tk.Label(marcLims, text = 'Unitats:', width = 7)
        self.label['spec_type'].grid(row = 1, column = 6, pady = 10, padx = 5, sticky = 'e')
        self.object['spec_type'] =  ttk.Combobox(marcLims, textvariable = set_valueST, values = ['nm', 'eV', '1/cm'], state = 'readonly', width = 4)
        self.object['spec_type'].grid(row = 1, column = 7, pady = 10, padx = 0, sticky = 'w')
        self.object['spec_type'].bind("<<ComboboxSelected>>", self.new_spectype)
        self.object['spec_type'].value = set_valueST
        
        self.lims = {}
        set_valueLeft = tk.DoubleVar(marcLims, value = 0)
        self.label['spec_xaxis'] = tk.Label(marcLims, text = 'Eix X:', width = 6)
        self.label['spec_xaxis'].grid(row = 0, column = 8, pady = 10, padx = 5, sticky = 'e')
        self.object['spec_left'] = tk.Entry(marcLims, textvariable=set_valueLeft, width = 6)
        self.object['spec_left'].grid(row = 0, column = 9, pady = 10, padx = 0, sticky = 'w')
        self.object['spec_left'].bind('<Return>', lambda e: self.set_speclims(e, key = 'spec_left'))
        self.object['spec_left'].value = set_valueLeft

        set_valueRight = tk.DoubleVar(marcLims, value = 1)
        self.object['spec_right'] = tk.Entry(marcLims, textvariable=set_valueRight, width = 6)
        self.object['spec_right'].grid(row = 0, column = 10, pady = 10, padx = 0, sticky = 'w')
        self.object['spec_right'].bind('<Return>', lambda e: self.set_speclims(e, key = 'spec_right'))
        self.object['spec_right'].value = set_valueRight

        set_valueBot = tk.DoubleVar(marcLims, value = 0)
        self.label['spec_yaxis'] = tk.Label(marcLims, text = 'Eix Y:', width = 6)
        self.label['spec_yaxis'].grid(row = 1, column = 8, pady = 10, padx = 5, sticky = 'e')
        self.object['spec_bot'] = tk.Entry(marcLims, textvariable=set_valueBot, width = 6)
        self.object['spec_bot'].grid(row = 1, column = 9, pady = 10, padx = 0, sticky = 'w')
        self.object['spec_bot'].bind('<Return>', lambda e: self.set_speclims(e, key = 'spec_bot'))
        self.object['spec_bot'].value = set_valueBot

        set_valueTop = tk.DoubleVar(marcLims, value = 1)
        self.object['spec_top'] = tk.Entry(marcLims, textvariable=set_valueTop, width = 6)
        self.object['spec_top'].grid(row = 1, column = 10, pady = 10, padx = 0, sticky = 'w')
        self.object['spec_top'].bind('<Return>', lambda e: self.set_speclims(e, key = 'spec_top'))
        self.object['spec_top'].value = set_valueTop

        set_valueDades = tk.BooleanVar(marcLims, value = True)
        self.object['spec_data'] = tk.Checkbutton(marcLims, text="Dades", variable=set_valueDades, command=self.mostrar_dades, indicatoron = True)
        self.object['spec_data'].grid(row = 0, column = 11, pady = 10, padx = 5, sticky = 'e')
        self.object['spec_data'].value = set_valueDades

        set_valueBkg = tk.BooleanVar(marcLims, value = True)
        self.object['spec_bkg'] = tk.Checkbutton(marcLims, text="Fons", variable=set_valueBkg, command=self.plot_spec, indicatoron = True)
        self.object['spec_bkg'].grid(row = 1, column = 11, pady = 10, padx = 5, sticky = 'e')
        self.object['spec_bkg'].value = set_valueBkg

        set_valueEtiq = tk.BooleanVar(marcLims, value = True)
        self.object['spec_etiq'] = tk.Checkbutton(marcLims, text="Etiquetes", variable=set_valueEtiq, command=self.set_etiqs, indicatoron = True)
        self.object['spec_etiq'].grid(row = 1, column = 12, pady = 10, padx = 5, sticky = 'e')
        self.object['spec_etiq'].value = set_valueEtiq
        
        marcLims.grid_columnconfigure(0, minsize = 200)
        marcLims.grid_columnconfigure(5, minsize = 100)
        plt.rcParams["font.size"]=18
        self.fig, self.ax = plt.subplots(nrows=1, ncols=2)

        self.fig.subplots_adjust(left=0.01, right=0.99, bottom=0.15, top=0.9, wspace=0.3)
        # Add an Axes to the right of the main Axes.
        
        self.new_file()
        self.object['map_limInf'].value.set(self.limInf)
        self.object['map_limSup'].value.set(self.limSup)
        
        self.image = self.ax[0].imshow(self.Z, origin="lower", vmin = self.limInf, vmax = self.limSup, extent = [0, self.mida[0], 0, self.mida[1]], interpolation = None)
        self.cax = mapa.create_cbar(self.fig, self.image)
        self.scale = mapa.Escala(self.ax[0])
    
        mapa.ajust_eixos(self.ax[0])
        self.ax[0].set_autoscale_on(True)

        marcMig = tk.Frame(self.root)
        marcMig.grid(row = 3, column = 0, sticky = "nsew")
        marcMig.grid_rowconfigure(0, weight=1)
        marcMig.grid_columnconfigure(0, weight=1)
        self.canvas = FigureCanvasTkAgg(self.fig, master=marcMig)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        
        self.canvas.mpl_connect('button_press_event', lambda event: self.on_click(event, self.ax[0]))
        self.canvas.mpl_connect('motion_notify_event', self.update_mouse)
        self.root.bind('<Configure>', self._trigger_resize)
        self.root.bind_all('<Escape>', lambda event: self.root.quit())
        
        self.zoom = InteraccioFigura(self.ax[0], self.image, self.scale, self.cax, self.mida)

        marcBot = tk.Frame(self.root)
        marcBot.grid(row = 4, column = 0, sticky = 'ew')

        self.object['button1'] = tk.Button(marcBot, text="Dibuixa histograma", command=self.plot_hist)
        self.object['button1'].grid(row = 0, column = 2, pady = 5, padx = 100)

        self.object['button2'] = tk.Button(marcBot, text="Guarda espectre", command=self.save_spec)
        self.object['button2'].grid(row = 0, column = 3, pady = 5, padx = 100)

        self.object['button3'] = tk.Button(marcBot, text="Eixir", command=self.root.quit)
        self.object['button3'].grid(row = 0, column = 4, pady = 5, padx = 100)
        
        self.canvas.draw()
        
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(3, weight=1)  # marcbot

        self.plt_map()
        self.canvas.get_tk_widget().focus_force()
        self.root.mainloop()

    def map_lims(self, event, lim = 'Inf'):
        match lim:
            case 'Inf': self.limInf = float(event.widget.get())
            case 'Sup': self.limSup = float(event.widget.get())

        lims = self.limInf, self.limSup
        mapa.update_cbar(self.cax, lims, units = self.specs[self.spec_type].units[self.nommag] if not self.nommap == 'Ràtio (P2/P1)' else '')
        self.image.set_clim(*lims)
        self.canvas.draw()
    
    def mostrar_dades(self):
        if not hasattr(self, 'dades'):
            return

        self.dades.set_visible(self.object['spec_data'].value.get())
        self.canvas.draw_idle()
        
    def new_spectype(self, event):
        self.spec_type = event.widget.get()
        self.label['track_xaxis'].configure(text = self.specs[self.spec_type].xtitle)
        if not hasattr(self, 'posx') or not hasattr(self, 'posy'): return
        self.lims = {}
        self.plot_spec()
    
    def set_etiqs(self):
        if not hasattr(self, 'etiquette'): return
        
        for element in self.etiquette.values(): element.set_visible(self.object['spec_etiq'].value.get())
        self.canvas.draw_idle()
        
    def set_speclims(self, event, key):
        self.lims[key] = float(event.widget.get())
        self.ax[1].set_xlim(self.lims['spec_left'], self.lims['spec_right'])
        self.ax[1].set_ylim(self.lims['spec_bot'], self.lims['spec_top'])
        self.canvas.draw()

    def new_cmap(self, event):
        self.image.set_cmap(event.widget.get())
        self.canvas.draw()

    def _trigger_resize(self, event):
        # Cancel·lar el timer del resize ràpid del canal actiu
        if not hasattr(self, 'zoom'): return
        if hasattr(self, "_active_timer_id") and self._active_timer_id:
            self.root.after_cancel(self._active_timer_id)

        # Programar el resize del canal actiu després de 50 ms
        self._active_timer_id = self.root.after(100, self.zoom._resize())
        
    def event_to_pixel(self, event):
        x_pixel = math.floor(self.dims[0]/self.mida[1]*event.xdata) + 1
        y_pixel = math.floor(self.dims[1]/self.mida[0]*event.ydata) + 1
        return x_pixel, y_pixel
    
    def change_map(self, value):
        self.file = self.nomsMapes[value.widget.get()]
        self.folder = self.file.with_suffix('')
        self.format = self.file.suffix
        self.new_file()
        self.plt_map()

    def new_file(self):
        xdata, self.spectra, self.mida, self.dims, self.laser, _ = open_file([self.file], self.format)
        self.IntInt = np.sum(self.spectra, axis=1).reshape(*self.dims)
        self.Z = self.IntInt.copy()
        self.limInf, self.limSup = lims_outliers(self.Z)
        self.object['laser'].value.set(self.laser)
        
        self.specs = {'nm': SpecType('PL (λ)', xdata['nm'], 'nm', 'λ (nm)'),
                      'eV': SpecType('PL (E)', xdata['eV'], 'eV', 'E (eV)'),
                      '1/cm': SpecType('RAMAN', xdata['1/cm'], 'cm⁻¹', 'q (cm⁻¹)')}
        
        if not Path(self.folder).exists() or next(Path(self.folder).glob("*.txt")) is StopIteration: return

        self.fits = {}
        for file in sorted(Path(self.folder).glob("*.txt")):
            if file.name.endswith("_params.txt"): continue

            header = {}
            with open(file, encoding="utf-8") as f:
                posicio = 0

                for linea in f:
                    if not linea.startswith("#"): break
                    posicio += 1
                    if ":" in linea:
                        clau, valor = linea[1:].split(":", 1)
                        header[clau.strip()] = valor.strip()

            if not header['Nom'] in self.fits: self.fits[header['Nom']] = {}
            dades = np.loadtxt(file, skiprows=2)

            self.rangfit = [float(header['Inici']), float(header['Final'])]
            units = header['Unitats']
            self.fit_start, self.fit_end = sorted(find_nearest(xdata[units], self.rangfit))
            xfit = xdata[units][self.fit_start:self.fit_end]

            if header['Pic'] == 'bkg':
                nvars = dades.shape[1]
                varbls = np.array(dades[:, 2:2+int((nvars-2)/2)].reshape(*self.dims))
                bkgclass = Fons(header['Pic'], units, header['Funció'], varbls, xfit = xfit, color = 'tab:blue')
                result = [np.sum(bkgclass.data([i, j])) for i in range(self.dims[0]) for j in range(self.dims[1])]
                bkgclass.Intensity = np.array(result).reshape(*self.dims)
                self.fits[header['Nom']]['bkg'] = bkgclass
                
                self.object['spec_type'].value.set(units)
                self.spec_type = units
                continue

            centers = dades[:, 2].reshape(*self.dims)
            FWHM = dades[:, 3].reshape(*self.dims)
            Int = dades[:, 4].reshape(*self.dims)
            IntNorm = Int / self.IntInt

            peak = Pic(header['Pic'], units, header["Funció"], centers, FWHM, Int, IntNorm, xfit = xfit, color = colorsT[len(self.fits[header['Nom']])])
            self.fits[header['Nom']][header['Pic']] = peak

        self.object["fits"].configure(values = list(self.fits.keys()))
        self.object["fits"].current(0)
        self.nomfit = list(self.fits.keys())[0]
        
        pics = list(self.fits[self.nomfit].keys())
        pics.remove('bkg')

        self.object["pic1"].configure(values = pics)
        self.object["pic1"].current(0)
        self.pic1 = pics[0]
        
        self.object["pic2"].configure(values = pics)
        self.object["pic2"].current(0)
        self.pic2 = pics[0]

    def update_mouse(self, event):
        if event.inaxes == self.ax[0]:
            x_pixel, y_pixel = self.event_to_pixel(event)

            self.object['track_x'].value.set(x_pixel)
            self.object['track_y'].value.set(y_pixel)
            self.object['track_z'].value.set(float(f"{self.Z[y_pixel-1, x_pixel-1]:.2f}"))

        elif event.inaxes == self.ax[1]:
            puntx = round(event.xdata); punty = round(event.ydata)

            self.object['track_xaxis'].value.set(puntx)
            self.object['track_yaxis'].value.set(punty)

        else:
            for key in ['track_x', 'track_y', 'track_z', 'track_xaxis', 'track_yaxis']: 
                self.object[key].value.set('')
    
    def limit_pixels(self):
        x0 = int(self.zoom.xlims[0]/self.mida[0]*self.dims[1])
        x1 = int(self.zoom.xlims[1]/self.mida[0]*self.dims[1])
        y0 = int(self.zoom.ylims[0]/self.mida[1]*self.dims[0])
        y1 = int(self.zoom.ylims[1]/self.mida[1]*self.dims[0])
        return x0, x1, y0, y1
    
    def plt_map(self, event = None, attr = None):
        if attr:
            setattr(self, attr, event.widget.get())
            if attr == 'nommag': self.label['track_z'].config(text = event.widget.get())
        
        self.object['pic1'].configure(state='disabled')
        self.object['pic2'].configure(state='disabled')
        if hasattr(self, 'fits'): 
            pics = list(self.fits[self.nomfit].keys())
            pics.remove('bkg')
        else: 
            for element in ['map', 'fits', 'mag']: self.object[element].configure(state='disabled')
        
        match self.nommap:
            case 'Intensitat':
                self.Z = self.IntInt
                self.object['mag'].configure(values = ["Intensitat"])
                self.object['mag'].set("Intensity")
                self.nommag = "Intensity"
            case 'Pics':
                match self.pic1:
                    case 'bkg' | 'Tots': 
                        self.object['mag'].configure(values = ["Intensity"])
                        self.nommag = 'Intensity'
                    case _: self.object['mag'].configure(values = peakAttr)

                pics.extend(['bkg', 'Tots'])
                self.object['pic1'].configure(values = pics, state='readonly')
                if self.pic1 not in pics: 
                    self.object['pic1'].set(pics[0])
                    self.pic1 = pics[0]
                if self.pic1 == 'Tots': 
                    self.Z = np.zeros_like(self.Z)
                    for key, peak in self.fits[self.nomfit].items():
                        if key == 'bkg': continue

                        self.Z += peak.Intensity

                else: self.Z = getattr(self.fits[self.nomfit][self.pic1], self.nommag).copy()
            case 'P2-P1' | 'P2/P1':
                if self.pic1 not in pics:
                    self.object['pic1'].set(pics[0])
                    self.pic1 = pics[0]

                if self.pic2 not in pics:
                    self.object['pic2'].set(pics[-1])
                    self.pic2 = pics[-1]

                self.object['mag'].configure(values=peakAttr)

                val1 = getattr(self.fits[self.nomfit][self.pic1], self.nommag)
                val2 = getattr(self.fits[self.nomfit][self.pic2], self.nommag)

                self.Z = ops[self.nommap](val2, val1)
                self.Z = val2 - val1 if self.nommap == 'P2-P1' else val2 / val1

                self.object['pic1'].configure(values=pics, state='readonly')
                self.object['pic2'].configure(values=pics, state='readonly')
            case _:
                for magnitud in VectorExtraMags.values():
                    magsCombination = [getattr(self.fits[self.nomfit][pic], mg) for mg, pic in zip(magnitud.magnituds, magnitud.pics)]
                    if type(magnitud.operacio) is dict:
                        xdata = self.specs["nm"].xdata
                        idxInf, idxSup = find_nearest(xdata, magnitud.operacio["Range"])
                        magnitud.Intensity = np.array([np.sum(spec[idxInf:idxSup]) for spec in self.spectra]).reshape(*self.dims)
                        magnitud.magnituds=["Area"]
                    else:
                        magnitud.Intensity = magnitud.operacio(*magsCombination)
                
                mags = np.unique(magnitud.magnituds)
                self.object['mag'].configure(values = mags)
                self.object['mag'].set(mags[0])
                self.nommag = mags[0]
                self.Z = VectorExtraMags[self.nommap].Intensity.copy()

        units = self.specs[self.spec_type].units[self.nommag]
        if self.nommap == 'P2/P1': units = ''
        valors = self.Z[~np.isnan(self.Z)]
        self.limInf, self.limSup = lims_outliers(valors)

        mapa.update_map(self.image, self.color[self.nommag], self.Z, (self.limInf, self.limSup), units, mida = self.mida, cbar = self.cax)
        self.zoom.midaBase = self.mida
        self.zoom._base_size()
        self.object['map_limInf'].value.set(self.limInf)
        self.object['map_limSup'].value.set(self.limSup)
        self.object['cmap'].value.set(self.color[self.nommag])
        self.ax[0].set_title(f'{self.object["map"].get()} {self.object["pic1"].get() if self.object["map"].get() == "Pic" else ""} {self.object["mag"].get()}')
        self.canvas.draw()
        
        if hasattr(self, 'posx') and hasattr(self, 'posy'): self.plot_spec()

    def on_click(self, event, mapa):
        if event.inaxes != mapa or event.xdata==None or event.ydata==None:
            return
        else:
            self.posx, self.posy = self.event_to_pixel(event)
            self.plot_spec()

    def plot_hist(self):
        def gaussiana(x, x0, sigma, I): #Gaussiana #sigma = FWHM / (2 * np.sqrt(2 * np.log(2)))
            return I * np.exp(-((x - x0) / sigma) ** 2 / 2)
        
        units = self.specs[self.spec_type].units[self.nommag] 
        label = f'{self.nommag} ({units})'
        x0, x1, y0, y1 = self.limit_pixels()
        valors = self.Z[y0:y1, x0:x1].flatten()

        punts = np.linspace(self.limInf, self.limSup, 100)
        HistogramaMapa, limits = np.histogram(valors, bins = 15, range=[self.limInf, self.limSup], density=False)

        centres = (limits[:-1] + limits[1:]) / 2
        pas = 0.9 * (centres[1] - centres[0])
        p_ini = [np.median(valors), np.percentile(valors, 75)-np.percentile(valors, 25), np.max(HistogramaMapa)]
        limits = ([0, 0, 0], [+np.inf, +np.inf, +np.inf])
        
        #Gràfica histograma
        fig2, ax2 = plt.subplots()
        ax2.bar(centres, HistogramaMapa, width=pas, fc='tab:blue',align="center")
        ax2.set(xlabel=label, ylabel='Frequency', title=f'{self.nommap} {self.nommag}')
        fig2.show()
        
        print(f'Ajustant {self.nommap} {self.nommag}')
        try:
            popt, pcov = scopt.curve_fit(gaussiana, centres, HistogramaMapa,\
                p0=p_ini, bounds=limits)
        except RuntimeError:
            print("\n\t\tERROR! L'ajust per mínims quadrats ha fallat.\n")
            return
        
        ax2.plot(punts, gaussiana(punts, *popt), '-', color='tab:red')      
        perr = np.sqrt(np.diag(pcov))

        yint = (ax2.get_ylim()[1]-ax2.get_ylim()[0])
        posx = (ax2.get_xlim()[1]-ax2.get_xlim()[0])*0.6+ax2.get_xlim()[0]
        posy = yint*0.8+ax2.get_ylim()[0]
        ax2.annotate(fr'$x_0$ = {popt[0]:.4g} $\pm$ {perr[0]:.2g} {units if self.nommap != "Ràtio (P2-P1)" else ""}', xy=(posx, posy), xycoords='data')
        ax2.annotate(fr'$\sigma$ = {popt[1]:.3g} $\pm$ {perr[1]:.2g} {units if self.nommap != "Ràtio (P2-P1)" else ""}', xy=(posx, posy-yint*0.1), xycoords='data')    
        ax2.annotate(fr'$I_{{max}}$ = {popt[2]:.3g} $\pm$ {perr[2]:.2g}', xy=(posx, posy-yint*0.2), xycoords='data')
    
    def plot_spec(self):
        self.ax[1].clear()
        self.etiquette = {}
        pos = self.posy - 1, self.posx - 1
        idx = pos[1] + pos[0] * self.dims[1]
        self.I = self.spectra[idx,:].copy()
        spec = self.specs[self.spec_type]

        if hasattr(self,'fits'): 
            fit = self.fits[self.nomfit]
            xdata = spec.xdata[self.fit_start:self.fit_end]
            bkg = fit['bkg']

            if self.object['spec_bkg'].value.get(): 
                bkgdata = fit['bkg'].data(pos)
            else: 
                bkgdata = np.zeros_like(bkg.xfit)
                self.I[self.fit_start:self.fit_end] -= fit['bkg'].data(pos)
        else: 
            bkgdata = np.zeros_like(spec.xdata)
            xdata = spec.xdata

        match self.nommap:
            case 'Intensitat': pass
            case 'Pics': 
                match self.pic1:
                    case 'bkg': 
                        self.ax[1].fill_between(xdata, bkgdata, 0, color = 'tab:blue', alpha=0.6)
                    case 'Tots':
                        params = []
                        for key, peak in fit.items():
                            if key == 'bkg': 
                                self.ax[1].fill_between(xdata, bkgdata, 0, color = 'tab:blue', alpha=0.6)
                                continue
                            self.etiquette[key] = plot_peak(xdata, self.ax[1], peak, bkgdata, pos)
                            params.extend([peak.PeakCenter[*pos], peak.FWHM[*pos], peak.Intensity[*pos]])

                        yfit = np.zeros_like(xdata)
                        for key, peak in self.fits[self.nomfit].items(): 
                            if key == 'bkg' and not self.object['spec_bkg'].value.get(): continue
                            yfit += peak.data(pos)

                        self.ax[1].plot(xdata, yfit, 'k-', lw=2, label='Fit total')

                    case _: self.etiquette[self.pic1] = plot_peak(xdata, self.ax[1], fit[self.pic1], bkgdata, pos)

            case 'P2-P1' | 'P2/P1':
                for element in [self.pic1, self.pic2]: self.etiquette[element] = plot_peak(xdata, self.ax[1], fit[element], bkgdata, pos)
            case _:
                for element in VectorExtraMags[self.nommap].pics:
                    self.etiquette[element] = plot_peak(xdata, self.ax[1], fit[element], bkgdata, pos)
        
        self.dades, = self.ax[1].plot(spec.xdata, self.I, zorder=0)
        self.dades.set_visible(self.object['spec_data'].value.get())
        for element in self.etiquette.values(): element.set_visible(self.object['spec_etiq'].value.get())
        
        self.ax[1].set_title(f"{spec.name} spectrum X={self.posx} Y={self.posy}")
        self.ax[1].set_xlabel(spec.xtitle)
        self.ax[1].set_ylabel(r'Intensity (uA)')
        self.ax[1].tick_params(direction = 'in')

        if not self.lims:
            self.lims['spec_left'], self.lims['spec_right'] = min(xdata), max(xdata)

        self.lims['spec_bot'], self.lims['spec_top'] = 0, 1.15*self.ax[1].get_ylim()[1]
        for key, value in self.lims.items(): self.object[key].value.set(round(value, 2))

        self.ax[1].set_xlim(self.lims['spec_left'], self.lims['spec_right'])
        self.ax[1].set_ylim(self.lims['spec_bot'], self.lims['spec_top'])
        
        self.canvas.draw()
        
    def save_spec(self):
        if not hasattr(self, 'I'): return
        ruta = self.folder / 'Spectra'
        ruta.mkdir(parents = True, exist_ok = True)
        nom = ruta / f'{self.folder.stem}_{self.posx}_{self.posy}'
        np.savetxt(f'{nom}.txt', np.c_[self.specs[self.spec_type].xdata, self.I], delimiter=';', fmt = ['%.4f', '%d'])
        pos = self.posy-1, self.posx-1
        if hasattr(self, 'fits'):
            ruta = f'{self.folder}_{self.posx}_{self.posy} - FIT.txt'
            fit = self.fits[self.nomfit]
            bkg = self.fits[self.nomfit]['bkg']
            peakdata = 0
            for peak in fit.values(): peakdata += peak.data(pos)
            bkgdata = bkg.data(pos)
            data = np.c_[bkg.xfit, peakdata, bkgdata, peakdata-bkgdata]
            with open(f'{nom} - FIT.txt', 'w', encoding='utf-8', newline='') as f:
                f.write(f"#Nom: {[self.nomfit]}\n")
                f.write(f"#Unitats: {[bkg.units]}\n")
                f.write(f"#Pics: {[key for key in fit.keys() if key != 'bkg']}\n")
                f.write(f"#Funcions: {[peak.type for key, peak in fit.items() if key != 'bkg']}\n")
                f.write(f"#Centres: {[str(peak.PeakCenter[*pos]) for key, peak in fit.items() if key != 'bkg']}\n")
                f.write(f"#FWHM: {[str(peak.FWHM[*pos]) for key, peak in fit.items() if key != 'bkg']}\n")
                f.write(f"#Intensitats: {[str(peak.Intensity[*pos]) for key, peak in fit.items() if key != 'bkg']}\n")
                f.write(f'# # # #\n')
                f.write(f"#Fons: {[bkg.type]}\n")
                f.write(f"#Variables: {[str(bkg.varbls[*pos])]}\n\n")
                header = [self.specs[self.spec_type].xtitle, "I (uA)", "bkg", "I-bkg"]
                np.savetxt(f, data, delimiter = '\t', fmt = '%.2f', header = '\t'.join(header))

if __name__ == "__main__":
    PintaMapesInterficie()
