import numpy as np
import math as math

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

def nm_to_raman(lambda_nm, laser_nm):
    lambda_nm = np.asarray(lambda_nm)
    return 1e7 * (1/laser_nm - 1/lambda_nm)

def nm_to_eV(lambda_nm):
    return 1239.84197/np.asarray(lambda_nm) 

def raman_to_nm(shift_cm1, laser_nm):
    shift_cm1 = np.asarray(shift_cm1)
    return 1 / (1/laser_nm - shift_cm1/1e7)

def raman_to_eV(shift_cm1, laser_nm):
    return 1239.84197/laser_nm+1.23984198*1e-4*np.asarray(shift_cm1)