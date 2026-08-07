import sys
from tkinter import Tk, ttk, Menu

from menubuild import BuildMenu
from drawing.colormap import load_colormaps
from classes.interactions import RootInteraction

def eixir():
    sys.exit()

class Aplicacio: # Classe principal de l'aplicació que gestiona la interfície gràfica.
    def __init__(self, root):
        self.root = root
        self.current_file = None
        self.files = dict()

        self.notebook = ttk.Notebook(self.root) # Crea un notebook per a les pestanyes.
        self.notebook.pack(fill='both', expand=True)

        self._init_message()
        self._init_menu()
        self._init_style()

        self.binds = RootInteraction(self)

        self.root.title("POEMAS - Interfície Gràfica")

    def _init_message(self): # Mostra un missatge inicial quan s'obre l'aplicació.
        self.label_inici = ttk.Label(
            self.root,
            text="Carrega un fitxer per a començar.",
            font=("Arial", 24),
            anchor='center',
            justify='center'
        )
        self.label_inici.place(relx=0.5, rely=0.5, anchor='center')

    def _init_menu(self):
        self.menu = Menu(self.root, bg="#121212", fg="white") # Crea un menú principal per a l'aplicació...
        self.gestors = BuildMenu(self)

    def _init_style(self): # Configura l'estil de la interfície gràfica.
        style = ttk.Style()
        style.theme_use('clam') # Tema visual de l'aplicació
        BG = "#121212"
        FG = "#eeeeee"
        ACCENT = "#3a7ff6"
        style.configure("TNotebook.Tab", font=('Helvetica', 14, 'bold'), padding=[10, 5], background="#121212", foreground="white"),
        style.map("TNotebook.Tab", background=[("selected", "#2811DA")])
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=('Helvetica', 16))
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TMenu", font=('Helvetica', 12), background=BG, foreground=FG)
        style.configure("Green.Horizontal.TProgressbar", troughcolor='#e0e0e0', background='#2ecc71', thickness=18) # Barra de progrés verda

def main():
    load_colormaps() # Carrega tots els mapes de colors possibles. Ho fem abans perquè així només es carrega una vegada.
    root = Tk()
    Aplicacio(root)
    root.geometry("1200x900")  # Mida més gran

    root.protocol("WM_DELETE_WINDOW", eixir)
    root.mainloop()

if __name__ == "__main__":
    main()