import numpy as np

def ccd_correct(xdata, spectra):
    with open('CCD/CCD.csv', encoding='utf-8') as f:
        CCD_Data = np.loadtxt((line.replace(',', '.') for line in f), delimiter=' ', usecols=(0, 1))

    # spectra -= percentile(spectra, 1)
    QE = np.interp(xdata, CCD_Data[0], CCD_Data[1], left=np.nan, right=np.nan)
    QE[QE < 0.05] = np.nan
    spectra /= QE
    spectra[spectra < 0] = 0

    return spectra