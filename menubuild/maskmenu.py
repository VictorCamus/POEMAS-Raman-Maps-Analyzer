from matplotlib.colors import ListedColormap
from tkinter import messagebox

from window import GestorBase

class GestorMascara(GestorBase): # Classe que gestiona les accions relacionades amb les màscares de les imatges.
    def __init__(self, app):
        super().__init__(app)

        accions = [
            ('Afegir', lambda: self._afegir_mascara(), '<Control-m>'),
            ('Guardar', lambda: self._registrar_mascara(), '<Alt-m>'),
            ('Esborrar', lambda: self._esborrar_mascara(), '<Control-Shift-M>'),
        ]

        self.afegir_menu('Màscares', accions)

    def _afegir_mascara(self): # Afegeix una màscara a la pestanya GRAIN si està present.
        if not self.pestanyes_comprova(): return
        
        file = self.app.current_file
        if not self.grain_comprova(file): return
        if hasattr(file, 'mask'): return
        
        grainCh = file.channel['GRAIN']
        file.mask = (grainCh.Z > 0).astype(int)

        colors = [(1, 0, 0, 1), (1, 1, 1, 0)]  # Roig (0), Transparent (1)
        colormap = ListedColormap(colors)

        for ch in file.channel.values():
            if ch.tipus == 'GRAIN':
                ch.mask = ch.axis.imshow(
                    file.mask, cmap=colormap, interpolation='none',
                    origin='lower', extent=[0, file.midaBase[0], 0, file.midaBase[1]],
                    vmin=0, vmax=1, alpha=.6
                )
                ch.figure.canvas.draw()

    def _registrar_mascara(self): # Guarda la màscara actual en un fitxer dins de la carpeta GRAIN.
        if not self.pestanyes_comprova(): return
        file = self.app.current_file
        
        if not self.grain_comprova(file): return
        if not self.fletxes_comprova(file): return
        
        if not hasattr(file, 'mask'):
            messagebox.showinfo("Informació", "Afegeix una màscara abans de continuar.")
            return

        self.guardar_general(file, amb_histograma=False)

    def _esborrar_mascara(self): # Esborra la màscara actual de totes les pestanyes.
        if not self.pestanyes_comprova(): return
        file = self.app.current_file
        
        if not self.grain_comprova(file): return
        if not hasattr(file, 'mask'): return

        for channelObj in file.channel.values():
            if channelObj.tipus != 'GRAIN':
                channelObj.mask.remove()
                delattr(channelObj, 'mask')
                channelObj.figure.canvas.draw()

        delattr(file, 'mask')