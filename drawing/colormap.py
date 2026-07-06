import matplotlib.pyplot as plt
import matplotlib

from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from typing import Sequence
from matplotlib import colormaps as cm
from numpy import linspace
N=255

hot = cm['hot']
newColors= hot(linspace(0, 1, 420))[:256]
newcmp = ListedColormap(newColors)
matplotlib.colormaps.register(cmap=newcmp, name = 'calent', force=True)

cmaps_custom = [
    # Personalitzats
    "AFM",
    "MAG",
    "PHASE",
    "CPD",
    "COND",
    "SPV",
    "GRAIN"]

cmaps_matplotlib = [
    # Moderns / perceptuals
    "calent",
    "viridis",
    "plasma",
    "inferno",
    "magma",
    "cividis",
    "turbo",

    # Sequential
    "Greys",
    "Purples",
    "Blues",
    "Greens",
    "Oranges",
    "Reds",

    # Sequential multi-color
    "YlGn",
    "YlGnBu",
    "GnBu",
    "BuGn",
    "PuBu",
    "PuRd",

    # Diverging
    "coolwarm",
    "bwr",
    "seismic",
    "RdBu",
    "RdYlBu",
    "Spectral",

    # Cyclic / especials
    "twilight",
    "hsv",

    # Clàssics
    "jet",
    "cool",
    "spring",
    "summer",
    "autumn",
    "winter",
    "gray",
]

