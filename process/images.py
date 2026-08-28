import io
import sys
import subprocess

def zoom(event, old_lims, midaBase, base_scale=1.1):
    xdata, ydata = event.xdata, event.ydata
    xlim, ylim = old_lims

    scale_factor = 1 / base_scale if event.button == 'up' else base_scale
    midaX = (xlim[1] - xlim[0]) * scale_factor
    midaY = (ylim[1] - ylim[0]) * scale_factor

    relx = (xlim[1] - xdata) / (xlim[1] - xlim[0])
    rely = (ylim[1] - ydata) / (ylim[1] - ylim[0])

    xlow = xdata - midaX * (1 - relx)
    xhigh = xdata + midaX * relx
    ylow = ydata - midaY * (1 - rely)
    yhigh = ydata + midaY * rely

    if 0 < xlow < xhigh < midaBase[0] and 0 < ylow < yhigh < midaBase[1]:
        xlim = (xlow, xhigh)
        ylim = (ylow, yhigh)

    return xlim, ylim

def rotate(data, N, rotation = 0, flip = False):
    Nx, Ny = N

    single = isinstance(data, tuple) and len(data) == 2
    if single: data = [data]

    transformed = []
    for x, y in data:
        match rotation:
            case 0: pass
            case 1: x, y = y, Ny - 1 - x
            case 2: x, y = Nx - 1 - x, Ny - 1 - y
            case 3: x, y = Nx - 1 - y, x

        if flip: x = Nx - 1 - x

        transformed.append((x, y))

    return transformed[0] if single else transformed

def on_motion(event, old_lims, midaBase, press):
    xlim, ylim = old_lims
    dx = event.xdata - press[0]
    dy = event.ydata - press[1]

    new_xlim = (xlim[0] - dx, xlim[1] - dx)
    new_ylim = (ylim[0] - dy, ylim[1] - dy)

    if new_xlim[0] >= 0 and new_xlim[1] <= midaBase[0]:
        xlim = new_xlim
    if new_ylim[0] >= 0 and new_ylim[1] <= midaBase[1]:
        ylim = new_ylim

    return xlim, ylim

def copy_figure(figure):
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", bbox_inches="tight", transparent=True)

    if sys.platform == "win32": _copy_figure_windows(buffer)
    elif sys.platform.startswith("linux"): _copy_figure_linux(buffer)
    else: raise NotImplementedError(f"Clipboard d'imatges no implementat per a {sys.platform}")

def _copy_figure_windows(buffer):
    from win32 import win32clipboard

    png_data = buffer.getvalue()

    CF_PNG = win32clipboard.RegisterClipboardFormat("PNG")

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(CF_PNG, png_data)
    finally:
        win32clipboard.CloseClipboard()

def _copy_figure_linux(buffer):
    subprocess.run(["wl-copy", "--type", "image/png"], input=buffer.getvalue(), check=True)