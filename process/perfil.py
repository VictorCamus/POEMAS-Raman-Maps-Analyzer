import numpy as np
import math as math

# Algorisme que elegeix els píxels que més s'aproximen a una recta.
def get_line(p1, p2): 
    x1 = p1[0]; y1 = p1[1]
    x2 = p2[0]; y2 = p2[1]

    points = []
    issteep = abs(y2-y1) > abs(x2-x1)
    if issteep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2
    rev = False
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
        rev = True
    deltax = x2 - x1
    deltay = abs(y2-y1)
    error = int(deltax / 2)
    y = y1
    ystep = None
    if y1 < y2:
        ystep = 1
    else:
        ystep = -1
    for x in range(x1, x2 + 1):
        if issteep:
            points.append((y, x))
        else:
            points.append((x, y))
        error -= deltay
        if error < 0:
            y += ystep
            error += deltax
    # Reverse the list if thecoordinates were reversed
    if rev:
        points.reverse()
    return points

def plot_profile(ax, Z, line, length, color):
    coords = np.asarray(line)
    x_vals = coords[:, 0]
    y_vals = coords[:, 1]

    dades = Z[y_vals, x_vals]
    zmin = dades.min(); zmax = dades.max(); diff = (zmax-zmin)/15
    punts = np.linspace(0, length, len(dades))
    
    profile, = ax.plot(punts, dades, color=color)
    ax.set_xlim(0, length)
    ylims = (round(zmin-diff, 0), round(zmax+diff, 0))
    ax.set_ylim(*ylims)

    return punts, dades, profile

# Guarda els valors z corresponents a les coordenades donades per get_line.
def guardar(fig, tipus, xdata, ydata, folder, num: int = 0):
    fig.savefig(folder / f'{tipus} - Profile {num}.jpg', dpi = 80)

    PROF = np.column_stack((xdata, ydata))
    np.savetxt(folder / f'{tipus} - P{num}.txt', PROF, fmt='%.3f')
