"""Classe base per a gestionar les accions comunes de l'aplicació."""
from abc import ABC, abstractmethod
from functools import partial
from tkinter import Event, Menu, TclError, messagebox
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from classes.protocols import GestorProtocol
    from classes.views import FileView
    from POEMAS import Aplicacio as App
    from window.builder import BaseWindow


class BaseMenu(ABC):
    """Classe base per a gestionar les accions comunes de l'aplicació."""

    def __init__(self, app: App) -> None:
        """Inicia el menú i hereta els atributs necessaris de l'aplicació principal.

        Parameters
        ----------
        app: App
            Aplicació principal

        """
        self.files = app.files
        self.root = app.root
        self.notebook = app.notebook

        self._windows: dict[type[BaseWindow], BaseWindow] = {}

        self.get_file = app.get_file
        self.set_file = app.set_file

        self.submenu = Menu(
            app.menu,
            tearoff=0,
            font=("Helvetica", 12, "bold"),
            bg="#2b2b2b",
            fg="#eeeeee",
            activebackground="#3a7ff6",
            activeforeground="#ffffff",
        )

    @abstractmethod
    def _add_menu(self, menu: Menu) -> None:
        """Registra les subpestanyes del menú.

        Parameters
        ----------
        menu: Menu
            Objecte menú de tkinter.

        """

    @property
    def current_file(self) -> FileView:
        """Retorna el fitxer actual, i no hi ha cap obert, dona error.

        Returns
        -------
        file: FileView
            Fitxer obert i mostrat en pantalla actualment

        Raises
        ------
        RuntimeError
            Si no hi ha cap fitxer obert

        """
        file = self.get_file()
        if file is None:
            msg = "No hi ha cap fitxer obert"
            raise RuntimeError(msg)

        return file

    @current_file.setter
    def current_file(self, file: FileView | None) -> None:
        """Assigna un nou fitxer obert actual.

        Parameters
        ----------
        file: FileView
            Nou fitxer. Si no queden més fitxers, llavors és None

        """
        self.set_file(file)

    def add_tab(self, text: str | None = None, func: Callable[[], object] | None = None, shortcut: str = "",
                *, file_check: bool = True, args: tuple[object, ...] | None = None,
                kwargs: dict[str, object] | None = None) -> None:
        """Afig una subpestanya al menú que executarà una acció o obrirà una subfinestra.

        Parameters
        ----------
        text: str | None = None
            Nom de la subpestanya. Si és None, crea un espai.
        func: Callable[[], None] | None = None
            Funció que s'executa quan cliques sobre la pestanya.
        shortcut: str = ""
            Drecera de teclat que executa l'acció. Opcional
        file_check: bool = True
            Comprova si hi ha cap fitxer obert abans d'executar res.
        args: tuple[object, ...] | None = None
            Variables sense nom que s'afigen a la funció
        kwargs: dict[str, object] | None = None
            Variables anomenades que s'afigen a la funció

        Raises
        ------
        ValueError
            Si no hi ha cap funció declarada

        """
        if text is None:
            self.submenu.add_separator()
            return

        if func is None:
            msg = f"El menú {text} no té cap funció associada."
            raise ValueError(msg)

        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}

        command = partial(func, *args, **kwargs)

        if file_check:
            command = partial(self._executa_amb_fitxer, command)
        if shortcut:
            self.root.bind(f"<{shortcut}>", lambda _: command())

        self.submenu.add_command(label=text, command=command, accelerator=shortcut)

    def _executa_amb_fitxer(self, command: Callable[[], object]) -> object | None:
        if self.get_file() is None:
            messagebox.showinfo("Informació", "No hi ha cap fitxer obert.")
            return None

        return command()

    def open_window[W: BaseWindow](self, window_type: type[W]) -> W:
        """Obri una finestra o recupera la instància existent.

        Parameters
        ----------
        window_type: type[W]
            Classe de la finestra que es vol obrir

        Returns
        -------
        window: W
            Instància de la finestra oberta

        """
        existing = self._windows.get(window_type)

        if existing is not None:
            try:
                if existing.window.winfo_exists():
                    existing.window.deiconify()
                    existing.window.lift()
                    existing.window.focus_force()

                    return cast("W", existing)
            except TclError:
                pass

            self._windows.pop(window_type, None)

        constructor = cast("Callable[[GestorProtocol], W]", window_type)
        instance = constructor(self)

        self._windows[window_type] = instance

        def forget(event: Event) -> None:
            if (event.widget is instance.window and self._windows.get(window_type) is instance):
                self._windows.pop(window_type, None)

        instance.window.bind("<Destroy>", forget, add="+")

        return instance
