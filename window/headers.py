from tkinter.ttk import Frame, Label, Entry, Combobox
from tkinter import messagebox, IntVar, BooleanVar, DoubleVar, StringVar, Checkbutton
from .labels import build_grid
from drawing.colormap import cmaps
from drawing.colormap import cmaps_matplotlib
from drawing import mapdraw as mapa
import numpy as np

# Fitxer que crea la capçalera per a les pestanyes del notebook.
# Conté també les mètodes per afegir etiquetes, camps d'entrada i comboboxes a la capçalera.

class GestorHeaderAFM:
    def __init__(self, filedata):
        self.filedata = filedata
        self.view = CrearHeaderAFM(parent=filedata.frame, controller=self)

    def set_channel(self, channel):
        self.view.refresh(channel)
        self._redraw(cmap = True, lims = True)

    def on_cmap_change(self, value):
        ch = self.filedata.current_channel
        ch.color.cmap_c = value
        self._redraw(cmap = True)
    
    def on_rev_change(self, value, widget):
        ch = self.filedata.current_channel
        if ch.color.cmap_r != value and ch.color.limSup != ch.color.limInf:
            ch.color.limInf, ch.color.limSup = ch.color.limSup, ch.color.limInf
            rb_climsup = widget["colSup"]
            rb_climsup.value.set(ch.color.limSup)
            
            rb_climinf = widget["colInf"]
            rb_climinf.value.set(ch.color.limInf)
            
        ch.color.cmap_r = value
        self._redraw(cmap = True)

    def on_lim_inf_change(self, value):
        ch = self.filedata.current_channel
        if value >= ch.lims[1]:
            messagebox.showerror(
                "Error en actualitzar la gràfica",
                "El límit inferior ha de ser menor que el superior."
            )
            
            return

        ch.lims[0] = value
        self._redraw(lims = True)
    
    def on_lim_sup_change(self, value):
        ch = self.filedata.current_channel
        if value <= ch.lims[0]:
            messagebox.showerror(
                "Error en actualitzar la gràfica",
                "El límit inferior ha de ser menor que el superior."
            )
            return

        ch.lims[1] = value
        self._redraw(lims = True)

    def on_spectra_lim_inf_change(self, value):
        channel = self.filedata.current_channel

        channel.spectra_lims[0] = value
        self._update_spectra_Z(channel)

    def on_spectra_lim_sup_change(self, value):
        channel = self.filedata.current_channel

        channel.spectra_lims[1] = value
        self._update_spectra_Z(channel)

    def on_scale_change(self, value):
        ch = self.filedata.current_channel
        ch.color.scale = value
        self.filedata.escala.color = ch.color.scale
        self.filedata.canvas.draw_idle()
        
    def on_col_sup_change(self, value):
        ch = self.filedata.current_channel
        ch.color.limSup = value
        self._redraw(cmap = True)
    
    def on_col_inf_change(self, value):
        ch = self.filedata.current_channel
        ch.color.limInf = value
        self._redraw(cmap = True)
        
    def _redraw(self, cmap = False, lims = False, Z = False):
        file = self.filedata
        ch = self.filedata.current_channel

        if cmap: 
            file.image.set_cmap(ch.color.cmap)
            file.cbar.limInf.set_color(ch.color.limInf)
            file.cbar.limSup.set_color(ch.color.limSup)
        
        if lims:
            file.image.set_clim(*ch.lims)
            file.cbar.limInf.set_text(f"{ch.lims[0]:g}" + (f" {ch.units}" if ch.units else ""))
            file.cbar.limSup.set_text(f"{ch.lims[1]:g}" + (f" {ch.units}" if ch.units else ""))

        if Z: file.image.set_data(ch.Z)

        file.canvas.draw_idle()

    def _update_spectra_Z(self, channel):
        x = channel.xdata['nm']
        spectra = channel.spectra

        lim_inf, lim_sup = channel.spectra_lims
        mask = ((x >= lim_inf) & (x <= lim_sup))

        channel.Z = np.nansum(spectra[:, :, mask], axis=2)
        channel.lims = np.percentile(channel.Z, [0.2, 99.8])
        self._redraw(lims = True, Z = True)

