from tkinter import messagebox
import numpy as np
from pybaselines import Baseline

from .base import BaseMenu
from window import BaseWindow, BaseMapWindow
from window.widgets import Widget
from classes.fits import FitSpec

class GestorEspectre(BaseMenu):  # Classe que gestiona les accions relacionades amb els perfils de fletxes.
    ordre = 200
    
    def __init__(self, app):
        super().__init__(app)  # Inicialitza la classe base

    def registrar_menu(self, menu):
        accions = [
            ('Calcular fons', lambda: Fons(self)),
            ('Afegir llindar', lambda: Llindar(self)),
            ('Fer ajust', lambda: FitSpec(self)),
            ('Guardar espectre', self._guardar),
        ]
        
        self.create_menu("Espectre", menu, accions)  # Crida a la funció comuna d'afegir menú

    def _guardar(self): # Guarda els perfils dibuixats en fitxers de perfil.
        spec = self.current_file.view.spectrum

        folder = self.current_file.folder
        channel = self.current_file.current_channel
        posy, posx = channel.spectra.coords

        ruta = folder / 'Spectra'
        ruta.mkdir(parents=True, exist_ok=True)
        nom = ruta / f'{folder.stem}_{posx}_{posy}'

        header = '\t'.join([
            f'{"Xdata (" + channel.spectra.units + ")":>12}',
            f'{"I (cts)":>12}',
            f'{"Bkg (cts)":>12}'
        ])
        np.savetxt(f'{nom}.txt', np.c_[channel.spectra.x, channel.spectra.y, channel.spectra.bkg],
            header=header, delimiter='\t', fmt='%12.4f\t%12.2f\t%12.2f')

        spec.figure.savefig(f'{nom}.png', bbox_inches = 'tight')
        # pos = posy - 1, posx - 1
        # if hasattr(self, 'fits'):
        #     ruta = f'{self.folder}_{self.posx}_{self.posy} - FIT.txt'
        #     fit = self.fits[self.nomfit]
        #     bkg = self.fits[self.nomfit]['bkg']
        #     peakdata = 0
        #     for peak in fit.values(): peakdata += peak.data(pos)
        #     bkgdata = bkg.data(pos)
        #     data = np.c_[bkg.xfit, peakdata, bkgdata, peakdata - bkgdata]
        #     with open(f'{nom} - FIT.txt', 'w', encoding='utf-8', newline='') as f:
        #         f.write(f"#Nom: {[self.nomfit]}\n")
        #         f.write(f"#Unitats: {[bkg.units]}\n")
        #         f.write(f"#Pics: {[key for key in fit.keys() if key != 'bkg']}\n")
        #         f.write(f"#Funcions: {[peak.type for key, peak in fit.items() if key != 'bkg']}\n")
        #         f.write(f"#Centres: {[str(peak.PeakCenter[*pos]) for key, peak in fit.items() if key != 'bkg']}\n")
        #         f.write(f"#FWHM: {[str(peak.FWHM[*pos]) for key, peak in fit.items() if key != 'bkg']}\n")
        #         f.write(f"#Intensitats: {[str(peak.Intensity[*pos]) for key, peak in fit.items() if key != 'bkg']}\n")
        #         f.write(f'# # # #\n')
        #         f.write(f"#Fons: {[bkg.type]}\n")
        #         f.write(f"#Variables: {[str(bkg.varbls[*pos])]}\n\n")
        #         header = [self.specs[self.spec_type].xtitle, "I (uA)", "bkg", "I-bkg"]
        #         np.savetxt(f, data, delimiter='\t', fmt='%.2f', header='\t'.join(header))

