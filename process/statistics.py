import numpy as np
import pandas as pd
import sys
from matplotlib.ticker import AutoLocator, ScalarFormatter
from process.basics import truncar_significatives
sys.path.insert(1, r'C:\Users\Parmenio\OneDrive - Universitat de Valencia\Escritorio\Doctorat\Programetes\Funcions')
sys.path.insert(1, r'C:\Users\ASUS\OneDrive - Universitat de València\Escritorio\Doctorat\Programetes\Funcions')

def guardar_histograma(fig, ax, z, lims, carpeta, name, title=None, nbins=100, weight=False, nom=None):
    if name != 'GRAIN': basePath = carpeta / f'Histogrames - {name}'
    else: basePath = carpeta
        
    if weight: basePath += ' Pesat'; name += ' Pesat'

    basePath.mkdir(parents=True, exist_ok=True)

    # 1. HISTOGRAMA: Bàsic.
    bar, HIST, histLims = hist(ax, z, lims, xlabel=title, nbins = nbins, weight=weight)
    np.savetxt(f"{basePath}/{name} Hist.txt", HIST, fmt='%.5f')
    fig.subplots_adjust(left=0.05, bottom=0.25)
    fig.savefig(f"{basePath}/{name} Hist.png")
    bar.remove()

    # 2. BOXPLOT
    boxFig = boxplot(ax, z, histLims, name = name, ylabel=title, weight=weight)
    databox = get_box_plot_data([name], boxFig)
    databox.to_csv(f"{basePath}/{name} Boxplot data.txt", sep='\t', index=False, float_format='%.3f')
    fig.subplots_adjust(left=0.2, bottom=0.15)
    fig.savefig(f"{basePath}/{name} Boxplot.png")
    remove_boxplot(boxFig)

def hist(ax, data, lims, xlabel = None, nbins = 80, weight = False, color='blue'):
    vmin, vmax = lims
    ample = (vmax - vmin) / nbins
    HIST = fer_histograma(data, nbins, lims=[vmin, vmax], weight=weight)
    bins = HIST[:, 0]; values = HIST[:, 1]
    minBin = np.min(bins); maxBin = np.max(bins)
    
    ax.set_xlabel(xlabel); ax.set_ylabel("")
    ax.set_yticks([])
    bars = ax.fill_between(bins, values, step='mid', alpha=1, color=color)
    ax.axis([minBin - ample / 2, maxBin + ample / 2, 0, np.max(values) * 1.1])
    ax.xaxis.set_major_locator(AutoLocator())
    ax.xaxis.set_major_formatter(ScalarFormatter())
 
    return bars, HIST, (minBin, maxBin)

def boxplot(ax, z, lims, name, ylabel=None, weight=False, color='blue'):
    ax.set_xlabel(''); ax.set_ylabel(ylabel)
    ax.set_xticklabels([])
    ax.set_xlim([0.5, 1.5]); ax.set_ylim(lims)
    
    if weight:
        w = z
        stats = calcula_boxplot_ponderat(z, w, name)
        boxplot = ax.bxp([stats], patch_artist=True, tick_labels=[name], sym='', meanline=True, showmeans=True, whis=[5, 95])
    else:
        boxplot = ax.boxplot(z, patch_artist=True, tick_labels=[name], sym='', meanline=True, showmeans=True, whis=[5, 95])
    
    for box in boxplot['boxes']: box.set_facecolor(color)
    for median in boxplot['medians']: median.set_color('black')
    for mean in boxplot['means']: mean.set_color('black')
    
    ax.yaxis.set_major_locator(AutoLocator())
    
    return boxplot

def remove_boxplot(boxplot):
    for element in boxplot.values():
        for artist in element:
            artist.remove()

def lims_outliers(arr):
    quart1 = np.percentile(arr, 10)
    quart3 = np.percentile(arr, 90)
    iqr = quart3 - quart1
    inf = quart1 - 4 * iqr; sup = quart3 + 4 * iqr
    lim_inf = max(inf, np.min(arr))
    lim_sup = min(sup, np.max(arr))
    lim_inf = truncar_significatives(lim_inf, 2, cap_a = 'avall')
    lim_sup = truncar_significatives(lim_sup, 2, cap_a = 'amunt')
    return lim_inf, lim_sup