class CrearHeaderAFM:
    def __init__(self, parent, controller):
        self.frame = Frame(parent)
        self.controller = controller
        self.channel = self.controller.filedata.current_channel

        self.frame.grid(row=2, column=0, sticky='ew', pady = 5)
        self.frame.columnconfigure(0, weight=1)

        if self.channel.spectra is not None: self._editar_limits_spectra()
        self._editar_limits()
        self._color_mapa_escala()

    def _color_mapa_escala(self): # Afegeix controls per canviar el color del mapa i de l'escala.
        def _grid_color():
            return [
                (("cmap_c", str, self.channel.name),
                 ("Color mapa:", 'cb', {"options": cmaps}),
                 (self.controller.on_cmap_change, "args", {})),
                (("cscale", str, 'w'),
                 ("Color escala:", 'radiobutton', {"options": {'B': 'w', 'N': 'k'}, 'vertical': False}),
                 (self.controller.on_scale_change, "args", {})),
            ]

        def _grid_crev():
            return [
                (("cmap_r", bool, False),
                (None, 'radiobutton', {"options": {'N': False, 'R': True}, 'vertical': False}),
                (self.controller.on_rev_change, "args", {'widget': self.widgets_lims})),
            ]
        
        self.widgets_scale = build_grid(self.frame, _grid_color(), row=0, col=3, button=False)
        widget_rev = build_grid(self.frame, _grid_crev(), row=0, col=5, button=False)
        self.widgets_scale.update(widget_rev)

    def _editar_limits(self): # Afegeix controls per editar els límits del mapa.
        def _grid_lims():
            return [
                (("limSup", float, self.channel.lims[1]),
                 ("Valor màxim:", 'entry', {}),
                 (self.controller.on_lim_sup_change, "args", {})),
                (("limInf", float, self.channel.lims[0]),
                 ("Valor mínim:", 'entry', {}),
                 (self.controller.on_lim_inf_change, "args", {}))
            ]
        def _color_lims():
            return [
                (("colSup", str, self.channel.color.limSup),
                 (None, 'radiobutton', {'options': {'B': 'w', 'N': 'k'}, 'vertical': False}),
                 (self.controller.on_col_sup_change, "args", {})),
                (("colInf", str, self.channel.color.limInf),
                 (None, 'radiobutton', {'options': {'B': 'w', 'N': 'k'}, 'vertical': False}),
                 (self.controller.on_col_inf_change, "args", {}))
            ]

        self.widgets_lims = build_grid(self.frame, _grid_lims(), row=0, col=7, button=False)
        col_lims = build_grid(self.frame, _color_lims(), row=0, col=9, button=False)
        self.widgets_lims.update(col_lims)

    def _editar_limits_spectra(self):
        def _grid_lims_spectra():
            return [
                (("LimSup", float, self.channel.spectra_lims[1]),
                 ("Espectre màxim:", 'entry', {}),
                 (self.controller.on_spectra_lim_sup_change, "args", {})),

                (("LimInf", float, self.channel.spectra_lims[0]),
                 ("Espectre mínim:", 'entry', {}),
                 (self.controller.on_spectra_lim_inf_change, "args", {}))
            ]

        self.widgets_spectra_lims = build_grid(self.frame, _grid_lims_spectra(), row=0, col=1, button=False)

    def refresh(self, ch = None): # Canvia la capçalera en canviar de canal.
        if not ch: return

        # ---- 1. Actualitzar els comboboxes dels colors del mapa----
        combo_cmap = self.widgets_scale["cmap_c"]
        combo_cmap.set(ch.color.cmap_c)

        rb_cmap_rev = self.widgets_scale["cmap_r"]
        rb_cmap_rev.value.set(ch.color.cmap_r)

        # ---- 2. Actualitzar els comboboxes dels colors de l'escala ----
        rb_cscale = self.widgets_scale["cscale"]
        rb_cscale.value.set(ch.color.scale)
        
        rb_climsup = self.widgets_lims["colSup"]
        rb_climsup.value.set(ch.color.limSup)
        
        rb_climinf = self.widgets_lims["colInf"]
        rb_climinf.value.set(ch.color.limInf)
        
        # ---- 3. Actualitzar els camps d'entrada dels límits ----
        self.widgets_lims["limInf"].value.set(f"{ch.lims[0]:g}")
        self.widgets_lims["limSup"].value.set(f"{ch.lims[1]:g}")

        if self.channel.spectra is not None:
            for widget in self.widgets_spectra_lims.values():
                widget.grid() if ch.spectra is not None else widget.grid_remove()

