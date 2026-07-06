import numpy as np
from dataclasses import dataclass
from process.basics import truncar_significatives

@dataclass
class MapInfo: # Informació sobre els possibles fitxers de mapes oberts.
    title: str
    mult: float
    units: str
    interp: str
    
def all_maps(): # Informació sobre els possibles fitxers de mapes oberts. MapInfo està en classes.
    mapes = {
        "AFM": MapInfo("Height (nm)", 1E9, "nm", "gaussian"),
        "MAG": MapInfo("Mag (uA)", 1, "uA", "gaussian"),
        "PHASE": MapInfo("Phase (º)", 1, "º", "gaussian"),
        "CPD": MapInfo("CPD (mV)", 1E3, "mV", "gaussian"),
        "CPD - Mean": MapInfo("CPD - Mean (mV)", 1E3, "mV", "gaussian"),
        "COND": MapInfo("I (pA)", 1E12, "pA", "gaussian"),
        "SPV": MapInfo("SPV (mV)", 1E3, "mV", "gaussian"),
        "GRAIN": MapInfo("", 1, "", "none"),
    }

    return mapes

def map_info(tipus): # Retorna la informació d'un tipus de mapa específic.
    return all_maps()[tipus]

def map_types(): # Retorna una llista amb tots els tipus de mapes possibles.
    return list(all_maps().keys())

@dataclass
class Colors:
    cmap_c: str # Color.
    cmap_r: bool # Normal o revertit.
    scale: str
    limInf: str
    limSup: str

    @property
    def cmap(self):
        return f'{self.cmap_c}_r' if self.cmap_r else self.cmap_c
    
    @property
    def lims(self):
        return (self.limInf, self.limSup)
    
def all_colors(): # Informació sobre els possibles fitxers de mapes oberts. MapInfo està en classes.
    colors = {
        "AFM": Colors("AFM", False, 'w', *("w", "k")),
        "MAG": Colors("MAG", False, 'w', *("w", "k")),
        "PHASE": Colors("PHASE", False, 'w', *("w", "k")),
        "CPD": Colors("CPD", False, 'w', *("w", "k")),
        "CPD - Mean": Colors("CPD", False, 'w', *("w", "k")),
        "COND": Colors("COND", False, 'w', *("w", "k")),
        "SPV": Colors("SPV", False, 'w', *("w", "k")),
        "GRAIN": Colors("GRAIN", False, 'w', *("w", "k")),
    }

    return colors

def color_info(tipus): # Retorna la informació d'un tipus de mapa específic.
    return all_colors()[tipus]

def lims(z, tipus):
    # 1. Cas especial GRAIN: Sortida immediata per evitar càlculs innecessaris
    if tipus == 'GRAIN':
        return z, np.array([0, 1])

    # 2. Optimització de numpy: Càlcul de percentils en una sola passada
    # Això és el doble de ràpid que cridar-lo dues vegades
    vmin, vmax = np.percentile(z, [0.2, 99.8])

    # 3. Estructura match-case per a la lògica segons el tipus
    match tipus:
        case 'AFM':
            z -= vmin; vmax -= vmin
            vmin = 0.0
        case 'COND':
            limit = max(abs(vmin), abs(vmax))
            vmin, vmax = -limit, limit
        case _: pass
        
    # 4. Truncament de valors
    vmin = truncar_significatives(vmin, 2, cap_a='avall')
    vmax = truncar_significatives(vmax, 2, cap_a='amunt')

    # 5. Seguretat per evitar límits idèntics
    if vmin == vmax:
        vmin -= 5
        vmax += 5

    return np.array([vmin, vmax]), z

def gausfit():  # Informació sobre els paràmetres a ajustar d'una gaussiana.
    
    var = {
        'amp': {'value': 0, 'min': 0, 'vary': False},
        'mu': {'value': 0, 'vary': False},
        'sigma': {'value': 0, 'min': 0, 'vary': False},
    }
    
    return(var)