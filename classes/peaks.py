import numpy as np
from process.mathfuncs import Functions

class Pic:
    def __init__(self, name, units, func, PeakCenter, FWHM, Intensity, NormInt, xfit=None, color='green'):
        self.name = name
        self.units = units
        self.type = func
        self.func = Functions[func]
        self.PeakCenter = PeakCenter
        self.FWHM = FWHM
        self.Intensity = Intensity
        self.NormInt = NormInt
        self.xfit = xfit
        self.color = color

        self.Area = self.Intensity * self.FWHM / (2 * np.sqrt(np.log(10))) * np.sqrt(np.pi)

        self.labels = {"PeakCenter": r"Peak center (cm$^{-1}$)",
                       "FWHM": r"FWHM (cm$^{-1}$)",
                       "Area": r"Intensity (a.u.)",
                       "Intensity": r"Intensity (a.u.)",
                       "NormInt": r"Normalized Intensity (a.u.)"}

    def data(self, pos, xdata=None):
        if not xdata: xdata = self.xfit
        params = [self.PeakCenter[*pos], self.FWHM[*pos], self.Intensity[*pos]]
        return self.func(xdata, *params)

class Fons:
    def __init__(self, name, units, func, varbls, xfit=None, color='tab:blue'):
        self.name = name
        self.units = units
        self.type = func
        self.func = Functions[func]
        self.varbls = varbls
        self.xfit = xfit
        self.color = color

    def data(self, pos, xdata=None):
        if not xdata: xdata = self.xfit
        return self.func(xdata, *np.atleast_1d(self.varbls[*pos]))