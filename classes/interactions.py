"""Controla i activa les interaccions generals del programa."""

from tkinter import Event, TclError
from typing import TYPE_CHECKING, Literal, cast

from matplotlib.backend_bases import MouseButton

import process.images as zoom
from process.converter import coords_to_pixel

if TYPE_CHECKING:
    from tkinter import Tk

    from matplotlib.backend_bases import MouseEvent

    from classes.data import GeometryData
    from classes.protocols import NotebookProtocol, TkCanvasProtocol
    from classes.views import FileView, MapView
    from POEMAS import Aplicacio as App


class AppInteraction:
    """Interaccions bàsiques de l'aplicació controlades per dreceres de teclat."""

    def __init__(self, app: App) -> None:
        """Activa les interaccions i les lliga a l'objecte corresponent.

        Parameters
        ----------
        app: App
            Aplicació pare

        """
        self.get_file = app.get_file
        self.set_file = app.set_file
        self.files = app.files

        self._active_timer_id: str | None = None
        self._all_timer_id: str | None = None
        self._drag_tab: int | None = None

        self._root_binds(app.root, app.notebook)
        self._notebook_binds(app.notebook)

    def _root_binds(self, root: Tk, notebook: NotebookProtocol) -> None:
        """Connecta les interaccions relacionades amb l'aplicació.

        Parameters
        ----------
        root: Tk
            Finestra pare de l'aplicació
        notebook: NotebookProtocol
            Espai de treball principal

        """
        root.bind("<Configure>", lambda _: self._trigger_resize(root=root))
        root.bind_all("<Up>", lambda _: self._next_tab(notebook=notebook, forward=True))
        root.bind_all("<Down>", lambda _: self._next_tab(notebook=notebook, forward=False))
        root.bind_all("<Right>", lambda _: (self._next_tab(notebook=self.current_file.notebook, forward=True)
                           if self.current_file else "break"))
        root.bind_all("<Left>", lambda _: (self._next_tab(notebook=self.current_file.notebook, forward=False)
                           if self.current_file else "break"))

    def _notebook_binds(self, notebook: NotebookProtocol) -> None:
        """Connecta les interaccions relacionades amb l'aplicació.

        Parameters
        ----------
        notebook: NotebookProtocol
            Espai de treball del fitxer corresponent

        """
        notebook.bind("<<NotebookTabChanged>>", self._on_file_changed)
        notebook.bind("<ButtonPress-1>", lambda e: self._on_press(event=e, notebook=notebook))
        notebook.bind("<B1-Motion>", lambda e: self._on_drag(event=e, notebook=notebook))
        notebook.bind("<ButtonRelease-1>", lambda _: self._on_release())

    @property
    def current_file(self) -> FileView | None:
        """Retorna el fitxer actual, i no hi ha cap obert, dona error.

        Returns
        -------
        file: FileProtocol
            Fitxer obert i mostrat en pantalla actualment

        """
        file = self.get_file()
        if file is None:
            return None

        return file

    @current_file.setter
    def current_file(self, file: FileView | None) -> None:
        """Assigna un nou fitxer obert actual.

        Parameters
        ----------
        file: FileProtocol
            Nou fitxer. Si no queden més fitxer, llavors és None

        """
        self.set_file(file)

    def _trigger_resize(self, root: Tk) -> None:
        """Controla l'actualització de la mida dels objectes de l'aplicació si també en canvia la finestra.

        Parameters
        ----------
        root: Tk
            Finestra pare de l'aplicació

        """
        if self.current_file is None:
            return

        tab = self.current_file.tab

        # Cancel·lar el timer del resize ràpid del canal actiu
        if self._active_timer_id:
            tab.after_cancel(self._active_timer_id)

        # Programar el resize del canal actiu després de 50 ms
        self._active_timer_id = tab.after(25, self._resize_active)

        # Cancel·lar i programar el timer global del retard de 1 segon
        if self._all_timer_id:
            root.after_cancel(self._all_timer_id)

        self._all_timer_id = root.after(1000, self._resize_all)

    @staticmethod
    def _next_tab(notebook: NotebookProtocol, *, forward: bool) -> Literal["break"]:
        """Canvia a finestra anterior o posterior.

        Parameters
        ----------
        notebook: NotebookProtocol
            Espai de treball de l'aplicació
        forward: bool
            True: Posterior, False: Anterior

        Returns
        -------
        break: Literal["break"]
            Indica que la interacció s'ha acabat

        """
        if not notebook or not notebook.tabs():
            return "break"

        actual = notebook.index(notebook.select())
        total = notebook.index("end")
        nova = (actual + 1) % total if forward else (actual - 1) % total
        notebook.select(nova)

        return "break"

    def _resize_active(self) -> None:
        """Executa el resize només del canal/pestanya activa."""
        self._active_timer_id = None

        if self.current_file is not None:
            self.current_file.mapview.resize()

    # -----------------------
    def _resize_all(self) -> None:
        """Executa el resize de la resta dels fitxers després d'1 segon."""
        self._all_timer_id = None

        for file in self.files.values():
            if file is not self.current_file:
                file.mapview.resize()

    def _on_file_changed(self, event: Event) -> None:
        """Canvia de fitxer actual quan es canvia de pestanya.

        Parameters
        ----------
        event: Event
            Interacció de l'espai de treball

        """
        notebook = cast("NotebookProtocol", event.widget)
        tab_id = notebook.select()

        for f in self.files.values():
            if str(f.tab) == tab_id:
                self.current_file = f
                break

    def _on_press(self, event: Event, notebook: NotebookProtocol) -> None:
        """Indica si s'està polsant sobre una pestanya.

        Parameters
        ----------
        notebook: NotebookProtocol
            Espai de treball de l'aplicació
        event: Event
            Interacció de l'espai de treball

        """
        try:
            self._drag_tab = notebook.index(f"@{event.x},{event.y}")
        except TclError:
            self._drag_tab = None

    def _on_drag(self, event: Event, notebook: NotebookProtocol) -> None:
        """Controla l'arrossegament de pestanyes dins de l'espai de treball.

        Parameters
        ----------
        notebook: NotebookProtocol
            Espai de treball de l'aplicació
        event: Event
            Interacció de l'espai de treball

        """
        if self._drag_tab is None:
            return

        try:
            target = notebook.index(f"@{event.x},{event.y}")
        except TclError:
            return

        if target == self._drag_tab:
            return

        # Mou la pestanya
        notebook.insert(target, str(self._drag_tab))

        # Reordena el diccionari de fitxers
        keys = list(self.files.keys())
        name = keys.pop(self._drag_tab)
        keys.insert(target, name)

        old_files = dict(self.files)
        self.files.clear()

        for k in keys:
            self.files[k] = old_files[k]

        # Actualitza l'índex que s'està arrossegant
        self._drag_tab = target

    def _on_release(self) -> None:
        """Retorna a l'estat neutre quan es deixa de polsar sobre una pestanya."""
        self._drag_tab = None


