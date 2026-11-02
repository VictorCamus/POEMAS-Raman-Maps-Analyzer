"""Fitxer llavor d'execució del programa."""

import sys
from tkinter import Menu, Tk, ttk
from typing import TYPE_CHECKING, cast

from classes.interactions import AppInteraction
from drawing.colormap import load_colormaps
from menubuild.register import BuildMenu

if TYPE_CHECKING:
    from classes.protocols import NotebookProtocol
    from classes.views import FileView


def eixir() -> None:
    """Drecera per a tancar el programa."""
    sys.exit()


class Aplicacio:
    """Classe principal de l'aplicació que gestiona la interfície gràfica."""

    def __init__(self, root: Tk) -> None:
        """S'inicialitza la funció base."""
        self.root: Tk = root
        self.root.title("POEMAS - Interfície Gràfica")

        self.notebook: NotebookProtocol = cast("NotebookProtocol", ttk.Notebook(self.root))
        self.notebook.pack(fill="both", expand=True)

        self._current_file: FileView | None = None
        self.files: dict[str, FileView] = {}

        self._init_message()
        self._init_menu()
        self._init_style()

        self.binds = AppInteraction(self)

    def get_file(self) -> FileView | None:
        """Torna el fitxer actual obert en la interfície gràfica.

        Returns
        -------
        file
            Fitxer actual si existeix, si no None.

        """
        return self._current_file

    def set_file(self, file: FileView | None) -> None:
        """Configura el nou fitxer actual en la interfície gràfica."""
        self._current_file = file

    def _init_message(self) -> None:  # Mostra un missatge inicial quan s'obre l'aplicació.
        self.init_message: ttk.Label = ttk.Label(
            self.root,
            text="Carrega un fitxer per a començar.",
            font=("Arial", 24),
            anchor="center",
            justify="center",
        )
        self.init_message.place(relx=0.5, rely=0.5, anchor="center")

    def _init_menu(self) -> None:
        self.menu: Menu = Menu(self.root, bg="#121212", fg="white")
        self.gestors: BuildMenu = BuildMenu(self)

    @staticmethod
    def _init_style() -> None:  # Configura l'estil de la interfície gràfica.
        style: ttk.Style = ttk.Style()
        style.theme_use("clam")  # Tema visual de l'aplicació
        bg: str = "#121212"
        fg: str = "#eeeeee"
        pad: list[int] = [10, 5]

        style.configure("TNotebook.Tab", font=("Helvetica", 14, "bold"), padding=pad, background=bg, foreground=fg)
        style.map("TNotebook.Tab", background=[("selected", "#2811DA")])
        style.configure("TFrame", background=bg, foreground=fg)
        style.configure("TLabelFrame", background=bg, foreground=fg)
        style.configure("TLabel", background=bg, foreground="white", font=("Helvetica", 10, "bold"))
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TMenu", font=("Helvetica", 12), background=bg, foreground=fg)
        style.configure("Green.Horizontal.TProgressbar", troughcolor="#e0e0e0", background="#2ecc71", thickness=18)

        style.configure("Custom.TEntry", font=("Helvetica", 10))
        style.configure("Custom.TButton", font=("Helvetica", 10, "bold"), background="#3a7ff6", foreground=fg,
                        selected="#3a7ff6")
        style.map("Custom.TButton", background=[("active", "#2456a6"), ("pressed", "#2456a6")],
                  foreground=[("active", fg), ("pressed", fg)])
        style.configure("Custom.TCheckbutton", font=("Helvetica", 10), background=bg, foreground=fg,
            selectcolor=bg, activebackground=bg, activeforeground=fg, anchor="w")
        style.map("Custom.TCheckbutton", background=[("active", bg)], foreground=[("active", fg)],
                indicatorcolor=[("active", bg), ("selected", bg)])

        style.configure("Custom.TCombobox", font=("Helvetica", 10))
        style.configure("Custom.TRadiobutton", font=("Helvetica", 10, "bold"), background=bg, foreground=fg,
            selectcolor=bg, activebackground=bg, activeforeground=fg, anchor="w")
        style.map("Custom.TRadiobutton", background=[("active", bg)],
            foreground=[("active", fg)], indicatorcolor=[("active", bg), ("selected", bg)])


def main() -> None:
    """Es crea la interfície gràfica amb les característiques predeterminades del programa."""
    load_colormaps()
    root = Tk()
    Aplicacio(root)
    root.geometry("1200x900")

    root.protocol("WM_DELETE_WINDOW", eixir)
    root.mainloop()


if __name__ == "__main__":
    main()
