"""Classes que controlen els ginys generals dels mapes i els espectres."""
from typing import TYPE_CHECKING, Protocol, TypedDict, cast, is_typeddict

from typing_extensions import TypeForm

from .widgets import Widget

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

    from classes.data import ChannelData, FitData, PeakData, SpecData
    from classes.protocols import GestorProtocol
    from classes.views import FileView
    from window.widgets import GenericWidgets


class TypedDictMetadata(Protocol):
    """Claus base que utilitzen els TypedDict."""

    __required_keys__: frozenset[str]
    __optional_keys__: frozenset[str]


def set_selector(combo: Widget[str], items: dict[str, str], current: str | None) -> str | None:
    """Canvia els valors d'un combobox segons els ítems donats.

    combo: Widget[str] (ttk.Combobox)
        Giny combobox
    items: dict[str, str]
        Indica els nous valors de les opcions i la configuració
    current: str | None
        Clau del nou valor actual

    Returns
    -------
    current: str | None
        Nou valor que pot canviar si no s'ha donat cap o si no existia eixa clau a ítems.

    """
    if not items:
        combo.config(values=[])
        combo.options = {}
        combo.set(value=None)
        return None

    keys = list(items)
    labels = list(items.values())

    combo.config(values=keys)
    combo.options = dict(zip(keys, labels, strict=False))

    if current not in keys:
        current = keys[0]

    combo.set(current)

    return current


def clear_selector(combo: Widget[str]) -> None:
    """Buida les opcions del combobox.

    Parameters
    ----------
    combo: Widget[str] (ttk.Combobox)
        Giny combobox

    """
    combo.config(values=[])
    combo.options = {}
    combo.set(value="")


def check_widgets[TWidgets](widgets: GenericWidgets, dict_typed: TypeForm[TWidgets]) -> TWidgets:
    """Comprova els ginys donats contenen almenys els ginys base.

    Parameters
    ----------
    widgets: GenericWidgets
        Col·lecció de ginys genèrica
    dict_typed: TypeForm[TWidgets]
        TypedDict amb els ginys base obligatoris

    Returns
    -------
    TWidgets
        Ginys que corresponen a claus del dict_typed donat.

    Raises
    ------
    TypeError
        Si la variable dict_typed no és TypeError o si cap clau de TypedDict no és un objecte Widget[str]
    ValueError
        Si falten els ginys obligatoris declarats a TypedDict

    """
    if not is_typeddict(dict_typed):
        msg = "El tipus proporcionat no és un TypedDict."
        raise TypeError(msg)

    typed_dict = cast("TypedDictMetadata", dict_typed)
    required_keys = typed_dict.__required_keys__
    optional_keys = typed_dict.__optional_keys__

    missing = required_keys.difference(widgets)

    if missing:
        msg = f"Falten els ginys obligatoris: {', '.join(sorted(missing))}."
        raise ValueError(msg)

    keys = required_keys | optional_keys
    result = {key: widgets[key] for key in keys if key in widgets}

    for key, widget in result.items():
        if not isinstance(widget, Widget):
            msg = f"El valor de {key!r} no és una instància de Widget."
            raise TypeError(msg)

        if widget.var_type is not str:
            msg = f"El giny {key!r} ha de tindre var_type=str."
            raise TypeError(msg)

    return cast("TWidgets", result)


class MapWidgets(TypedDict):
    """Ginys obligatoris per a emprar MapMixin."""

    file: Widget[str]
    channel: Widget[str]


