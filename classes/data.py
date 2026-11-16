"""Arxiu que conté les classes que emmagatzemen les dades de cada fitxer, amb les corresponents subclasses."""

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

import numpy as np

# Necessaris per a l'avaluació de les anotacions en temps d'execució.
from numpy.typing import NDArray  # ruff: ignore[typing-only-third-party-import]

from classes.protocols import ColorBool, SpecUnits  # ruff: ignore[typing-only-first-party-import]
from drawing.colormap import cmaps
from process.basics import find_nearest, set_lims
from process.converter import coords_to_pixel
from process.mathfuncs import DEFAULT_FUNCS, DEFAULT_PARAMS, DefaultFunction, DefaultParameter

if TYPE_CHECKING:
    from typing import Literal

    type IntSlice = slice[
        int,
        int,
        int | None,
    ]
else:
    IntSlice = slice


@dataclass
class FileData:
    """Emmagatzema les dades del fitxer que després es guardaran en un fitxer h5."""

    channel: dict[str, ChannelData]
    geometry: GeometryData
    objects: ObjectData

    def __post_init__(self) -> None:
        """Assigna el canal actual i la màscara booleana, si no existeix."""
        if self.objects.mask.size == 0:
            self.objects.mask = np.array(np.ones(self.geometry.dim[::-1]), dtype=np.bool_)


@dataclass
class Colors:
    """Colors dels objectes gràfics de cada canal."""

    cmap_c: str = ""  # Color.
    cmap_r: bool = False  # Normal o revertit.
    scale: ColorBool = "w"
    lim_inf: ColorBool = "w"
    lim_sup: ColorBool = "k"

    @property
    def cmap(self) -> str:
        """Color del mapa i la barra de colors."""
        return f"{self.cmap_c}_r" if self.cmap_r else self.cmap_c

    @property
    def lims(self) -> tuple[ColorBool, ColorBool]:
        """Color del text dels límits."""
        return self.lim_inf, self.lim_sup


@dataclass
class ChannelData:
    """Emmagatzema les dades de cada canal del fitxer."""

    name: str
    data: NDArray[np.float32]
    units: str
    lims: list[float] = field(default_factory=list, repr=False)
    color: Colors = field(default_factory=Colors)
    spectra: SpecData | None = None

    def __post_init__(self) -> None:
        """Assigna un color i uns límits predeterminats si no existeixen o s'han designat erròniament."""
        if not self.color.cmap_c:
            self.color.cmap_c = self.name if self.name in cmaps else "jet"

        if len(self.lims) == 0:
            self.update_lims()

    @property
    def ax_title(self) -> str:
        """Retorna el títol predeterminat per als eixos dels histogrames, mitjanes...

        Returns
        -------
        ax_title: str
            Títol de l'eix

        """
        return f"{self.name} ({self.units})" if self.units else f"{self.name}"

    @property
    def spec(self) -> SpecData:
        """Comprova que el canal és de tipus espectral.

        Raises
        ------
        ValueError
            Si el canal no conté dades espectrals

        """
        if self.spectra is None:
            msg = "Este fitxer no té dades espectral."
            raise ValueError(msg)

        return self.spectra

    def update_lims(self) -> None:
        """Actualització predeterminada dels límits després de certes operacions."""
        self.lims, self.data = set_lims(self.name, self.data)


@dataclass
class SpecData:
    """Emmagatzema les dades espectres d'un canal del fitxer."""

    xdata: dict[str, NDArray[np.float32]]
    raw_ydata: NDArray[np.uint16 | np.uint32]
    units: SpecUnits
    laser: float
    bkgdata: NDArray[np.uint16 | np.uint32] | None = None
    lims: list[float] = field(default_factory=list, repr=False)
    ccd: NDArray[np.float32] = field(default_factory=lambda: np.array([], dtype=np.float32))
    bkg_active: bool = True
    ccd_active: bool = False
    coords: tuple[int, int] = (0, 0)
    fits: dict[str, FitData] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        """Assigna límits i valors de la CCD a l'espectre si no existeixen.

        L'última comprovació serveix per a fer funcionar fitxers antics amb les versions noves.
        """
        if len(self.lims) == 0:
            self.lims = [round(float(min(self.x)), 3), round(float(max(self.x)), 3)]

        if self.ccd.size == 0:
            file = "process/CCD.csv"
            data = np.loadtxt(file, delimiter="\t", usecols=(0, 1), dtype=np.float32)

            left = data[0, 1]
            right = data[-1, 1]
            self.ccd = np.asarray(
                np.interp(self.xdata["nm"], data[:, 0], data[:, 1], left=left, right=right),
                dtype=float,
            )

        for fit in self.fits.values():
            for peak in fit.peaks.values():
                if "A" in peak.params:
                    peak.params["amp"] = peak.params.pop("A")

    @property
    def x(self) -> NDArray[np.float32]:
        """Retorna el vector del domini amb les unitats actuals."""
        return self.xdata[self.units]

    @property
    def y(self) -> NDArray[np.float32]:
        """Retorna les dades espectrals del píxel actual."""
        return np.array(self.ydata[*self.coords], dtype=np.float32)

    @property
    def bkg(self) -> NDArray[np.float32]:
        """Retorna el fons calculat per algorismes de suavitzat si existeix. Si no, retorna un vector buit."""
        if self.bkgdata is None:
            return np.zeros_like(self.y, dtype=np.float32)

        return np.array(self.bkgdata[*self.coords], dtype=np.float32)

    @property
    def xrange(self) -> slice[int, int, int]:
        """Retorna l'slice corresponent als límits actuals de l'eix X.

        Els índexs s'obtenen buscant les posicions més pròximes als límits
        definits en 'self.lims'. L'índex final queda exclòs de l'slice.
        """
        left_index, right_index = sorted(find_nearest(self.x, self.lims))

        return slice(left_index, right_index, 1)

    @property
    def ydata(self) -> NDArray[np.float32]:
        """Retorna la matriu de dades crues espectrals amb la transformació del CCD si s'ha seleccionat."""
        ydata = self.raw_ydata.astype(np.float32)

        if self.ccd_active:
            ydata /= self.ccd

        return ydata


