from typing import Tuple
from tkinter import TclError

import process.images as zoom
from process.converter import coords_to_pixel
from drawing import mapdraw

class RootInteraction:
    def __init__(self, parent):
        self.parent = parent
        self.files = parent.files

        self._active_timer_id = None
        self._restants_timer_id = None
        self._drag_tab = None

        self.root.bind("<Configure>", self._trigger_resize)

        self.root.bind_all("<Up>", lambda e: self._next_tab(True, self.notebook))
        self.root.bind_all("<Down>", lambda e: self._next_tab(False, self.notebook))

        self.root.bind_all("<Right>", lambda e: self._next_tab(True, self.current_file.view.selector)
                           if self.current_file else "break")
        self.root.bind_all("<Left>", lambda e: self._next_tab(False, self.current_file.view.selector)
                           if self.current_file else "break")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_file_changed)
        self.notebook.bind("<ButtonPress-1>", self._on_press)
        self.notebook.bind("<B1-Motion>", self._on_drag)
        self.notebook.bind("<ButtonRelease-1>", self._on_release)

    @property
    def root(self):
        return self.parent.root

    @property
    def notebook(self):
        return self.parent.notebook

    @property
    def current_file(self):
        return self.parent.current_file

    @current_file.setter
    def current_file(self, value):
        self.parent.current_file = value

    def _next_tab(self, next: bool, notebook):
        if not notebook or not notebook.tabs():
            return "break"

        actual = notebook.index(notebook.select())
        total = notebook.index("end")
        nova = (actual + 1) % total if next else (actual - 1) % total
        notebook.select(nova)

        return "break"

    def _trigger_resize(self, event):
        if not self.current_file:
            return

        tab = self.current_file.view.tab

        # Cancel·lar el timer del resize ràpid del canal actiu
        if self._active_timer_id:
            tab.after_cancel(self._active_timer_id)

        # Programar el resize del canal actiu després de 50 ms
        self._active_timer_id = tab.after(25, self._resize_active)

        # Cancel·lar i programar el timer global del retard de 1 segon
        if self._restants_timer_id:
            self.root.after_cancel(self._restants_timer_id)

        self._restants_timer_id = self.root.after(1000, self._resize_restants)

    # -----------------------
    def _resize_active(self):
        """Executa el resize només de
        l canal/pestanya activa."""
        if not self.current_file: return

        self.current_file.view.map.zoom.resize()
        self._active_timer_id = None

    # -----------------------
    def _resize_restants(self):
        """Executa el resize de la resta dels fitxers després de 1 segon."""
        if not self.current_file: return

        for f in self.files.values():
            if f is not self.current_file:
                f.view.map.zoom.resize()

        self._restants_timer_id = None

    def _on_file_changed(self, event):
        notebook = event.widget
        tab_id = notebook.select()
        if not self.current_file: return

        for f in self.files.values():
            if str(f.view.tab) == tab_id:
                self.current_file = f
                f.view.map.header.set_channel(f.current_channel)
                break

    def _on_press(self, event):
        try:
            self._drag_tab = self.notebook.index(f"@{event.x},{event.y}")
        except TclError:
            self._drag_tab = None

    def _on_drag(self, event):
        if self._drag_tab is None: return

        try:
            target = self.notebook.index(f"@{event.x},{event.y}")
        except TclError:
            return

        if target == self._drag_tab: return

        # Mou la pestanya
        self.notebook.insert(target, self._drag_tab)

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

    def _on_release(self, event):
        self._drag_tab = None

class MapInteraction:
    def __init__(self, map_view):
        self.map = map_view
        self.geometry = map_view.geometry

        self.press = None

        self.map.canvas.mpl_connect('scroll_event', self._scroll)
        self.map.canvas.mpl_connect('button_press_event', self._press)
        self.map.canvas.mpl_connect('button_release_event', self._release)
        self.map.canvas.mpl_connect('motion_notify_event', self._motion)

        self.map.canvas.mpl_connect("key_press_event", lambda e: zoom.copy_figure(self.map.figure) if e.key == "ctrl+c" else None)
        self.map.canvas.mpl_connect("key_press_event", lambda e: self.base_size() if e.key == "ctrl+z" else None)

    def _scroll(self, event):
        if not event.inaxes: return
        self.geometry.xylims = zoom.zoom(event, self.geometry.xylims, self.geometry.midaBase)
        self.map.refresh_geometry()

    def _press(self, event):
        if event.inaxes != self.map.axis: return
        self.press = event.xdata, event.ydata

        if event.xdata==None or event.ydata==None: return
        if not hasattr(self.map.model, "spectrum"): return

        pixels = coords_to_pixel([(event.xdata, event.ydata)], self.geometry.N, self.geometry.midaBase)[0]
        self.map.model.spectrum.plot_pixel(*pixels)

    def _release(self, event):
        self.press = None

    def _motion(self, event):
        if event.inaxes != self.map.axis or not self.press: return
        self.geometry.xylims = zoom.on_motion(event, self.geometry.xylims, self.geometry.midaBase, self.press)
        self.map.refresh_geometry()

    def resize(self, event=None):
        self.dimensions = mapdraw.get_dimensions(self.map.axis, self.geometry.rect)

    def base_size(self):
        self.geometry.reset_zoom()
        self.map.refresh_geometry()
        self.resize()

    @property
    def dimensions(self):
        return self._dimensions

    @dimensions.setter
    def dimensions(self, value: Tuple[float]):
        self._dimensions = value
        mapdraw.set_dimensions(self.map.canvas, self.map.escala, self.map.cbar, self.map.geometry.rect, *value)