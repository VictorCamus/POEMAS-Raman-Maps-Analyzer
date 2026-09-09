import numpy as np
from process.converter import raman_to_nm, raman_to_eV, nm_to_raman, nm_to_eV, eV_to_raman, eV_to_nm
from classes import ChannelData, Geometry, ObjectData, SpecData

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
                xunits = linia.split('=', 1)[1].strip()
                break
    
    dades = np.genfromtxt(file, delimiter = '\t') # q: [0,2:]. x: [1:,0]. y: [1:,1]. I: [1:,2:]
    q = dades[0,2:]
    y = np.unique(dades[1:,0])
    x = np.unique(dades[1:,1])

    npixels = len(x), len(y)
    spectra = dades[1:, 2:]

    if np.nanmax(spectra) <= np.iinfo(np.uint16).max: spectra = spectra.astype(np.uint16)
    else: spectra = spectra.astype(np.uint32)

    spectra = spectra.reshape(npixels[1], npixels[0], spectra.shape[1])

    mida = (x[1]-x[0])*npixels[0], (y[1]-y[0])*npixels[1]

    xdata = {}; channels = {}
    match xunits:
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

    spectra = SpecData(xdata = xdata, raw_ydata = spectra, units = xunits)
    channels['Spectra'] = ChannelData(name='Spectra', units = 'cts', spectra=spectra)
    data = {'channel': channels, 'geometry': Geometry(npixels, mida), 'objects': ObjectData(laser = laser)}

    return fileclass(**data)