@dataclass
class FitData:
    """Emmagatzema les dades de l'ajust corresponent.

    Copia les dades del fons espectral d'SpecData també, ja que diferents ajustos poden tindre fons diferents.
    """

    name: str
    units: SpecUnits
    r2: NDArray[np.float32]
    xrange: IntSlice
    config: dict[str, PeakDataConfig]
    bkgdata: NDArray[np.uint16 | np.uint32] | None = None
    peaks: dict[str, PeakData] = field(default_factory=dict)

    def bkg(self, coords: tuple[int, int], nzeros: int) -> NDArray[np.float32]:
        """Retorna el fons calculat per algorismes de suavitzat d'un píxel concret. Si no, retorna un vector buit.

        Parameters
        ----------
        coords: tuple[int, int]
            Coordenades del píxel
        nzeros: int
            Mida del domini del fons

        Returns
        -------
        bkg: NDArray[np.float32]
            Vector de dades del fons

        """
        if self.bkgdata is None:
            return np.array(np.zeros(nzeros), dtype=np.float32)

        return np.array(self.bkgdata[*coords], dtype=np.float32)


@dataclass
class PeakData:
    """Emmagatzema les dades de cada pic (o fons) ajustat."""

    ref: str
    name: str
    params: dict[str, NDArray[np.float32]] = field(default_factory=dict)
    function: str = "Gaussiana"
    is_bkg: bool = False

    @property
    def func(self) -> DefaultFunction:
        """Retorna la classe que controla les operacions de la funció donada."""
        return DEFAULT_FUNCS[self.function]

    def ydata(self, xdata: NDArray[np.float32], coords: tuple[int, int]) -> NDArray[np.float32]:
        """Retorna l'ajust corresponent amb un dels píxels del mapa.

        Parameters
        ----------
        xdata: NDArray[np.float32]
            Vector de dades del domini de la funció
        coords: tuple[int, int]
            Coordenades del píxel

        Returns
        -------
            Dades de la funció corresponent

        """
        params = {name: par[coords] for name, par in self.params.items()}

        return self.func.evaluate(xdata, params)

    @property
    def parameter_names(self) -> list[str]:
        """Retorna una llista que conté la clau de cada paràmetre.

        Returns
        -------
        parameter_names: list[str]
            Llista amb les claus

        """
        names = list(self.params)

        if self.func.derived_params is not None:
            derived = self.func.derived_params
            names.extend(derived)

        return names

    def get_parameter(self, name: str) -> NDArray[np.float32]:
        """Retorna el valor d'un paràmetre derivat a partir dels obtinguts per l'ajust.

        Parameters
        ----------
        name: str
            Nom del paràmetre

        Returns
        -------
        parameter: NDArray[np.float32]
            Matriu de valors del paràmetre

        Raises
        ------
        KeyError
            Si el nom del paràmetre no existeix.

        """
        if name in self.params:
            return self.params[name]

        derived = self.func.derived_params

        if derived is None or name not in derived:
            msg = f"El paràmetre {name!r} no està disponible per a la funció {self.function!r}"
            raise KeyError(msg)

        return derived[name](self.params)


