from tkinter.ttk import Frame
from tkinter import messagebox
from .labels import build_grid
from drawing.colormap import cmaps

# Fitxer que crea la capçalera per a les pestanyes del notebook.
# Conté també les mètodes per afegir etiquetes, camps d'entrada i comboboxes a la capçalera.

class GestorCapçalera:
    def __init__(self, filedata):
        self.filedata = filedata
        self.view = CrearCapçalera(parent=filedata.frame, controller=self)

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
        
    def _redraw(self, cmap = False, lims = False):
        file = self.filedata
        ch = self.filedata.current_channel

        if cmap: 
            file.image.set_cmap(ch.color.cmap)
            file.cbar.limInf.set_color(ch.color.limInf)
            file.cbar.limSup.set_color(ch.color.limSup)
        
        if lims:
            units = ch.dades.units
            file.image.set_clim(*ch.lims)
            file.cbar.limInf.set_text(f"{ch.lims[0]:g}" + (f" {units}" if units else ""))
            file.cbar.limSup.set_text(f"{ch.lims[1]:g}" + (f" {units}" if units else ""))
            
        file.canvas.draw_idle()

class CrearCapçalera:
    def __init__(self, parent, controller):
        self.frame = Frame(parent)
        self.controller = controller
        self.channel = self.controller.filedata.current_channel

        self.frame.grid(row=1, column=0, sticky='ew', pady = 5)
        self.frame.columnconfigure(0, weight=1)
        
        self._editar_limits()
        self._color_mapa_escala()

      
    def _color_mapa_escala(self): # Afegeix controls per canviar el color del mapa i de l'escala.
        def _grid_color():
            return [
                (("cmap_c", str, self.channel.tipus),
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