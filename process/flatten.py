import numpy as np

def level_plane(Z, N):
    Nx, Ny = N
    _, bx, by = fit_plane(Z, N)
    c2 = -0.5 * (bx*Nx + by*Ny)
    return extract_plane(Z, N, c2, bx, by)

def level_facet(Z, N, max_iter=50, eps=1e-6):
    for i in range(max_iter):
        nx, ny, nz = compute_normals(Z)
        n_dom = dominant_normal(nx, ny, nz)

        plane, _, _ = normal_to_plane(n_dom, N)
        new_data = Z - plane

        # 5. criteri convergència
        if np.linalg.norm(n_dom - np.array([0,0,1])) < 1e-4:
            break

        Z = new_data

    return Z

def fit_plane(data, N):
    y, x = np.indices(N[::-1])

    z = data.flatten()
    x = x.flatten()
    y = y.flatten()

    # Matriu de disseny
    A = np.c_[np.ones_like(x), x, y]

    # Ajust per mínims quadrats
    coeffs, *_ = np.linalg.lstsq(A, z, rcond=None)
    c, bx, by = coeffs

    return c, bx, by

def extract_plane(data, N, c, bx, by):
    Nx, Ny = N
    y, x = np.indices((Ny, Nx))
    plane = c + bx*x + by*y
    return data - plane

def compute_normals(Z):
    dzdy, dzdx = np.gradient(Z)
    nx = -dzdx; ny = -dzdy; nz = np.ones_like(Z)

    norm = np.sqrt(nx**2 + ny**2 + nz**2)
    nx /= norm; ny /= norm; nz /= norm

    return nx, ny, nz

def dominant_normal(nx, ny, nz, sigma=0.3):
    n = np.stack([nx.ravel(), ny.ravel(), nz.ravel()], axis=1)

    mean = np.mean(n, axis=0)
    mean /= np.linalg.norm(mean)

    dots = n @ mean
    weights = np.exp((dots - 1) / (sigma**2))

    w = weights[:, None]
    n_weighted = np.sum(w * n, axis=0)
    n_weighted /= np.linalg.norm(n_weighted)

    return n_weighted

def normal_to_plane(nvec, N):
    nx, ny = N
    y, x = np.mgrid[:ny, :nx]

    nx0, ny0, nz0 = nvec

    c = 0.0; bx = -nx0 / nz0; by = -ny0 / nz0

    plane = c + bx * x + by * y
    return plane, bx, by

def linematch_median(Z, N):
    Ny = N[1]
    medians = np.median(Z, axis=1)
    return apply_row_shifts(Z, Ny, medians)

def linematch_median_diff(Z, N):
    Ny = N[1]
    shifts = np.zeros(Ny)

    for i in range(Ny - 1):
        diff = Z[i+1] - Z[i]
        median = np.median(diff)
        shifts[i+1] = shifts[i] + median

    # eliminar pendent global (slope_level_row_shifts)
    x = np.arange(Ny)
    p = np.polyfit(x, shifts, 1)
    shifts = shifts - (p[0]*x + p[1])

    return apply_row_shifts(Z, Ny, shifts)

def linematch_modus(Z, N):
    Ny = N[1]
    shifts = np.zeros(Ny)

    for i in range(Ny):
        row = np.sort(Z[i])

        n = len(row)
        if n < 9:
            shifts[i] = np.median(row)
        else:
            seglen = int(np.sqrt(n))
            best_width = np.inf
            best_j = 0

            for j in range(n - seglen):
                width = row[j+seglen] - row[j]
                if width < best_width:
                    best_width = width
                    best_j = j

            segment = row[best_j + seglen//3 : best_j + 2*seglen//3]
            shifts[i] = np.mean(segment)

    return apply_row_shifts(Z, Ny, shifts)

def linematch_match(Z, N):
    Nx, Ny = N
    shifts = np.zeros(Ny)
    for i in range(1, Ny):
        a = Z[i-1]
        b = Z[i]

        # gradient difference
        diff = (a[1:] - a[:-1]) - (b[1:] - b[:-1])
        q = np.mean(np.abs(diff))

        if q == 0:
            shifts[i] = shifts[i-1]
            continue

        # weights
        w = np.exp(-(diff**2)/(2*q))

        # correction
        lam = (a[0] - b[0]) * w[0]
        for j in range(1, Nx-1):
            lam += (a[j] - b[j]) * (w[j-1] + w[j])
        lam += (a[-1] - b[-1]) * w[-1]

        lam /= (2 * np.sum(w))

        shifts[i] = shifts[i-1] - lam

    return apply_row_shifts(Z, Ny, shifts)

def apply_row_shifts(Z, Ny, shifts):
    shifts = shifts - np.mean(shifts)  # zero_level_row_shifts
    for i in range(Ny): Z[i, :] -= shifts[i]
    return Z