from numpy import asarray
from math import floor

HC = 1239.84197          # Planck constant × c (eV·nm)
HC_CM = 1e7 / HC         # 8065.54429 cm⁻¹/eV

def nm_to_raman(lambda_nm, laser_nm): # Convert wavelength (nm) to Raman shift (cm⁻¹).
    lambda_nm = asarray(lambda_nm)
    return 1e7 * (1 / laser_nm - 1 / lambda_nm)

def nm_to_eV(lambda_nm): # Convert wavelength (nm) to energy (eV).
    return HC / asarray(lambda_nm)

def raman_to_nm(shift_cm1, laser_nm): # Convert Raman shift (cm⁻¹) to wavelength (nm).
    shift_cm1 = asarray(shift_cm1)
    return 1 / (1 / laser_nm - shift_cm1 / 1e7)

def raman_to_eV(shift_cm1, laser_nm): # Convert Raman shift (cm⁻¹) to energy (eV).
    shift_cm1 = asarray(shift_cm1)
    return HC / laser_nm - shift_cm1 / HC_CM

def eV_to_nm(energy_eV): # Convert energy (eV) to wavelength (nm).
    return HC / asarray(energy_eV)

def eV_to_raman(energy_eV, laser_nm): # Convert energy (eV) to Raman shift (cm⁻¹).
    energy_eV = asarray(energy_eV)
    return HC_CM * (HC / laser_nm - energy_eV)

def coords_to_pixel(points, N, mida):
    Nx, Ny = N
    midaX, midaY = mida

    return [(floor(x * Nx / midaX), floor(y * Ny / midaY)) for x,y in points]

def pixel_to_coords(points, N, mida):
    Nx, Ny = N
    midaX, midaY = mida

    return [((x + 0.5) * midaX/ Nx, (y + 0.5) * midaY / Ny) for x,y in points]

def pixel_center(points, N, mida):
    pixels = coords_to_pixel(points, N, mida)

    if any(col < 0 or col >= N[0] or row < 0 or row >= N[1] for col, row in pixels):
        return None

    return pixel_to_coords(pixels, N, mida)