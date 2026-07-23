import numpy as np

def truncar_significatives(x, n, cap_a='amunt'):
    from decimal import Decimal, getcontext, ROUND_FLOOR, ROUND_CEILING
    
    if x == 0:
        return int(0)

    getcontext().prec = 50

    signe = 1 if x > 0 else -1
    x_dec = Decimal(str(abs(x)))

    exponent = int(x_dec.log10().to_integral(rounding=ROUND_FLOOR))
    factor = Decimal(10) ** (exponent - n + 1)

    if cap_a == 'avall':
        truncat = (x_dec / factor).to_integral(rounding=ROUND_FLOOR) * factor
    elif cap_a == 'amunt':
        truncat = (x_dec / factor).to_integral(rounding=ROUND_CEILING) * factor
    else:
        raise ValueError("El valor de 'cap_a' ha de ser 'amunt' o 'avall'")

    valor = float(signe * truncat)

    return int(valor) if valor.is_integer() else valor

def find_nearest(array, values):
    array = np.asarray(array)
    values = np.atleast_1d(values)
    idx = [(np.abs(array - value)).argmin() for value in values]

    return idx if len(idx) > 1 else idx[0]

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