class MapInteraction:
    """Controla les interaccions relacionades amb el mapa lligat a cada fitxer."""

    def __init__(self, map_view: MapView) -> None:
        """Activa les interaccions del canvas del fitxer corresponent."""
        self.mapview = map_view
        self.geometry: GeometryData = map_view.file.geometry

        self.press: tuple[float, float] | None = None

        self._connect_binds(self.mapview.canvas)

    def _connect_binds(self, canvas: TkCanvasProtocol) -> None:
        """Connecta les interaccions al canvas del fitxer corresponent.

        Parameters
        ----------
        canvas: TkCanvasProtocol
            Canvas del fitxer

        """
        canvas.mpl_connect("scroll_event", self._scroll)
        canvas.mpl_connect("button_press_event", self._press)
        canvas.mpl_connect("button_release_event", lambda _: self._release())
        canvas.mpl_connect("motion_notify_event", self._motion)
        canvas.mpl_connect("key_press_event", lambda e: zoom.copy_figure(self.mapview.figure)
                                        if e.key == "ctrl+c" else None)
        canvas.mpl_connect("key_press_event", lambda e: self.mapview.base_size()
                                        if e.key == "ctrl+z" else None)

    def _scroll(self, event: MouseEvent) -> None:
        """Transforma els límits de la imatge per a simular-ne l'augment o minvament (zoom).

        Parameters
        ----------
        event: MouseEvent
            Interacció del ratolí sobre la imatge

        """
        if not event.inaxes or isinstance(event.button, MouseButton):
            return
        if event.xdata is None or event.ydata is None or event.button is None:
            return

        self.geometry.xylims = zoom.zoom(
            xydata=(event.xdata, event.ydata),
            button=event.button,
            old_lims=self.geometry.xylims,
            base_size=self.geometry.base_size)
        self.mapview.refresh_geometry()

    def _press(self, event: MouseEvent) -> None:
        """Controla si s'està polsant sobre la imatge.

        Parameters
        ----------
        event: MouseEvent
            Interacció del ratolí sobre la imatge

        """
        if event.inaxes != self.mapview.axis:
            return

        if event.xdata is None or event.ydata is None:
            return

        self.press = event.xdata, event.ydata

        if not hasattr(self.mapview.file, "specview"):
            return

        pixels = coords_to_pixel([(event.xdata, event.ydata)], self.geometry.dim, base_size=self.geometry.base_size)[0]

        if not self.mapview.file.objects.mask[pixels[1], pixels[0]]:
            return

        self.mapview.file.specview.plot_pixel(*pixels)

    def _release(self) -> None:
        """Indica que s'ha deixat de polsar sobre la imatge."""
        self.press = None

    def _motion(self, event: MouseEvent) -> None:
        """Transforma els límits de la imatge per a simular-ne l'arrossegament.

        Parameters
        ----------
        event: MouseEvent
            Interacció del ratolí sobre la imatge

        """
        if event.inaxes != self.mapview.axis or self.press is None or event.xdata is None or event.ydata is None:
            return

        self.geometry.xylims = zoom.on_motion(
            xydata=(event.xdata, event.ydata),
            old_lims=self.geometry.xylims,
            base_size=self.geometry.base_size,
            press=self.press)

        self.mapview.refresh_geometry()