cmaps = cmaps_custom + cmaps_matplotlib
colors: dict[str, dict[str, Sequence[tuple[float, ...]]]] = {
    # CPD - Blue/Yellow
    # 'CPD' : {'red':     
    # [(0/N, 1-255/N, 1-255/N),
    # (26/N, 1-255/N, 1-255/N),
    # (51/N, 1-255/N, 1-255/N),
    # (77/N, 1-229/N, 1-229/N),
    # (102/N, 1-179/N, 1-179/N),
    # (128/N, 1-127/N, 1-127/N),
    # (153/N, 1-77/N, 1-77/N),
    # (179/N, 1-25/N, 1-25/N),
    # (204/N, 1-0/N, 1-0/N),
    # (230/N, 1-0/N, 1-0/N),
    # (255/N, 1-0/N, 1-0/N)],
    
    # 'green':     
    # [(0/N, 1-255/N, 1-255/N),
    # (26/N, 1-255/N, 1-255/N),
    # (51/N, 1-255/N, 1-255/N),
    # (77/N, 1-229/N, 1-229/N),
    # (102/N, 1-179/N, 1-179/N),
    # (128/N, 1-127/N, 1-127/N),
    # (153/N, 1-77/N, 1-77/N),
    # (179/N, 1-25/N, 1-25/N),
    # (204/N, 1-0/N, 1-0/N),
    # (230/N, 1-0/N, 1-0/N),
    # (255/N, 1-0/N, 1-0/N)],
    
    # 'blue':     
    # [(0/N, 1-255/N, 1-255/N),
    # (26/N, 1-151/N, 1-151/N),
    # (51/N, 1-51/N, 1-51/N),
    # (77/N, 1-27/N, 1-27/N),
    # (102/N, 1-77/N, 1-77/N),
    # (128/N, 1-129/N, 1-129/N),
    # (153/N, 1-179/N, 1-179/N),
    # (179/N, 1-231/N, 1-231/N),
    # (204/N, 1-203/N, 1-203/N),
    # (230/N, 1-99/N, 1-99/N),
    # (255/N, 1-0/N, 1-0/N)],
    # },

    # CPD: Cold
    'CPD': {'red':     
    [(0/N, 1-255/N, 1-255/N),
    (77/N, 1-212/N, 1-212/N),
    (128/N, 1-205/N, 1-205/N),
    (179/N, 1-169/N, 1-169/N),
    (230/N, 1-23/N, 1-23/N),
    (255/N, 1-0/N, 1-0/N)],
    
    'green':     
    [(0/N, 1-255/N, 1-255/N),
    (77/N, 1-185/N, 1-185/N),
    (128/N, 1-152/N, 1-152/N),
    (179/N, 1-83/N, 1-83/N),
    (230/N, 1-23/N, 1-23/N),
    (255/N, 1-0/N, 1-0/N)],
    
    'blue':     
    [(0/N, 1-255/N, 1-255/N),
    (77/N, 1-130/N, 1-130/N),
    (123/N, 1-100/N, 1-100/N),
    (179/N, 1-59/N, 1-59/N),
    (230/N, 1-23/N, 1-23/N),
    (255/N, 1-0/N, 1-0/N)],
    },

    'AFM' :  {'red':     
        [(0/N, 1-255/N, 1-255/N),
        (32/N, 1-136/N, 1-136/N),
        (94/N, 1-57/N, 1-57/N),
        (152/N, 1-17/N, 1-17/N),
        (188/N, 1-6/N, 1-6/N),
        (255/N, 1-6/N, 1-6/N),],
        
        'green':     
        [(0/N, 1-255/N, 1-255/N),
        (17/N, 1-255/N, 1-255/N),
        (47/N, 1-234/N, 1-234/N),
        (106/N, 1-159/N, 1-159/N),
        (182/N, 1-47/N, 1-47/N),
        (232/N, 1-7/N, 1-7/N),
        (255/N, 1-6/N, 1-6/N)],
        
        'blue':     
        [(0/N, 1-255/N, 1-255/N),
        (85/N, 1-255/N, 1-255/N),
        (160/N, 1-179/N, 1-179/N),
        (220/N, 1-42/N, 1-42/N),
        (255/N, 1-4/N, 1-4/N)],
        },
    'MAG' :  {'red':
        [(0/N , 1-255/N, 1-255/N),
        (26/N , 1-219/N, 1-219/N),
        (51/N , 1-184/N, 1-184/N),
        (77/N , 1-148/N, 1-148/N),
        (102/N , 1-113/N, 1-113/N),
        (128/N , 1-76/N, 1-76/N),
        (153/N , 1-41/N, 1-41/N),
        (179/N , 1-5/N, 1-5/N),
        (204/N , 1-0/N, 1-0/N),
        (230/N , 1-0/N, 1-0/N),
        (255/N , 1-0/N, 1-0/N)],

        'green':
        [(0/N , 1-255/N, 1-255/N),
        (26/N , 1-255/N, 1-255/N),
        (51/N , 1-255/N, 1-255/N),
        (77/N , 1-255/N, 1-255/N),
        (102/N , 1-255/N, 1-255/N),
        (128/N , 1-255/N, 1-255/N),
        (153/N , 1-185/N, 1-185/N),
        (179/N , 1-113/N, 1-113/N),
        (204/N , 1-43/N, 1-43/N),
        (230/N , 1-0/N, 1-0/N),
        (255/N , 1-0/N, 1-0/N)],

        'blue': 
        [(0/N , 1-255/N, 1-255/N),
        (26/N , 1-255/N, 1-255/N),
        (51/N , 1-255/N, 1-255/N),
        (77/N , 1-255/N, 1-255/N),
        (102/N , 1-255/N, 1-255/N),
        (128/N , 1-255/N, 1-255/N),
        (153/N , 1-255/N, 1-255/N),
        (179/N , 1-255/N, 1-255/N),
        (204/N , 1-208/N, 1-208/N),
        (230/N , 1-104/N, 1-104/N),
        (255/N , 1-4/N, 1-4/N)],
    },
    # 'SPV' :  {'red':
    #     [(0/N , 1-255/N, 1-255/N),
    #     (100/N , 1-255/N, 1-255/N),
    #     (116/N , 1-255/N, 1-255/N),
    #     (127/N , 1-50/N, 1-50/N),
    #     (127.5/N , 1-0/N, 1-0/N),
    #     (147/N , 1-3/N, 1-3/N),
    #     (253/N , 1-0/N, 1-0/N),
    #     (255/N , 1-0/N, 1-0/N)],

    #     'green':
    #     [(0/N , 1-218/N, 1-218/N),
    #     (26/N , 1-196/N, 1-196/N),
    #     (60/N , 1-130/N, 1-130/N),
    #     (127.5/N , 1-0/N, 1-0/N),
    #     (215/N , 1-253/N, 1-253/N),
    #     (255/N , 1-254/N, 1-254/N)],

    #     'blue': 
    #     [(0/N , 1-136/N, 1-136/N),
    #     (46/N , 1-47/N, 1-47/N),
    #     (127.5/N , 1-0/N, 1-0/N),
    #     (128/N , 1-50/N, 1-50/N),
    #     (153/N , 1-251/N, 1-251/N),
    #     (255/N , 1-6/N, 1-6/N)]},
    'SPV' :  {'red':
        [(0/N , 1-255/N, 1-255/N),
        (127.5/N , 1-200/N, 1-200/N),
        (180/N , 1-0/N, 1-0/N),
        (255/N , 1-0/N, 1-0/N)],

        'green':
        [(0/N , 1-0/N, 1-0/N),
        (67/N , 1-130/N, 1-130/N),
        (101/N , 1-196/N, 1-196/N),
        (127.5/N , 1-200/N, 1-200/N),
        (255/N , 1-0/N, 1-0/N)],

        'blue': 
        [(0/N , 1-0/N, 1-0/N),
        (81/N , 1-47/N, 1-47/N),
        (127.5/N , 1-200/N, 1-200/N),
        (153/N , 1-255/N, 1-255/N),
        (255/N , 1-255/N, 1-255/N)]}, 
    
    # 'COND' : {'red': # Mapa addicional per a COND. Una escala de colors taronja i blau amb centre negre.     
    #     [(0/N, 1-255/N, 1-255/N),
    #     (32/N, 1-136/N, 1-136/N),
    #     (94/N, 1-57/N, 1-57/N),
    #     (152/N, 1-17/N, 1-17/N),
    #     (188/N, 1-6/N, 1-6/N),
    #     (255/N, 1-6/N, 1-6/N),],
        
    #     'green':     
    #     [(0/N, 1-255/N, 1-255/N),
    #     (17/N, 1-255/N, 1-255/N),
    #     (47/N, 1-234/N, 1-234/N),
    #     (106/N, 1-159/N, 1-159/N),
    #     (182/N, 1-47/N, 1-47/N),
    #     (232/N, 1-7/N, 1-7/N),
    #     (255/N, 1-6/N, 1-6/N)],
        
    #     'blue':     
    #     [(0/N, 1-255/N, 1-255/N),
    #     (85/N, 1-255/N, 1-255/N),
    #     (160/N, 1-179/N, 1-179/N),
    #     (220/N, 1-42/N, 1-42/N),
    #     (255/N, 1-4/N, 1-4/N)],
    #     }
}

def load_colormaps(): # Crea els colormaps personalitzats a partir dels canals de colors definits a dalt i els registra a Matplotlib.
    for name, channels in colors.items():
        cmap = LinearSegmentedColormap(name, channels, N)
        matplotlib.colormaps.register(cmap=cmap, force=True)
        matplotlib.colormaps.register(cmap=cmap.reversed(), force=True)
        
    # Assign standard colormaps to aliases  
    matplotlib.colormaps.register(cmap=plt.get_cmap('plasma'), name='PHASE', force=True)
    matplotlib.colormaps.register(cmap=plt.get_cmap('plasma_r'), name='PHASE_r', force=True)
    matplotlib.colormaps.register(cmap=plt.get_cmap('viridis'), name='COND', force=True)
    matplotlib.colormaps.register(cmap=plt.get_cmap('viridis_r'), name='COND_r', force=True)

    # Custom ListedColormap
    grain_cmap = ListedColormap(['black', 'tab:orange'], name='GRAIN')
    matplotlib.colormaps.register(cmap=grain_cmap, force=True)
    
    grain_cmap_r = ListedColormap(['tab:orange', 'black'], name='GRAIN_r')
    matplotlib.colormaps.register(cmap=grain_cmap_r, force=True)