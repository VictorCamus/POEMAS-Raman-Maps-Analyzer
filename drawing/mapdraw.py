from matplotlib.figure import Figure
import numpy as np
from process.basics import truncar_significatives
# DIBUIX_MAPES: Llig les dades relacionades amb un fitxer AIST i les dibuixa sobre una figura.

def create_map(*args, **kwargs):
    figure = Figure()
    figure.patch.set_alpha(0)
    axis = figure.add_subplot(111)
    image = axis.imshow([[0]], origin="lower")
    
    cbar = create_cbar(figure, image)
    update_map(image, *args, **kwargs, cbar = cbar)
    ajust_eixos(axis)
    
    return figure, axis, image, cbar

def update_map(image, cmap, Z, lims, units, mida = None, colLims = ('w', 'k'), cbar = None):
    vmin, vmax = lims
    
    if cmap == 'GRAIN': Z = (Z > 0).astype(int)  # Matriu binària: 1 si és un gra, 0 si no
        
    image.set_data(Z)
    image.set_cmap(cmap)
    image.set_clim(vmin, vmax)
    image.set_clim(vmin, vmax)
    
    if mida is not None: image.set_extent([0, mida[0], 0, mida[1]])
    if cbar: update_cbar(cbar, lims, units = units, colors = colLims) # Barra de colors.

def ajust_eixos(ax): # Elimina els eixos del mapa
    ax.set_axis_off()
    ax.set_aspect('equal') # Quadra l'aspecte de la imatge sense deformar-la.
    ax.set_facecolor('none') # Lleva el fons.
    ax.set_autoscale_on(True)
    
def create_cbar(figure, image):
    cax = figure.add_axes([0.9775, 0.11, 0.08266666, 0.77777])
    cbar = figure.colorbar(image, cax=cax, orientation='vertical')
    cbar.set_ticks([])

    cbar.limInf = cbar.ax.text(0.65, 0.02, '', ha='center', va='bottom',
        fontweight='bold', fontname='DejaVu Sans', rotation=90, transform=cbar.ax.transAxes)
    cbar.limSup = cbar.ax.text(0.65, 0.98, '', ha='center', va='top', 
        fontweight='bold', fontname='DejaVu Sans', rotation=90, transform=cbar.ax.transAxes)
    
    return cbar

def update_cbar(cbar, lims, units=None, colors = ('w', 'k')):
    vmin, vmax = lims  # Assignació directa
    color_inf, color_sup = colors
    cbar.ax.set_ylim(vmin, vmax)
    
    text_inf = f"{vmin:g} {units or ''}"
    text_sup = f"{vmax:g} {units or ''}"

    cbar.limInf.set_text(text_inf)
    cbar.limSup.set_text(text_sup)

    cbar.limInf.set_color(color_inf)
    cbar.limSup.set_color(color_sup)

def get_dimensions(axis, rect):
    fig = axis.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    bbox = axis.get_window_extent(renderer=renderer)

    width, height = bbox.width, bbox.height

    fig_w, fig_h = fig.get_size_inches()
    dpi = fig.dpi
    fig_w *= dpi
    fig_h *= dpi

    cax_pos = [(bbox.x1 + 0.05 * width) / fig_w, bbox.y0 / fig_h, 0.12 * width / fig_w * np.sqrt(rect), height / fig_h]

    return width, height, cax_pos

def set_dimensions(canvas, escala, cbar, rect, width, height, cax_pos):
    escala.mida(width, height, rect)

    if not cbar: return
    
    cbar.limInf.set_fontsize(height/22)
    cbar.limSup.set_fontsize(height/22)
    cbar.ax.set_position(cax_pos)

    canvas.draw_idle()
    
# ESCALA: Classe que afegeix l'escala al mapa. Per conveni estarà sempre en micres.
class Escala:
    def __init__(self, ax, color = 'w'):
        self.line = None
        self.text = None
        
        self.crea_escala(ax)
        self.color = color
    
    @property
    def color(self, value):
        return self._color
    
    @color.setter
    def color(self, value):
        self._color = value
        self.text.set_color(value)
        self.line.set_color(value)

    # --- Resta del codi ---
    def crea_escala(self, ax):
        xdim, ydim, xtext, ytext, num = self.calcula_coords(ax.get_xlim(), ax.get_ylim())
        self.line, = ax.plot(xdim, ydim)
        self.text = ax.text(xtext, ytext, self.set_text(num), ha='center', fontname='Arial', weight='bold')
        self.color = 'w'
        
    def set_text(self, num, units = r'$\mu$m', nsign = 2):
        if num <= 0.5: 
            units = 'nm'
            if num <= 0.1: nsign = 1
            num *= 1E3
        
        newNum = truncar_significatives(num, nsign, cap_a='avall')
        text = f'{newNum} {units}'
        
        return text

    # Calcula les coordenades on es posarà l'escala i el text.
    def calcula_coords(self, xlims, ylims):
        xmin, xmax = xlims; ymin, ymax = ylims
        midaX = xmax - xmin; midaY = ymax-ymin
        a = 2 * midaX
        num = a / 10

        # Escriu les coordenades de l'escala.
        x1 = 1/10 * midaX + xmin; x2 = 3/10 * midaX + xmin
        y1 = 1/10 * midaY + ymin
        xdim = [x1, x2]; ydim = [y1, y1]
        
        xtext = (x1+x2)/2; ytext = 1.3/10 * midaY + ymin # Escriu el text de l'escala.

        return xdim, ydim, xtext, ytext, num

    # Actualitza les coordenades de l'escala en cas de fer zoom o moure la imatge.
    def actualitza(self, xlims, ylims):
        xdim, ydim, xtext, ytext, num = self.calcula_coords(xlims, ylims)

        self.line.set_xdata(xdim)
        self.line.set_ydata(ydim)

        self.text.set_text(self.set_text(num))
        self.text.set_position((xtext, ytext))
    
    def mida(self, width, height, rect):
        self.text.set_fontsize(width/20*np.sqrt(rect))
        self.line.set_linewidth(height/100/np.sqrt(rect))