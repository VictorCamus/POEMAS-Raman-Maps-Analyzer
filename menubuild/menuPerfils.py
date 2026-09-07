import numpy as np
from pathlib import Path
from tkinter import messagebox, Button, filedialog, Frame

from drawing.arrows import FletxaInteractiva
from .base import BaseMenu
from window import BaseFigureWindow
from window.widgets import Widget
from classes.objects import ProfileData
from process.basics import get_line

class GestorPerfils(BaseMenu):  # Classe que gestiona les accions relacionades amb els perfils de fletxes.
    ordre = 30
    
    def __init__(self, app):
        super().__init__(app)  # Inicialitza la classe base

        self.color = ['r','b','g','orange','y','cyan','pink','k']

    def registrar_menu(self, menu):
        accions = [
            ('Afegir', lambda: self._add_prf(), '<Shift-P>'),
            ('Sincronitzar perfils', lambda: self._sync_prf(), None),
            ('Mostrar perfils', lambda: self.obrir_mostrar_perfils(), None),
            ('SEPARATOR'),
            ('Esborrar', lambda: self._close_prf(), '<Control-Alt-p>'),
        ]
        
        self.create_menu("Perfils", menu, accions)  # Crida a la funció comuna d'afegir menú
    
    def obrir_mostrar_perfils(self):
        if not self.comprova_fitxer(): return
        if not list(key for key, f in self.files.items() if f.objects.profiles):
            messagebox.showinfo("Informació", "No hi ha cap perfil dibuixat.")
            return
        
        MostrarPerfils(self)

    def _sync_prf(self):
        if not self.comprova_fitxer(): return
        file = self.current_file

        if not file.objects.profiles: return
        
        for f in self.files.values():
            if f is file: continue

            if not np.array_equal(f.geometry.N, file.geometry.N) or not np.array_equal(f.geometry.midaBase, file.geometry.midaBase):
                messagebox.showwarning("Atenció", f"El fitxer '{f.name}' té una mida diferent i no es poden propagar els perfils.")
                continue
            
            for num, prof in file.objects.profiles.items(): f.objects.profiles[num] = ProfileData(prof.line, prof.length)
            f.view.map.profiles.create_arrows()

    def _add_prf(self): # Afegeix un perfil de fletxa a la pestanya actual.
        if not self.comprova_fitxer(): return
        file = self.current_file
        map = file.view.map

        num = len(file.objects.profiles)

        def save_arrow(pixels, length, file = file, num = num):
            profile.line = get_line(*pixels)
            profile.length = length

            file.objects.profiles[num] = profile
            map.profiles.arrow[num] = arrow

        profile = ProfileData()
        arrow = FletxaInteractiva(map.axis, file.geometry.N, num + 1, file.geometry.midaBase,
                                  self.color[num % 8], on_fletxa_finalitzada=save_arrow)
        
    def _close_prf(self):
        if not self.comprova_fitxer(): return

        file = self.current_file
        file.objects.profiles.clear()
        file.view.map.profiles.elimina()

