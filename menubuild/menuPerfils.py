from matplotlib.pyplot import close
import shutil
import stat
import numpy as np

from drawing.arrows import FletxaInteractiva
from drawing.plots import base_plot
from tkinter import messagebox, Button, filedialog
from .base import BaseMenu
from window import BaseFigureWindow
from pathlib import Path
from classes.file import ProfileData
from process.basics import get_line

class GestorPerfils(BaseMenu):  # Classe que gestiona les accions relacionades amb els perfils de fletxes.
    ordre = 30
    
    def __init__(self, app, get_current, set_current):
        super().__init__(app, get_current, set_current)  # Inicialitza la classe base

        self.color = ['r','b','g','orange','y','cyan','pink','k']

    def registrar_menu(self, menu):
        accions = [
            ('Afegir', lambda: self._afegir_perfils(), '<Shift-P>'),
            ('Sincronitzar perfils', lambda: self._prfs_sync(), None),
            ('Guardar', lambda: self.save_file(func = self._guardar_perfil), '<Control-p>'),  
            ('Guardar tots els fitxers', lambda: self.save_file(func = self._guardar_perfil, tots = True), '<Control-Shift-P>'),
            ('Mostrar perfils', lambda: self.obrir_mostrar_perfils(), None),
            ('SEPARATOR'),
            ('Esborrar', lambda: self._esborrar_perfils(), '<Control-Alt-p>'),
        ]
        
        self.create_menu("Perfils", menu, accions)  # Crida a la funció comuna d'afegir menú
    
    def obrir_mostrar_perfils(self):
        if not self.comprova_fitxer(): return
        if not list(key for key, f in self.files.items() if f.profile is not None):
            messagebox.showinfo("Informació", "No hi ha cap perfil dibuixat.")
            return
        
        MostrarPerfils(self)

    def _prfs_sync(self):
        if not self.comprova_fitxer(): return
        file = self.current_file

        if file.profile is None: return
        
        for f in self.files.values():
            if f is file: continue
            
            if f.N != file.N and f.midaBase != file.midaBase:
                messagebox.showwarning("Atenció", f"El fitxer '{f.name}' té una mida diferent i no es poden propagar els perfils.")
                continue
            
            f.profile = {num: ProfileData(prof.line, prof.length) for num, prof in file.profile.items()}
            for num, prof in f.profile.items():
                prof.create_arrow(num, f.axis, f.N, f.midaBase)

    def _afegir_perfils(self): # Afegeix un perfil de fletxa a la pestanya actual.
                
        def fer_perfils(file, channel, num):

            def quan_fletxa_estiga_llesta(pixels, length, file = file, num = num):
                profile.line = get_line(*pixels)
                profile.length = length

                file.profile[num] = profile

            profile = ProfileData()
            profile.arrow = FletxaInteractiva(file.axis, channel.Z, num+1, file.midaBase,
                self.color[num % 8], on_fletxa_finalitzada=quan_fletxa_estiga_llesta)
            
        if not self.comprova_fitxer(): return
        file, channel = self.element_obert()

        if channel.name == 'Grain':
            messagebox.showinfo("Informació", "No dibuixeu perfils sobre la pestanya GRAIN.")
            return

        nprof = 0 if file.profile is None else len(file.profile)
        if nprof == 0: file.profile = {}
        fer_perfils(file, channel, nprof)
        
    def _guardar_perfil(self, file, fig, ax): # Guarda els perfils dibuixats en fitxers de perfil.
        if file.profile is None:
            messagebox.showerror("Error en guardar els perfils", "No hi ha cap perfil dibuixat")
            return False

        profile = file.profile
        nprof = len(profile)

        path_profile = file.folder / 'Perfils'
        if path_profile.exists():
            shutil.rmtree(path_profile, onerror=self._handle_remove_readonly)

        ax.set_xlabel(r'Length ($\mu$m)')
        fig.subplots_adjust(left=0.2, bottom=0.2)

        if nprof > 1:
            perfils_fig, perfils_axis = base_plot(r'Length ($\mu$m)', '', dim=(6,4))        
            perfils_fig.subplots_adjust(left=0.2, bottom=0.2)
        
        folders = {}
        for num in range(nprof):
            num += 1
            folders[num] = path_profile / f'Perfil - {num}'
            folders[num].mkdir(parents=True)

        for ch in file.channel.values():
            if ch.name == 'Grain': continue
            y_min = np.inf; y_max = -np.inf; length_max = 0

            for num, prof in profile.items():
                ax.set_ylabel(ch.ax_title)
                punts, dades, line = prof.plot(num, ax, ch.Z)

                prof_path = folders[num+1] / f'{ch.name} - P{num+1}'
                fig.savefig(f'{prof_path}.jpg', dpi=80)
                np.savetxt(f'{prof_path}.txt', np.column_stack((punts, dades)), fmt='%.3f')

                line.remove()
                
                if nprof > 1:
                    y_min = np.minimum(y_min, dades.min()); y_max = np.maximum(y_max, dades.max()); length_max = np.maximum(length_max, prof.length)
                    perfils_axis.plot(punts, dades, color=color)
                
            if nprof > 1:
                perfils_axis.set_ylabel(ch.ax_title)
                perfils_axis.set_xlim(0, length_max)
                diff = (y_max-y_min)/15
                perfils_axis.set_ylim(y_min-diff, y_max+diff)
                perfils_fig.savefig(path_profile / f'{ch.name} - Perfils.jpg', dpi = 80)
                for line in perfils_axis.lines: line.remove()

        for ch in file.channel.values():
            file.redraw(ch)
            file.figure.savefig(path_profile / f'{ch.name}.jpg', bbox_inches='tight', dpi = 80)

        if nprof > 1: close(perfils_fig)

        return True
    
    def _handle_remove_readonly(self, func, path, exc_info):
        path = Path(path)
        path.chmod(stat.S_IWRITE)
        func(path)
        
    def _esborrar_perfils(self):
        if not self.comprova_fitxer(): return
        file = self.current_file
        if file.profile is None: return
        for prof in file.profile.values(): prof.arrow.elimina()
        file.profile = None

