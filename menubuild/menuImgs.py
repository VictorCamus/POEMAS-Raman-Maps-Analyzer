import numpy as np
from process import perfil as prf

from .base import BaseMenu
from tkinter import messagebox

class GestorImatges(BaseMenu): # Classe que gestiona les accions relacionades amb el zoom de les imatges.
    ordre = 10 # Atribut per a ordenar els menús (opcional)
    
    def __init__(self, app, get_current, set_current):
        super().__init__(app, get_current, set_current)

        self.p1 = {}; self.p2 = {}
        
    def registrar_menu(self, menu):
        accions = [
            ("Rotar en sentit horari", lambda: self._rotar(k = 1), "<Shift-R>"),
            ("Rotar en sentit antihorari", lambda: self._rotar(k = -1), "<Shift-L>"),
            ("Sincronitzar rotació", lambda: self._rot_sync(), None),
            ("Zoom manual", lambda: self._zoom_manual(), None),
            ("Sincronitzar zoom", lambda: self._zoom_sync(), None),
            ("SEPARATOR"),
            ("Desfer zoom", lambda: self._desfer_zoom(), None)
        ]
        
        self.create_menu("Operacions bàsiques", menu, accions)
        
    def _rotar(self, new_rot=0, k=0, file=None):
        if not self.comprova_fitxer(): return
        if not file: file = self.current_file
        channel = file.current_channel
        
        # --- Normalitzar rotació ---
        if k != 0: new_rot = (file.rot + k) % 4
        rot = (new_rot - file.rot) % 4
        file.rot = new_rot
        if rot == 0: return  # No cal fer res

        # --- Rotar canals ---
        for ch in file.channel.values(): ch.Z = np.rot90(ch.Z, k=rot)

        file.image.set_data(channel.Z)
        self._actualitzar_rotacio(file, rot)

    def _rotar_limits(self, xlims, ylims, Lx, Ly, rotation):
        match rotation:
            case 0: return xlims, ylims # 0º
            case 1: return (ylims,(Lx - xlims[1], Lx - xlims[0])) # 90º
            case 2: return ((Lx - xlims[1], Lx - xlims[0]), (Ly - ylims[1], Ly - ylims[0])) # 180º
            case 3: return ((Ly - ylims[1], Ly - ylims[0]), xlims) # 270º

    def _perfils_rotacio(self, file, rotation):
        Nx, Ny = file.N
        
        for num in range(len(file.get_line)):
            p1 = file.get_line[num][0]
            p2 = file.get_line[num][-1]
            
            match rotation:
                case 0: return
                case 1:
                    self.p1[num] = [p1[1], Nx - p1[0]]
                    self.p2[num] = [p2[1], Nx - p2[0]]
                case 2:
                    self.p1[num] = [p1[1], p1[0]]
                    self.p2[num] = [p2[1], p2[0]]                    
                case 3:
                    self.p1[num] = [Ny - p1[1], p1[0]]
                    self.p2[num] = [Ny - p2[1], p2[0]]
            
            file.get_line[num] = prf.get_line(self.p1[num], self.p2[num])

    def _actualitzar_rotacio(self, file, rot):
        if hasattr(file, 'mask'):
            file.mask = np.rot90(file.mask, rotation=rot)
            file.mask.set_data(file.mask)
        if hasattr(file, 'get_line'): self._perfils_rotacio(file, rotation=rot)

        new_midaX, new_midaY = file.midaBase  # Ja intercanviats en _rotar

        if hasattr(file, 'fletxa'):
            num = 0
            for fletxa in file.fletxa.values():
                fletxa.elimina()
                # Utilitza les coordenades actualitzades de p1 i p2
                start = [self.p1[num][0] * new_midaY / file.N[1], self.p1[num][1] * new_midaX / file.N[0]]
                end = [self.p2[num][0] * new_midaY / file.N[1], self.p2[num][1] * new_midaX / file.N[0]]
                fletxa.start = start
                fletxa.end = end
                fletxa.dibuixa()
                num += 1     

        file.zoom.xylims = self._rotar_limits(*file.zoom.xylims, *file.midaBase, rot)
        
        if rot % 2 == 1:
            file.midaBase = file.midaBase[::-1]
            file.N = file.N[::-1]   
        
        file.image.set_extent([0, file.midaBase[0], 0, file.midaBase[1]])

        if file.zoom.mida[0] != file.zoom.mida[1]: file.zoom._resize()

    def _rot_sync(self):
        if not self.comprova_fitxer(): return
        file = self.current_file

        for f in self.files.values():
            if f is not file:
                self._rotar(new_rot=file.rot, file=f)

    def _zoom_manual(self):
        
        def set_lims(left = None, right = None, bottom = None, top = None, file = None, axis = 'Eix X'): # Aplica la sincronització del zoom a tots els altres mapes.
            if axis == 'Eix X':
                l_ref, r_ref = file.zoom.xlims
                if left is None: left = l_ref
                if right is None: right = r_ref

                if left < 0: 
                    left = 0
                    self.widgets[axis]["left"].value.set(left)
                if right > file.midaBase[0]: 
                    right = file.midaBase[0]
                    self.widgets[axis]["right"].value.set(right)

                if left >= right:
                    messagebox.showerror("Límits del mapa",
                    "El límit superior ha de ser major que l'inferior.")
                    return
                
                file.zoom.xlims = (left, right)
            
            elif axis == 'Eix Y':
                b_ref, t_ref = file.zoom.ylims
                if bottom is None: bottom = b_ref
                if top is None: top = t_ref
                
                if bottom < 0: 
                    bottom = 0
                    self.widgets[axis]["bottom"].value.set(bottom)
                if top > file.midaBase[1]: 
                    top = file.midaBase[1]
                    self.widgets[axis]["top"].value.set(top)

                if bottom >= top:
                    messagebox.showerror(
                    "Límits del mapa",
                    "El límit superior ha de ser major que l'inferior."
                    )
                    return
                
                file.zoom.ylims = (bottom, top)
            
            file.zoom._resize()

        if not self.comprova_fitxer(): return
        file = self.current_file

        tabConfig = [
            ("Eix X", file.zoom.xlims, set_lims, "left", "right"),
            ("Eix Y", file.zoom.ylims, set_lims, "bottom", "top"),
        ]

        def _grid_lims(axis, getter, setter, lim_inf, lim_sup):
            return [
                # Estructura: ((var_name, var_type), (label, object), setter, {getter, **extra})
                ((lim_inf, float, getter[0]), ("Límit inferior:", 'entry'), (setter, "kwargs", {'file': file, 'axis': axis})),
                ((lim_sup, float, getter[1]), ("Límit superior:", 'entry'), (setter, "kwargs", {'file': file, 'axis': axis})),
            ]
        
        self.widgets, _ = self.create_window("Editar eixos (Límits)", gridBuilder = _grid_lims, tabConfig = tabConfig)
    
    def _zoom_sync(self):
        if not self.comprova_fitxer(): return
        file = self.current_file

        for f in self.files.values():
            if f.N != file.N and f.midaBase != file.midaBase:
                messagebox.showerror("Error", "Les dimensions dels arxius són diferents")
                return
            if f is not file:
                f.zoom.xylims = file.zoom.xylims

    def _desfer_zoom(self): # Desfés el zoom de totes les pestanyes obertes.       
        if not self.comprova_fitxer(): return
        file = self.current_file
        file.zoom._base_size()