@dataclass
class PeakDataConfig:
    """Emmagatzema la configuració inicial de cada pic (o fons) de l'ajust."""

    ref: str = ""
    name: str = ""
    function: str = "Gaussiana"
    unique: bool = False
    params: dict[str, DefaultParameter] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Crea els paràmetres per defecte si no existeixen."""
        if not self.params:
            self.params = {name: replace(DEFAULT_PARAMS[name]) for name in self.func.params}

    @property
    def func(self) -> DefaultFunction:
        """Retorna la classe que controla les operacions de la funció donada."""
        return DEFAULT_FUNCS[self.function]

    def update_function(self, func_key: str) -> None:
        """Canvia la funció i conserva els paràmetres compatibles.

        Parameters
        ----------
        func_key: str
            Clau de la funció

        """
        new_func = DEFAULT_FUNCS[func_key]
        old_params = self.params

        self.params = {name: (old_params[name] if name in old_params else DEFAULT_PARAMS[name])
                                                                for name in new_func.params}

        self.function = func_key

    def ydata(self, xdata: NDArray[np.float32]) -> NDArray[np.float32]:
        """Avalua el model amb els paràmetres de la classe.

        Parameters
        ----------
        xdata: NDArray[np.float32]
            Rang de dades sobre el que s'avalua la funció

        Returns
        -------
        result: NDArray[np.float32]
            Vector de valors del model en el rang donat

        """
        values = {name: param.value for name, param in self.params.items()}

        return self.func.evaluate(xdata, values)


@dataclass
class GeometryData:
    """Controla i defineix la geometria de cada fitxer compartida per cada canal comú."""

    dim: tuple[int, int]
    base_size: tuple[float, float]
    rotation: int = field(default=0, repr=False)
    flip: bool = field(default=False, repr=False)

    xlims: tuple[float, float] = field(default=(0.0, 0.0), repr=False)
    ylims: tuple[float, float] = field(default=(0.0, 0.0), repr=False)

    def __post_init__(self) -> None:
        """Comprova si hi ha límits establerts en cridar la classe."""
        if self.xlims[1] == 0 or self.ylims[1] == 0:
            self.reset_zoom()

    def reset_zoom(self) -> None:
        """La imatge retorna a la mida base màxima."""
        self.xlims = (0, self.base_size[0])
        self.ylims = (0, self.base_size[1])

    @property
    def xdim(self) -> int:
        """Retorna la dimensió horitzontal de la matriu de dades."""
        return self.dim[0]

    @property
    def ydim(self) -> int:
        """Retorna la dimensió vertical de la matriu."""
        return self.dim[1]

    @property
    def xylims(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Retorna els límits horitzontals i verticals de la imatge actual."""
        return self.xlims, self.ylims

    @xylims.setter
    def xylims(self, value: tuple[tuple[float, float], tuple[float, float]]) -> None:
        """Estableix els nous límits horitzontals i verticals de la imatge."""
        self.xlims, self.ylims = value

    @property
    def size(self) -> tuple[float, float]:
        """Retorna la mida horitzontal i vertical actual de la imatge."""
        return self.xlims[1] - self.xlims[0], self.ylims[1] - self.ylims[0]

    @property
    def rect(self) -> float:
        """Retorna el factor corrector que s'emprarà per a calcular les dimensions de la barra de colors."""
        return self.size[1] / self.size[0]

    @property
    def region(self) -> tuple[slice[int, int, None], slice[int, int, None]]:
        """Retorna la regió del mapa mostrada en el visor."""
        x0, x1, y0, y1 = self.limit_pixels()
        return np.s_[y0:y1, x0:x1]

    def rotate_lims(self, rotation: Literal[0, 1, 2, 3], *, flip: bool = False) -> None:
        """Gira i volteja els límits de la imatge.

        Parameters
        ----------
        rotation: Literal[0, 1, 2, 3]
            Determina quantes rotacions horàries s'apliquen.
        flip: bool = False
            Indica si la imatge s'ha de voltejar.

        """
        xsize, ysize = self.base_size
        xlims, ylims = self.xylims
        xnew, ynew = xlims, ylims

        match rotation:
            case 0:
                pass
            case 1:
                xnew, ynew = ynew, (ysize - xlims[1], ysize - xlims[0])
            case 2:
                xnew, ynew = (xsize - xlims[1], xsize - xlims[0]), (ysize - ynew[1], ysize - ynew[0])
            case 3:
                xnew, ynew = (xsize - ynew[1], xsize - ynew[0]), xlims

        if flip:
            xnew = (xsize - xnew[1], xsize - xnew[0])

        self.xylims = xnew, ynew

    def limit_pixels(self) -> tuple[int, int, int, int]:
        """Retorna els píxels relacionats amb els límits de la imatge.

        Returns
        -------
        x0: int
            Píxel esquerre
        x1: int
            Píxel dret
        y0: int
            Píxel inferior
        y1: int
            Píxel superior

        """
        coords = [(self.xlims[0], self.ylims[0]), (self.xlims[1], self.ylims[1])]
        coord0, coord1 = coords_to_pixel(coords, self.dim, self.base_size)
        x0, y0 = coord0
        x1, y1 = coord1

        return x0, x1, y0, y1


@dataclass
class ObjectData:
    """Conté els objectes possibles d'un fitxer."""

    profiles: dict[int, ProfileData] = field(default_factory=dict, repr=False)
    mask: NDArray[np.bool_] = field(default_factory=lambda: np.array([], dtype=np.bool_))


@dataclass
class ProfileData:
    """Conté les dades d'un perfil dibuixat en la figura."""

    line: list[tuple[int, int]] = field(default_factory=list)
    length: float = field(default_factory=float)

    @property
    def lims(self) -> list[tuple[int, int]]:
        """Torna el punt inicial i final del perfil."""
        return [self.line[0], self.line[-1]]
