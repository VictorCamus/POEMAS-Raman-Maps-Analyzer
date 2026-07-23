from numpy import genfromtxt, unique, nansum
from process.converter import raman_to_nm, raman_to_eV, nm_to_raman, nm_to_eV, eV_to_raman, eV_to_nm
from classes import ChannelData

def load(file_list, fileclass):
    file = file_list[0]
    with open(file) as f:
        is_laser = True
        for linia in f:
            if linia.startswith('#Laser') and is_laser:
                valor = linia.split('=', 1)[-1].strip()
                laser = float(valor[:3])
                is_laser = False
            elif linia.startswith('#AxisUnit[1]='):
                units = linia.split('=', 1)[1].strip()
                break
    
    dades = genfromtxt(file, delimiter = '\t') # q: [0,2:]. x: [1:,0]. y: [1:,1]. I: [1:,2:]
    q = dades[0,2:]
    y = unique(dades[1:,0])
    x = unique(dades[1:,1])

    N = len(x), len(y)
    spectra = dades[1:, 2:]
    spectra = spectra.reshape(N[1], N[0], spectra.shape[1])

    mida = (x[1]-x[0])*N[0], (y[1]-y[0])*N[1]

    xdata = {}; channels = {}
    match units:
        case 'nm': 
            xdata['nm'] = q
            xdata['eV'] = nm_to_eV(q)
            xdata['1/cm'] = nm_to_raman(q, laser)

        case 'eV':
            xdata['nm'] = eV_to_nm(q)
            xdata['eV'] = q
            xdata['1/cm'] = eV_to_raman(q, laser)

        case '1/cm':
            xdata['nm'] = raman_to_nm(q, laser)
            xdata['eV'] = raman_to_eV(q, laser)
            xdata['1/cm'] = q

    channels['Spectra'] = ChannelData(name='Spectra', units = units, xdata=xdata, spectra=spectra)
    data = {'channel': channels, 'N': N, '_midaBase': mida, 'laser': laser}

    return fileclass(**data)