class MostrarPerfils(BaseFigureWindow):
    def __init__(self, gestor):
        super().__init__(gestor, "Mostrar histogrames", dim = (5,4))

        self.color = ['r', 'b', 'g', 'orange', 'y', 'cyan', 'pink', 'k']
        self.num = 0

        self.ax.set_xlabel(r'Length ($\mu$m)')
        self.ax.set_xlim(0, self.file.profile[0].length)
        self.ax.set_ylabel(self.channel.ax_title)
        
        self.line = {}
        _, _, self.line[0] = self.file.profile[0].plot(0, self.ax, self.channel.Z)
        
        self.lims = self.ax.get_ylim()
        self.widgets['inf'].value.set(round(self.lims[0], 0))
        self.widgets['sup'].value.set(round(self.lims[1], 0))

        self.fig_frame.grid(row=14, column=2, pady=10)

        btn_prev = Button(self.fig_frame, text="◀", command = lambda: self.toggle_plot(k = - 1) , font=("Arial", 16)) 
        btn_prev.pack(side="left", padx=2) 
        
        btn_next = Button(self.fig_frame, text="▶", command = lambda: self.toggle_plot(k = 1), font=("Arial", 16)) 
        btn_next.pack(side="left", padx=4)

        self.fig.tight_layout()
        self.canvas.draw_idle()

    @property
    def nprof(self):
        return len(self.file.profile)
    
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
        self.ax.set_ylabel(self.channel.ax_title)
        self.toggle_plot()

    def set_widgets(self):
        self.lims = self.ax.get_ylim()
        if hasattr(self, "widgets"):
            self.widgets['inf'].value.set(round(self.lims[0], 3))
            self.widgets['sup'].value.set(round(self.lims[1], 3))
            if self.num==self.nprof: self.widgets['profile'].value.set("Tots els perfils")
            else: self.widgets['profile'].value.set(self.num+1)

    def plot_lims(self, inf=None, sup=None):
        if inf is not None: self.lims = (inf, self.lims[1])
        if sup is not None: self.lims = (self.lims[0], sup)

        self.ax.set_ylim(self.lims)
        
        self.fig.tight_layout()
        self.fig.canvas.draw_idle()
    
    def toggle_plot(self, k = 0):
        if self.num == self.nprof:
            for line in self.line.values(): line.remove()
        else: self.line[self.num].remove()

        self.num += k

        if self.num == self.nprof:
            for num, prof in self.file.profile.items(): _, _, self.line[num] = prof.plot(num, self.ax, self.channel.Z)
        else: _, _, self.line[self.num] = self.file.profile[self.num].plot(self.num, self.ax, self.channel.Z)

        self.fig.tight_layout()
        self.fig.tight_layout()
        self.fig.canvas.draw_idle()
        self.set_widgets()

    def guardar(self, value):
        if self.num == self.nprof: text = f"{self.file.name} - {self.channel.name} Tots els perfils"
        else: text = f"{self.file.name} - {self.channel.name} Perfil {self.num+1}"
        ruta = filedialog.asksaveasfilename(
            parent = self.win_notebook,
            defaultextension=".png",
            initialfile=f"{text}.png",
            filetypes=[("PNG", "*.png")]
        )

        if not ruta: return 

        self.fig.savefig(ruta)
        p = Path(ruta)

        for i, line in enumerate(self.line.values(), start=1):
            txt_ruta = p.with_name(f"{self.file.name} - {self.channel.name} Perfil {i}.txt")
            x = line.get_xdata(); y = line.get_ydata()

            np.savetxt(txt_ruta, np.column_stack((x, y)), fmt="%.3f")
    
    def _grid(self):
        files = list(key for key, f in self.files.items() if f.profile is not None)
        if self.file.profile is None: self.file = files[0]

        channels = list(self.file.channel.keys())

        return [
            (("file", str, self.file.name), ("Arxiu:", 'cb', {"options": files}), (self.plot_file, "args")),
            (("channel", str, self.channel.name), ("Canal:", 'cb', {"options": channels}), (self.plot_channel, "args")),
            (("profile", str, '1'), ("Perfil:", 'entry', {"state": "readonly"}), (self, "attr")),
            (("inf", float, 0), ("Límit inferior:", 'entry'), (self.plot_lims, "kwargs")),
            (("sup", float, 1), ("Límit superior:", 'entry'), (self.plot_lims, "kwargs")),
            (("save", str, "Guardar"), ("Guardar dades i imatge:", 'button'), (self.guardar, "args"))
            ]