import numpy as np
from matplotlib.ticker import AutoLocator, ScalarFormatter

from process.basics import truncar_significatives

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