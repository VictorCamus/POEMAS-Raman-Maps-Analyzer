from numpy import interp, nan
from pandas import read_table

def ccd_correct(xdata, spectra):
    CCD_Data = read_table('CCD/CCD.csv', delimiter=' ', decimal=',', usecols=[0, 1], header=None)
    QE = interp(xdata, CCD_Data[0], CCD_Data[1], left=nan, right=nan)
    QE[QE < 0.05] = nan
    print(spectra.shape)
    print(QE.shape)
    spectra /= QE

    return spectra