class Fons(BaseWindow):
    def __init__(self, gestor):
        super().__init__(gestor, "Calcular fons")

        self.spec = self.file.view.spectrum
        self.bkg = np.full(self.spec.xdata.shape, np.nan)

    @property
    def xdata(self):
        return self.channel.spectra.x

    @property
    def ydata(self):
        return self.channel.spectra.y[self.xrange]

    @property
    def xrange(self):
        return self.channel.spectra.xrange

    @property
    def baseline(self):
        return Baseline(x_data=self.xdata[self.xrange])

    def plot_bkg(self, value):
        self.widgets["percentile"].config(state = 'disabled')
        self.widgets["spline"].config(state='disabled')
        self.bkg = np.full(self.xdata.shape, np.nan)
        bkg_value = np.full_like(self.xrange, np.nan)

        match value:
            case 'nan': pass
            case 'percentile':
                self.widgets["percentile"].config(state='normal')
                bkg_value = np.nanpercentile(self.ydata, self.widgets["percentile"].get())

            case 'spline':

                self.widgets["spline"].config(state='normal')
                bkg_value, _ = self.baseline.mixture_model(self.ydata, lam = 10 ** self.widgets["spline"].get())

        self.bkg[self.xrange] = bkg_value
        self.spec.bkgline.set_ydata(self.bkg)
        self.spec.canvas.draw_idle()

    def percentile(self, value):
        bkg_value = np.nanpercentile(self.ydata, value)

        self.bkg = np.full(self.xdata.shape, np.nan)
        self.bkg[self.xrange] = bkg_value

        self.spec.bkgline.set_ydata(self.bkg)
        self.spec.canvas.draw_idle()

        return

    def spline(self, value):
        bkg_value, _ = self.baseline.mixture_model(self.ydata, lam = 10 ** value)

        self.bkg = np.full(self.xdata.shape, np.nan)
        self.bkg[self.xrange] = bkg_value

        self.spec.bkgline.set_ydata(self.bkg)
        self.spec.canvas.draw_idle()

        return

    def apply_bkg(self, value):
        bkg_class = self.widgets["bkg"].get()
        if bkg_class == 'nan':
            self.channel.spectra.bkgdata = np.full_like(self.channel.spectra.ydata, 0)
            return

        if self.widgets["map_bkg"].get() == 'one':
            N = self.file.geometry.N
            self.channel.spectra.bkgdata = np.tile(self.bkg, (N[1], N[0], 1))
        else:
            spec = self.channel.spectra.ydata
            for i in range(spec.shape[0]):
                for j in range(spec.shape[1]):
                    spectrum = spec[i, j, :][self.xrange]
                    bkg = np.full(self.xdata.shape, np.nan)

                    if bkg_class == 'percentile':
                        bkg_value = np.nanpercentile(spectrum, self.widgets["percentile"].get())
                    elif bkg_class == 'spline':
                        bkg_value, _ = self.baseline.mixture_model(spectrum)

                    bkg[self.xrange] = bkg_value
                    self.channel.spectra.bkgdata[i, j, :] = bkg

    def _create_widgets(self):
        opts = {"Cap": 'nan',
                "Percentil": "percentile",
                "Spline": "spline"}

        opts_bkg = {'Únic': 'one', 'Un per espectre': 'different'}

        self.widgets = {
            "bkg": Widget(key="bkg", var_type=str, init='nan',
                       text="Classe de fons:", widget="radiobutton", widget_kwargs={"options": opts},
                       setter=self.plot_bkg),

            "percentile": Widget(key="percentile", var_type=float, init=0,
                          text="Percentil (%):", widget="scale",
                          widget_kwargs = {'to': 100, 'resolution': 1, 'state': 'disabled'},
                          setter=self.percentile),

            "spline": Widget(key="spline", var_type=float, init=5,
                      text="Spline:", widget="scale",
                      widget_kwargs={"from": 3, "to": 7, "resolution": 1, "state": "disabled"},
                      setter = self.spline),

            "map_bkg": Widget(key="map_bkg", var_type=str, init='one',
                       text="Fons del mapa:", widget="radiobutton", widget_kwargs={"options": opts_bkg}),

            "apply": Widget(key="apply", var_type=str, init='Aplicar',
                       text = "Aplicar", widget = 'button',
                       setter = self.apply_bkg)
            }

class Llindar(BaseMapWindow):
    def __init__(self, gestor):
        super().__init__(gestor, "Calcular fons")

        self.z = self.channel.Z.copy()
        self.mask = np.ones_like(self.z, dtype=bool)

    def threshold(self, value):
        inf, sup = self.widgets['thrInf'].get(), self.widgets['thrSup'].get()

        self.mask = (self.z >= inf) & (self.z <= sup)
        self.update_fig(mask = self.mask)

    def apply_threshold(self, value):
        self.file.objects.mask = self.mask
        self.channel.Z = self.z
        self.file.view.map.refresh_map()

    def _create_widgets(self):

        self.widgets = {
            "thrInf": Widget(key="bkg", var_type=float, init=0,
                       text="Llindar inferior:", widget="entry",
                       setter=self.threshold),

            "thrSup": Widget(key="thrSup", var_type=float, init=int(1.1* np.nanmax(self.channel.Z)),
                          text="Llindar superior:", widget="entry",
                          setter=self.threshold),

            "apply": Widget(key="apply", var_type=str, init='Aplicar',
                       text = "Aplicar", widget = 'button',
                       setter = self.apply_threshold)
            }