class GestorHeaderRAMAN:
    def __init__(self, filedata, frame):
        self.file = filedata
        self.view = CrearHeaderRAMAN(parent=frame, controller=self)

    def new_cmap(self, event):
        self.file.image.set_cmap(event.widget.get())
        self.file.fig.canvas.draw()

    def new_spectype(self, event):
        self.file.spec_type = event.widget.get()
        self.file.label['track_xaxis'].configure(text=self.file.specs[self.file.spec_type].xtitle)
        if not hasattr(self.file, 'posx') or not hasattr(self.file, 'posy'): return
        self.file.lims = {}
        self.file.plot_spec()

    def set_speclims(self, event, key):
        self.file.lims[key] = float(event.widget.get())
        self.file.ax[1].set_xlim(self.file.lims['spec_left'], self.file.lims['spec_right'])
        self.file.ax[1].set_ylim(self.file.lims['spec_bot'], self.file.lims['spec_top'])
        self.file.canvas.draw()

    def set_etiqs(self):
        if not hasattr(self.file, 'etiquette'): return

        for element in self.file.etiquette.values(): element.set_visible(self.view.object['spec_etiq'].value.get())
        self.file.canvas.draw_idle()

    def mostrar_dades(self):
        if not hasattr(self.file, 'dades'):
            return

        self.file.dades.set_visible(self.view.object['spec_data'].value.get())
        self.file.canvas.draw_idle()

    def map_lims(self, event, lim = 'Inf'):
        match lim:
            case 'Inf': self.file.limInf = float(event.widget.get())
            case 'Sup': self.file.limSup = float(event.widget.get())

        lims = self.file.limInf, self.file.limSup
        mapa.update_cbar(self.file.cax, lims, units = self.file.specs[self.file.spec_type].units[self.file.nommag] if not self.file.nommap == 'Ràtio (P2/P1)' else '')
        self.file.image.set_clim(*lims)
        self.file.canvas.draw()