class MostrarPerfils(BaseFigureWindow):
    def __init__(self, gestor):
        super().__init__(gestor, "Mostrar histogrames", dim = (5,4))

        self.color = ['r', 'b', 'g', 'orange', 'y', 'cyan', 'pink', 'k']
        self.num = 0

        self.axis.set_xlabel(r'Length ($\mu$m)')
        self.axis.set_xlim(0, self.profiles[0].length)
        self.axis.set_ylabel(self.channel.ax_title)

        self.line = {}
        _, _, self.line[0] = self.file.view.map.profiles.plot(0, self.axis, self.channel.Z)
        
        self.lims = self.axis.get_ylim()
        self.widgets['inf'].value.set(round(self.lims[0], 0))
        self.widgets['sup'].value.set(round(self.lims[1], 0))

        buttons = Frame(self.fig_frame)
        buttons.pack(anchor="center", pady=5)

        btn_prev = Button(buttons, text="◀", command = lambda: self.toggle_plot(k = - 1) , font=("Arial", 16))
        btn_prev.pack(side="left", padx=2) 
        
        btn_next = Button(buttons, text="▶", command = lambda: self.toggle_plot(k = 1), font=("Arial", 16))
        btn_next.pack(side="left", padx=4)

        self.figure.tight_layout()
        self.canvas.draw_idle()

    @property
    def profiles(self):
        return self.file.objects.profiles

    @property
    def nprof(self):
        return len(self.profiles)
    
    @property
    def num(self):
        return self._num

    @num.setter
    def num(self, value):
        self._num = value % (self.nprof+1)


    def plot_file(self, value):
        self.file = value
        self.toggle_plot()
    
    def plot_channel(self, value):
        self.channel = value
        self.axis.set_ylabel(self.channel.ax_title)
        self.toggle_plot()

    def set_widgets(self):
        self.lims = self.axis.get_ylim()
        if hasattr(self, "widgets"):
            self.widgets['inf'].value.set(round(self.lims[0], 3))
            self.widgets['sup'].value.set(round(self.lims[1], 3))
            if self.num==self.nprof: self.widgets['profile'].value.set("Tots els perfils")
            else: self.widgets['profile'].value.set(self.num+1)

    def plot_lims(self, inf=None, sup=None):
        if inf is not None: self.lims = (inf, self.lims[1])
        if sup is not None: self.lims = (self.lims[0], sup)

        self.axis.set_ylim(self.lims)
        
        self.figure.tight_layout()
        self.figure.canvas.draw_idle()
    
    def toggle_plot(self, k = 0):
        if self.num == self.nprof:
            for line in self.line.values(): line.remove()
        else: self.line[self.num].remove()

        self.num += k

        if self.num == self.nprof:
            xmax = 0
            ymin = np.inf
            ymax = -np.inf

            for num in self.profiles:
                x, y, self.line[num] = self.file.view.map.profiles.plot(num, self.axis, self.channel.Z)

                xmax = np.nanmax([xmax, x[-1]])
                ymin = np.nanmin([ymin, np.nanmin(y)])
                ymax = np.nanmax([ymax, np.nanmax(y)])

            diff = (ymax - ymin) / 15 if ymax > ymin else 1

            self.axis.set_xlim(0, xmax)
            self.lims = (ymin - diff, ymax + diff)
            self.axis.set_ylim(self.lims)

        else: _, _, self.line[self.num] = self.file.view.map.profiles.plot(self.num, self.axis, self.channel.Z)

        self.figure.tight_layout()
        self.figure.tight_layout()
        self.figure.canvas.draw_idle()
        self.set_widgets()

    def guardar(self, value):
        if self.num == self.nprof: text = f"{self.file.name} - {self.channel.name} Tots els perfils"
        else: text = f"{self.file.name} - {self.channel.name} Perfil {self.num+1}"
        ruta = filedialog.asksaveasfilename(
            parent = self.main_frame,
            defaultextension=".png",
            initialfile=f"{text}.png",
            filetypes=[("PNG", "*.png")]
        )

        if not ruta: return

        self.figure.savefig(ruta, bbox_inches = 'tight')
        p = Path(ruta)

        if self.num == self.nprof:
            for i, line in enumerate(self.line.values(), start=1):
                self._save_prf_txt(p, line, i)
        else: self._save_prf_txt(p, self.line[self.num], self.num+1)

        map_route = p.parent / p.stem
        print(map_route)

        self.file.view.map.figure.savefig(f'{map_route} - MAP.png', bbox_inches='tight')

    def _save_prf_txt(self, path, line, i):
        txt_ruta = path.with_name(f"{self.file.name} - {self.channel.name} Perfil {i}.txt")
        x = line.get_xdata(); y = line.get_ydata()

        np.savetxt(txt_ruta, np.column_stack((x, y)), fmt="%.3f")

    def _create_widgets(self):
        files = list(key for key, f in self.files.items() if self.profiles is not None)
        if not self.profiles: self.file = files[0]

        channels = list(self.file.channel.keys())

        self.widgets = {
            "file": Widget(key="file", var_type=str, init=self.file.name,
                    text="Arxiu:", widget="cb", widget_kwargs={"options": files},
                    setter=self.plot_file),

            "channel": Widget(key="channel", var_type=str, init=self.channel.name,
                       text="Canal:", widget="cb", widget_kwargs={"options": channels},
                       setter=self.plot_channel),

            "profile": Widget(key="profile", var_type=str, init="1",
                       text="Perfil:", widget="entry", widget_kwargs={"state": "readonly"},
                       setter=self, mode="attr"),

            "inf": Widget(key="inf", var_type=float, init=0,
                   text="Límit inferior:", widget="entry",
                   setter=self.plot_lims, mode="kwargs"),

            "sup": Widget(key="sup", var_type=float, init=1,
                   text="Límit superior:", widget="entry",
                   setter=self.plot_lims, mode="kwargs"),

            "save": Widget(key="save", var_type=str, init="Guardar",
                    text="Guardar dades i imatge:", widget="button",
                    setter=self.guardar)}