from matplotlib.figure import Figure
from numpy import interp, argsort
from process.basics import find_nearest
import matplotlib.ticker as ticker

def base_plot(xtitle=None, ytitle=None, dim=(6,4)):
    fig = Figure(figsize=dim, tight_layout=True)
    ax = fig.add_subplot(111)

    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(2))
    ax.tick_params(axis='x', which='minor', direction='in')
    ax.tick_params(axis='x', labelsize=15, direction='in')

    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))
    ax.tick_params(axis='y', which='minor', direction='in')
    ax.tick_params(axis='y', labelsize=15, direction='in')

    ax.locator_params(axis='both', nbins=5)

    ax.set_xlabel(xtitle, fontsize=20, labelpad=10, fontname='Arial')
    ax.set_ylabel(ytitle, fontsize=20, labelpad=10, fontname='Arial')

    ax.set_axisbelow(True)

    fig.tight_layout()

    return fig, ax

def plot_peak(xdata, ax, peak, bkg, pos):
    color = peak.color
    name = peak.name
    ydata = peak.data(pos)
    idx = find_nearest(peak.xfit, peak.PeakCenter[*pos])
    ax.fill_between(xdata, ydata + bkg, bkg, color=color, alpha=0.6)

    index_sort = argsort(peak.xfit)
    peakcenter = interp(peak.PeakCenter[*pos], peak.xfit[index_sort], xdata[index_sort])

    etiquette = ax.annotate(f'{name} ({peakcenter:.2f})', xy=(peakcenter, peak.Intensity[*pos] + bkg[idx]),
                            xytext=(0, 10), textcoords='offset points', ha='center', color='k', fontweight='bold',
                            family='Arial')

    return etiquette

def IVplt(X, Y, units, color, size, labels):
    unX, unY = units
    sizeX, sizeY = size
    fig, ax = base_plot(xtitle = unX, ytitle = unY, dim = (sizeX,sizeY))

    for axis in (['top','bottom','left','right']): ax.spines[axis].set_linewidth(1.5)

    ax.plot(X,Y,'{}'.format(color),linewidth=2,label = labels)   #Ploteja l'anada del primer cicle. (X,Y,FORMAT DE LÍNIA, MIDA DE LA LÍNIA)

    return (fig,ax)