class CrearHeaderRAMAN:
    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller
        self.label = {}
        self.object = {}

        marcTop = Frame(self.parent)
        marcTop.grid(row = 0, column = 0, sticky = 'ew')
        marcTop.grid_columnconfigure(0, minsize=200)

        opcionsMap = ["Intensitat", "Pics", "P2-P1", "P2/P1"]
        self.label['map'] = Label(marcTop, text='Mapa:')
        self.label['map'].grid(row=0, column=1, pady=5, padx=10, sticky='e')
        self.object['map'] = Combobox(marcTop, textvariable=StringVar(marcTop, value=opcionsMap[0]), values=opcionsMap,
                                          state='readonly', width=8)
        self.object['map'].grid(row=0, column=2, pady=5, padx=0, sticky='w')
        self.object['map'].bind("<<ComboboxSelected>>", lambda event: self.controller.plt_map(event, attr='nommap'))
        self.object['map'].current(0)

        self.label['fits'] = Label(marcTop, text='Ajust:')
        self.label['fits'].grid(row=0, column=3, pady=5, padx=10, sticky='e')
        self.object['fits'] = Combobox(marcTop, textvariable=StringVar(marcTop, value=[]), values=[], state='readonly',
                                           width=12)
        self.object['fits'].grid(row=0, column=4, pady=5, padx=0, sticky='w')
        self.object['fits'].bind("<<ComboboxSelected>>", lambda event: self.plt_map(event, attr='nomfit'))

        self.label['pic1'] = Label(marcTop, text='P1:', width=3)
        self.label['pic1'].grid(row=0, column=5, pady=5, padx=5, sticky='e')
        self.object['pic1'] = Combobox(marcTop, textvariable=StringVar(marcTop, value=[]), values=[], state='readonly',
                                           width=5)
        self.object['pic1'].grid(row=0, column=6, pady=5, padx=0, sticky='w')
        self.object['pic1'].bind("<<ComboboxSelected>>", lambda event: self.plt_map(event, attr='pic1'))

        self.label['pic2'] = Label(marcTop, text='P2:', width=3)
        self.label['pic2'].grid(row=0, column=7, pady=5, padx=5, sticky='e')
        self.object['pic2'] = Combobox(marcTop, textvariable=StringVar(marcTop, value=[]), values=[], state='readonly',
                                           width=5)
        self.object['pic2'].grid(row=0, column=8, pady=5, padx=0, sticky='w')
        self.object['pic2'].bind("<<ComboboxSelected>>", lambda event: self.plt_map(event, attr='pic2'))

        self.label['mag'] = Label(marcTop, text='Magnitud:')
        self.label['mag'].grid(row=0, column=10, pady=5, padx=10)
        self.object['mag'] = Combobox(marcTop, textvariable=StringVar(marcTop, value="Intensity"),
                                          values=["Intensity"], state='readonly', width=10)
        self.object['mag'].grid(row=0, column=11, pady=5, padx=0)
        self.object['mag'].bind("<<ComboboxSelected>>", lambda event: self.plt_map(event, attr='nommag'))
        self.object['mag'].current(0)

        marcTrack = Frame(self.parent)
        marcTrack.grid(row=1, column=0, sticky='ew')

        marcTrack.grid_columnconfigure(0, minsize=200)
        marcTrack.grid_columnconfigure(7, minsize=200)

        set_valuex = IntVar(marcTrack, value='')
        self.label['track_x'] = Label(marcTrack, text='X:', width=3)
        self.label['track_x'].grid(row=0, column=1, pady=5, padx=5, sticky='e')
        self.object['track_x'] = Entry(marcTrack, textvariable=set_valuex, state='readonly', width=3)
        self.object['track_x'].grid(row=0, column=2, pady=5, padx=0, sticky='w')
        self.object['track_x'].value = set_valuex

        set_valuey = IntVar(marcTrack, value='')
        self.label['track_y'] = Label(marcTrack, text='Y:', width=3)
        self.label['track_y'].grid(row=0, column=3, pady=5, padx=5, sticky='e')
        self.object['track_y'] = Entry(marcTrack, textvariable=set_valuey, state='readonly', width=3)
        self.object['track_y'].grid(row=0, column=4, pady=5, padx=0, sticky='w')
        self.object['track_y'].value = set_valuey

        set_valuez = DoubleVar(marcTrack, value='')
        self.label['track_z'] = Label(marcTrack, text='Intensity:', width=10)
        self.label['track_z'].grid(row=0, column=5, pady=5, padx=5, sticky='e')
        self.object['track_z'] = Entry(marcTrack, textvariable=set_valuez, state='readonly', width=10)
        self.object['track_z'].grid(row=0, column=6, pady=5, padx=0, sticky='w')
        self.object['track_z'].value = set_valuez

        set_valuexax = IntVar(marcTrack, value='')
        self.label['track_xaxis'] = Label(marcTrack, text='λ (nm)', width=6)
        self.label['track_xaxis'].grid(row=0, column=8, pady=5, padx=5, sticky='e')
        self.object['track_xaxis'] = Entry(marcTrack, textvariable=set_valuexax, state='readonly', width=5)
        self.object['track_xaxis'].grid(row=0, column=9, pady=5, padx=0, sticky='w')
        self.object['track_xaxis'].value = set_valuexax

        set_valueyax = IntVar(marcTrack, value='')
        self.label['track_yaxis'] = Label(marcTrack, text='Intensity (uA):', width=10)
        self.label['track_yaxis'].grid(row=0, column=10, pady=5, padx=5, sticky='e')
        self.object['track_yaxis'] = Entry(marcTrack, textvariable=set_valueyax, state='readonly', width=5)
        self.object['track_yaxis'].grid(row=0, column=11, pady=5, padx=0, sticky='w')
        self.object['track_yaxis'].value = set_valueyax

        marcLims = Frame(self.parent)
        marcLims.grid(row=2, column=0, sticky="nsew")

        set_valueCM = DoubleVar(marcLims, value='hot')
        self.label['cmap'] = Label(marcLims, text='Color:', width=5)
        self.label['cmap'].grid(row=0, column=1, pady=5, padx=5, sticky='e')
        self.object['cmap'] = Combobox(marcLims, textvariable=set_valueCM, values=cmaps_matplotlib, state='readonly',
                                           width=8)
        self.object['cmap'].grid(row=0, column=2, pady=5, padx=0, sticky='w')
        self.object['cmap'].bind("<<ComboboxSelected>>", self.controller.new_cmap)
        self.object['cmap'].value = set_valueCM

        set_valueMS = DoubleVar(marcLims, value='')
        self.label['map_limSup'] = Label(marcLims, text='Límit superior:', width=12)
        self.label['map_limSup'].grid(row=0, column=3, pady=5, padx=5, sticky='e')
        self.object['map_limSup'] = Entry(marcLims, textvariable=set_valueMS, width=6)
        self.object['map_limSup'].grid(row=0, column=4, pady=5, padx=0, sticky='w')
        self.object['map_limSup'].bind('<Return>', lambda e: self.controller.map_lims(e, lim='Sup'))
        self.object['map_limSup'].value = set_valueMS

        set_valueMI = DoubleVar(marcLims, value='')
        self.label['map_limInf'] = Label(marcLims, text='Límit inferior:', width=12)
        self.label['map_limInf'].grid(row=1, column=3, pady=5, padx=5, sticky='e')
        self.object['map_limInf'] = Entry(marcLims, textvariable=set_valueMI, width=6)
        self.object['map_limInf'].grid(row=1, column=4, pady=5, padx=0, sticky='w')
        self.object['map_limInf'].bind('<Return>', lambda e: self.controller.map_lims(e, lim='Inf'))
        self.object['map_limInf'].value = set_valueMI

        set_valueL = DoubleVar(marcLims, value='')
        self.label['laser'] = Label(marcLims, text='λ₀ (nm):', width=7)
        self.label['laser'].grid(row=0, column=6, pady=5, padx=5, sticky='e')
        self.object['laser'] = Entry(marcLims, textvariable=set_valueL, width=6, state='readonly')
        self.object['laser'].grid(row=0, column=7, pady=5, padx=0, sticky='w')
        self.object['laser'].value = set_valueL

        self.spec_type = 'nm'
        set_valueST = DoubleVar(marcLims, value='nm')
        self.label['spec_type'] = Label(marcLims, text='Unitats:', width=7)
        self.label['spec_type'].grid(row=1, column=6, pady=5, padx=5, sticky='e')
        self.object['spec_type'] = Combobox(marcLims, textvariable=set_valueST, values=['nm', 'eV', '1/cm'],
                                            state='readonly', width=4)
        self.object['spec_type'].grid(row=1, column=7, pady=5, padx=0, sticky='w')
        self.object['spec_type'].bind("<<ComboboxSelected>>", self.controller.new_spectype)
        self.object['spec_type'].value = set_valueST

        self.lims = {}
        set_valueLeft = DoubleVar(marcLims, value=0)
        self.label['spec_xaxis'] = Label(marcLims, text='Eix X:', width=6)
        self.label['spec_xaxis'].grid(row=0, column=8, pady=5, padx=5, sticky='e')
        self.object['spec_left'] = Entry(marcLims, textvariable=set_valueLeft, width=6)
        self.object['spec_left'].grid(row=0, column=9, pady=5, padx=0, sticky='w')
        self.object['spec_left'].bind('<Return>', lambda e: self.controller.set_speclims(e, key='spec_left'))
        self.object['spec_left'].value = set_valueLeft

        set_valueRight = DoubleVar(marcLims, value=1)
        self.object['spec_right'] = Entry(marcLims, textvariable=set_valueRight, width=6)
        self.object['spec_right'].grid(row=0, column=10, pady=5, padx=0, sticky='w')
        self.object['spec_right'].bind('<Return>', lambda e: self.controller.set_speclims(e, key='spec_right'))
        self.object['spec_right'].value = set_valueRight

        set_valueBot = DoubleVar(marcLims, value=0)
        self.label['spec_yaxis'] = Label(marcLims, text='Eix Y:', width=6)
        self.label['spec_yaxis'].grid(row=1, column=8, pady=5, padx=5, sticky='e')
        self.object['spec_bot'] = Entry(marcLims, textvariable=set_valueBot, width=6)
        self.object['spec_bot'].grid(row=1, column=9, pady=5, padx=0, sticky='w')
        self.object['spec_bot'].bind('<Return>', lambda e: self.controller.set_speclims(e, key='spec_bot'))
        self.object['spec_bot'].value = set_valueBot

        set_valueTop = DoubleVar(marcLims, value=1)
        self.object['spec_top'] = Entry(marcLims, textvariable=set_valueTop, width=6)
        self.object['spec_top'].grid(row=1, column=10, pady=5, padx=0, sticky='w')
        self.object['spec_top'].bind('<Return>', lambda e: self.controller.set_speclims(e, key='spec_top'))
        self.object['spec_top'].value = set_valueTop

        set_valueDades = BooleanVar(marcLims, value=True)
        self.object['spec_data'] = Checkbutton(marcLims, text="Dades", variable=set_valueDades, command=self.controller.mostrar_dades,
                                               indicatoron = True)
        self.object['spec_data'].grid(row=0, column=11, pady=5, padx=5, sticky='e')
        self.object['spec_data'].value = set_valueDades

        set_valueBkg = BooleanVar(marcLims, value=True)
        self.object['spec_bkg'] = Checkbutton(marcLims, text="Fons", variable=set_valueBkg, command=self.controller.mostrar_dades)
        self.object['spec_bkg'].grid(row=1, column=11, pady=5, padx=5, sticky='e')
        self.object['spec_bkg'].value = set_valueBkg

        set_valueEtiq = BooleanVar(marcLims, value=True)
        self.object['spec_etiq'] = Checkbutton(marcLims, text="Etiquetes", variable=set_valueEtiq, command=self.controller.set_etiqs,
                                               indicatoron = True)
        self.object['spec_etiq'].grid(row=1, column=12, pady=5, padx=5, sticky='e')
        self.object['spec_etiq'].value = set_valueEtiq

        marcLims.grid_columnconfigure(0, minsize=200)
        marcLims.grid_columnconfigure(5, minsize=100)