def guardar_histograma_grans(zhist, carpzoom, mida_base, N, tipus, name): # Guarda els histogrames dels grans en la carpeta especificada.
    gra_guardar = [r'Area ($\mu m^2$)', r'Eq. disc radius ($\mu m$)']
    nom = ['Area', 'Radi']
    px = mida_base[0] / N[0]
    py = mida_base[1] / N[1]
    grans, area_total, radi_eq = calculs_grans(zhist, [px, py])
    dades = [area_total, radi_eq]
    lims = [[0,0.4],[0,0.4]]
    bins = 40, 40

    # Carpeta principal
    carp_hist = carpzoom / f"Histogrames - {name}"
    carp_hist.mkdir(parents=True, exist_ok=True)

    for i, valor_gra in enumerate(gra_guardar):
        carpguardar = carp_hist / nom[i]
        carpguardar.mkdir(parents=True, exist_ok=True)

        guardar_histograma(dades[i], lims[i], carpguardar, tipus, name,
                xtitle=valor_gra, nbins=bins[i])
        if nom[i] == 'Area':
            guardar_histograma(dades[i], lims[i], carpguardar, tipus, name,
                xtitle=valor_gra, nbins=bins[i],weight = True)
        
def calculs_grans(Z, p): # Calcula les estadístiques dels grans a partir de la matriu Z.
    px = p[0]; py = p[1]
    area_pixel = px*py
    grans, area_gra = np.unique(Z, return_counts=True)
    grans = grans[1:]; area_gra = area_gra[1:]
    grans = grans[area_gra>=5]; area_gra = area_gra[area_gra>=5]
    area_total = area_pixel*area_gra
    radi_eq = np.sqrt(area_total/np.pi)
    return grans, area_total, radi_eq
        
def fer_histograma(z,nbins,lims,weight = False): # Calcula l'histograma de les dades donades.
    min = lims[0]; max = lims[1]
    
    if weight == True:
        weights = z
    else:
        weights = np.ones_like(z)

    values, bin = np.histogram(z,range=[min,max],bins=nbins,weights=weights)
    bin = (bin[:-1] + bin[1:]) / 2  # ← centres dels bins
    values = values / np.sum(values) # Normalitza als valors.

    return np.column_stack((bin, values))

def calcula_boxplot_ponderat(z, w, label): # Calcula les estadístiques del boxplot ponderat.
    z = np.asarray(z)
    w = np.asarray(w)

    # Ordenar
    idx = np.argsort(z)
    z_sorted = z[idx]
    w_sorted = w[idx]
    w_cum = np.cumsum(w_sorted)
    w_total = w_cum[-1]

    def weighted_percentile(sorted_data, cum_weights, percent):
        target = percent * w_total
        return np.interp(target, cum_weights, sorted_data)

    Q1 = weighted_percentile(z_sorted, w_cum, 0.25)
    Q2 = weighted_percentile(z_sorted, w_cum, 0.50)
    Q3 = weighted_percentile(z_sorted, w_cum, 0.75)
    IQR = Q3 - Q1
    mean = np.average(z, weights=w)

    lower_fence = Q1 - 1.5 * IQR
    upper_fence = Q3 + 1.5 * IQR
    non_outlier_mask = (z >= lower_fence) & (z <= upper_fence)
    z_in = z[non_outlier_mask]

    lower_whisker = np.min(z_in) if len(z_in) > 0 else Q1
    upper_whisker = np.max(z_in) if len(z_in) > 0 else Q3
    outliers = z[~non_outlier_mask]

    stats = {
        'label': label,
        'mean': mean,
        'med': Q2,
        'q1': Q1,
        'q3': Q3,
        'whislo': lower_whisker,
        'whishi': upper_whisker,
        'fliers': outliers,
    }

    return stats
    
def get_box_plot_data(labels, bp):
    import numpy as np
    rows_list = []

    for i in range(len(labels)):
        dict1 = {}
        dict1['label'] = labels[i]

        # Whiskers (sempre Line2D)
        dict1['lower_whisker'] = bp['whiskers'][i*2].get_ydata()[1]
        dict1['upper_whisker'] = bp['whiskers'][(i*2)+1].get_ydata()[1]

        # Median (Line2D)
        dict1['median'] = bp['medians'][i].get_ydata()[1]

        # Mean (pot no existir!)
        if 'means' in bp and len(bp['means']) > i:
            dict1['mean'] = bp['means'][i].get_ydata()[1]
        else:
            dict1['mean'] = np.nan

        # 🔥 BOXES: compatible amb Line2D i PathPatch
        box = bp['boxes'][i]

        if hasattr(box, "get_ydata"):
            # Cas antic: Line2D
            y = box.get_ydata()
            dict1['lower_quartile'] = y[1]
            dict1['upper_quartile'] = y[2]

        else:
            # Cas patch_artist=True: PathPatch
            verts = box.get_path().vertices[:, 1]
            dict1['lower_quartile'] = np.min(verts)
            dict1['upper_quartile'] = np.max(verts)

        rows_list.append(dict1)

    return pd.DataFrame(rows_list)