class MapMixin:
    """Classe que conté les operacions principals dels ginys file i channel associades al mapa corresponent."""

    widgets: GenericWidgets

    def __init__(self, gestor: GestorProtocol) -> None:
        """Inicialitza els objectes essencials per a operar amb els ginys.

        update: bool
            Indica si un canvi aplicat sobre el giny també es transmet al mapa principal automàticament
        intersect:
            Indica si en operar amb més d'un arxiu es vol obtindre la intersecció (True) o la unió dels canals (False).

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        self._file: FileView = gestor.current_file
        self._channel: ChannelData = self._file.current_channel

        self.files: dict[str, FileView] = gestor.files

        self.file_key: str = self.file.name
        self.channel_key: str = self.channel.name

        self._file_ref: FileView | None = None
        self.update: bool = True
        self.intersect: bool = True

        self.notebook = gestor.notebook

    @property
    def map_widgets(self) -> MapWidgets:
        """Comprova si els ginys donats contenen file i channel."""
        return check_widgets(self.widgets, MapWidgets)

    @property
    def file(self) -> FileView:
        """Retorna el fitxer actual."""
        return self._file

    @file.setter
    def file(self, file_key: str) -> None:
        if file_key != "Tots els fitxers":
            self._file = self.files[file_key]
        self.file_key = file_key
        self.update_channels()

    @property
    def file_ref(self) -> FileView:
        """Retorna el fitxer de referència quan s'opera entre diferents fitxers.

        Returns
        -------
        file_ref: FileView
            Fitxer de referència

        Raises
        ------
        ValueError
            Si no hi ha cap fitxer de referència

        """
        if self._file_ref is None:
            msg = "No hi ha cap fitxer de referència seleccionat."
            raise ValueError(msg)

        return self._file_ref

    @file_ref.setter
    def file_ref(self, value: str) -> None:
        self._file_ref = self.files[value]
        self.update_channels()

    @property
    def channel(self) -> ChannelData:
        """Retorna el canal seleccionat."""
        return self._channel

    @channel.setter
    def channel(self, value: str | None) -> None:
        if value is None:
            return
        if value in self.file.channel:
            self._channel = self.file.channel[value]
        self.channel_key = value

        if self.file_key == "Tots els fitxers":
            return

        if self.update:
            self.file.notebook.select(self.file.channel_tabs[self._channel.name])

    def files_list(self) -> list[FileView]:
        """Retorna la llista de fitxers sobre la que es fa una certa operació.

        Returns
        -------
        files: list[FileView]
            Llista amb els fitxers

        """
        if self.file_key == "Tots els fitxers":
            files = list(self.files.values())
        else:
            files = [self.file]
            if self._file_ref is not None and self.file_ref is not self.file:
                files.append(self.file_ref)
            if self.update:
                self.notebook.select(self.file.tab)

        return files

    def compare_files(self) -> tuple[list[str], list[str], str]:
        """Compara els canals que comparteixen el fitxer de referència i un altre i canvia les varaibles si escau.

        Returns
        -------
        list_files: list[str]
            Llista de les claus dels fitxers existents amb l'opció de triar tots els fitxers
        channels: list[str]
            Llista de les claus resultants de la intersecció dels canals d'ambdós fitxers
        init_channel: str
            Clau del fitxer en comú sobre el que s'opera

        """
        list_files = ["Tots els fitxers", *list(self.files)]
        self._file_ref = self.files[list_files[1]]

        channels = list(self.file_ref.channel.keys() & self.file.channel.keys())

        init_channel = self.channel.name if self.channel.name in channels else channels[0]

        return list_files, channels, init_channel

    def update_channels(self) -> None:
        """Actualitza la llista de canals segons s'haja triat intersecció o unió."""
        if not hasattr(self, "file") or not hasattr(self, "widgets"):
            return

        files = self.files_list()
        channels = list(files[0].channel)

        if self.intersect:
            common = set.intersection(*(set(f.channel) for f in files))
            channels = [ch for ch in channels if ch in common]
        else:
            for f in files[1:]:
                for ch in f.channel:
                    if ch not in channels:
                        channels.append(ch)

        self.update_channel_combobox(channels)

    def update_files(self, files: list[str]) -> None:
        """Actualitza les opcions del giny file."""
        dict_files = {file: file for file in files}
        set_selector(combo=self.map_widgets["file"], items=dict_files, current=self.file_key)

    def update_channel_combobox(self, channels: list[str]) -> None:
        """Actualitza les opcions del giny channel."""
        dict_channels = {channel: channel for channel in channels}
        current = set_selector(combo=self.map_widgets["channel"], items=dict_channels, current=self.channel_key)

        if current is not None:
            self.channel = current


class SpecWidgets(TypedDict):
    """Ginys obligatoris per a emprar SpecMixin."""

    fit: Widget[str]
    peak: Widget[str]
    parameter: Widget[str]


