import numpy as np

def truncar_significatives(x, n, cap_a='amunt'):
    from decimal import Decimal, getcontext, ROUND_FLOOR, ROUND_CEILING

    if x == 0:
        return 0.0

    getcontext().prec = 50

    x_dec = Decimal(str(x))

    exponent = int(
        x_dec.copy_abs().log10().to_integral(rounding=ROUND_FLOOR)
    )

    factor = Decimal(10) ** (exponent - n + 1)

    if cap_a == 'avall':
        truncat = (
            x_dec / factor
        ).to_integral(rounding=ROUND_FLOOR) * factor

    elif cap_a == 'amunt':
        truncat = (
            x_dec / factor
        ).to_integral(rounding=ROUND_CEILING) * factor

    else:
        raise ValueError(
            "El valor de 'cap_a' ha de ser 'amunt' o 'avall'"
        )

    return float(truncat)

def find_nearest(array, values):
    array = np.asarray(array)
    values = np.atleast_1d(values)
    idx = [(np.abs(array - value)).argmin() for value in values]

    return (idx) if len(idx) > 1 else idx[0]

def set_lims(name, z):
    if name == 'Grain': return np.array([0, 1]), z

    vmin, vmax = np.nanpercentile(z, [0.2, 99.8])

    if name == 'Height':
        z -= vmin
        vmax -= vmin
        vmin = 0

    # 4. Truncament de valors
    vmin = truncar_significatives(vmin, 3, cap_a='avall')
    vmax = truncar_significatives(vmax, 3, cap_a='amunt')

    # 5. Correcció per evitar límits idèntics
    if vmin == vmax:
        vmin -= 5
        vmax += 5

    return np.array([vmin, vmax]), z

def get_line(p1, p2):
    x1, y1 = p1
    x2, y2 = p2

    points = []
    issteep = abs(y2 - y1) > abs(x2 - x1)
    if issteep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2
    rev = False
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
        rev = True
    deltax = x2 - x1
    deltay = abs(y2 - y1)
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
    # Reverse the list if the coordinates were reversed
    if rev:
        points.reverse()

    return points