class SpecMixin:
    """Classe que conté les operacions principals dels ginys fit, peak i parameter de l'espectre corresponent."""

    widgets: GenericWidgets

    def __init__(self, spectra: SpecData) -> None:
        """Inicialitza els objectes essencials per a operar amb els ginys.

        include_rawdata: bool
            Indica si es pot triar l'opció de veure les dades creus de l'espectre
        include_r2: bool
            Indica si es vol treballar amb les dades del coeficient r2 de l'ajust corresponent

        Parameters
        ----------
        spectra: SpecData
            Classe amb les dades espectrals

        """
        self.spectra = spectra

        self._fit: FitData | None = None
        self._peak: PeakData | None = None
        self._parameter: NDArray[np.float32] | None = None

        self.fit_key: str = "rawdata"
        self.peak_key: str | None = None
        self.parameter_key: str | None = None

        self.include_rawdata: bool = False
        self.include_r2: bool = False

    @property
    def spec_widgets(self) -> SpecWidgets:
        """Comprova si els ginys donats contenen fit, peak i parameter."""
        return check_widgets(self.widgets, SpecWidgets)

    @property
    def fit(self) -> FitData:
        """Retorna l'ajust corresponent si existeix. En el cas d'haver triat l'opció rawdata, passa a ser None.

        Returns
        -------
        fit: FitData
            Ajust seleccionat

        Raises
        ------
        ValueError
            Si no hi ha cap ajust triat

        """
        if self._fit is None:
            msg = "No existeix cap ajust actualment."
            raise ValueError(msg)

        return self._fit

    @fit.setter
    def fit(self, value: str) -> None:
        fits = self.spectra.fits

        if value == "rawdata" and self.include_rawdata:
            self.fit_key = "rawdata"
            self._fit = None
            self._peak = None
            self._parameter = None
            self._select_rawdata()
            return

        if value not in fits:
            return

        self._fit = fits[value]
        self.fit_key = value

        # Seleccionem el primer pic
        if self.fit.peaks:
            self._peak = next(iter(self.fit.peaks.values()))
            self.peak_key = self._peak.ref

            if self.parameter_key is not None and self.parameter_key in self.peak.parameter_names:
                self._parameter = self.peak.get_parameter(self.parameter_key)
            else:
                self.parameter_key, self._parameter = next(iter(self.peak.params.items()))

        self._select_fit()
        self.update_peaks()

    @property
    def peak(self) -> PeakData:
        """Retorna el pic corresponent si existeix. En el cas d'haver triat l'opció rawdata, passa a ser None.

        Returns
        -------
        peak: PeakData
            Pic seleccionat

        Raises
        ------
        ValueError
            Si no hi ha cap pic triat

        """
        if self._peak is None:
            msg = "No existeix cap pic dins de l'ajust."
            raise ValueError(msg)

        return self._peak

    @peak.setter
    def peak(self, value: str | None) -> None:
        if value is None:
            clear_selector(self.spec_widgets["peak"])
            self._peak = None
            self.peak_key = None

            self.parameter = None
            return

        if value == "r2" and self.include_r2:
            self._peak = None
            self.peak_key = "r2"
            self.parameter = None

            self._select_r2()
            return

        if value not in self.fit.peaks:
            return

        self._peak = self.fit.peaks[value]
        self.peak_key = value

        # Conservem el paràmetre si existeix en el nou pic
        if self.parameter_key is not None and self.parameter_key in self.peak.parameter_names:
            self._parameter = self.peak.get_parameter(self.parameter_key)
        else:
            self.parameter_key, self._parameter = next(iter(self.peak.params.items()))

        self._select_peak()
        self.update_params()

    @property
    def parameter(self) -> NDArray[np.float32]:
        """Retorna el paràmetre corresponent si existeix. Si s'ha triat l'opció rawdata o r2, passa a ser None.

        Returns
        -------
        peak: PeakData
            Pic seleccionat

        Raises
        ------
        ValueError
            Si no hi ha cap pic triat

        """
        if self._parameter is None:
            msg = "No existeix cap paràmetre per al pic triat."
            raise ValueError(msg)

        return self._parameter

    @parameter.setter
    def parameter(self, value: str | None) -> None:
        self.parameter_key = value

        if value is None:
            clear_selector(self.spec_widgets["parameter"])
            self._parameter = None
            return

        if value not in self.peak.parameter_names:
            return

        self._parameter = self.peak.get_parameter(value)
        self._select_parameter()

    def update_fits(self) -> None:
        """Actualitza les opcions del giny fit."""
        fits = list(self.spectra.fits)
        if self.include_rawdata:
            fits.insert(0, "rawdata")

        current = set_selector(combo=self.spec_widgets["fit"], items={fit: fit for fit in fits}, current=self.fit_key)
        if current is not None:
            self.fit = current

    def update_peaks(self) -> None:
        """Actualitza les opcions del giny peak."""
        dict_peaks = {peak.name: ref for ref, peak in self.fit.peaks.items()}
        if self.include_r2:
            dict_peaks["r2"] = "r2"

        self.peak = set_selector(combo=self.spec_widgets["peak"], items=dict_peaks, current=self.peak_key)

    def update_params(self) -> None:
        """Actualitza les opcions del giny parameter."""
        dict_params = {param: param for param in self.peak.parameter_names}
        self.parameter = set_selector(combo=self.spec_widgets["parameter"],
                                                  items=dict_params, current=self.parameter_key)

    # Hooks
    def _select_fit(self) -> None:
        """Operació opcional i particular d'una classe que crida SpecMixin quan selecciona un ajust."""

    def _select_rawdata(self) -> None:
        """Operació opcional i particular d'una classe que crida SpecMixin quan selecciona l'opció 'rawdata' de fit."""

    def _select_peak(self) -> None:
        """Operació opcional i particular d'una classe que crida SpecMixin quan selecciona un pic."""

    def _select_r2(self) -> None:
        """Operació opcional i particular d'una classe que crida SpecMixin quan selecciona l'opció 'r2' de peak."""

    def _select_parameter(self) -> None:
        """Operació opcional i particular d'una classe que crida SpecMixin quan selecciona un paràmetre."""
