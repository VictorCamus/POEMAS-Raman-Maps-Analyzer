import sys
from tkinter import Tk, ttk, Menu

from menubuild import BuildMenu
from drawing.colormap import load_colormaps

def eixir():
    sys.exit()

class Aplicacio: # Classe principal de l'aplicació que gestiona la interfície gràfica.
    def __init__(self, root):
        self.root = root
        self.current_file = None
        self.files = {}

        self.notebook = ttk.Notebook(self.root) # Crea un notebook per a les pestanyes.
        self.notebook.pack(fill='both', expand=True)
        self._mostrar_missatge_inicial()
        
        self._active_timer_id = None
        self._restants_timer_id = None
        
        self.menu = Menu(root, bg="#121212", fg="white") # Crea un menú principal per a l'aplicació...
        self.gestors = BuildMenu(self)
        
        self.root.title("WSxM - Interfície Gràfica")

        self._activar_binds()
        self._configurar_estil()

    def _activar_binds(self):
        self.root.bind("<Configure>", self._trigger_resize)

        self.root.bind_all("<Up>", self._next_tab_global_next)
        self.root.bind_all("<Down>", self._next_tab_global_prev)
        self.root.bind_all("<Right>", self._next_tab_file_next)
        self.root.bind_all("<Left>", self._next_tab_file_prev)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_file_changed)
        
    def _configurar_estil(self): # Configura l'estil de la interfície gràfica.
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
        
    def _mostrar_missatge_inicial(self): # Mostra un missatge inicial quan s'obre l'aplicació.
        self.label_inici = ttk.Label(
            self.root,
            text="Carrega un fitxer per a començar.",
            font=("Arial", 24),
            anchor='center',
            justify='center'
        )
        self.label_inici.place(relx=0.5, rely=0.5, anchor='center')
        
    def _next_tab_global_next(self, event):
        return self._next_tab(True, notebook=self.notebook)

    def _next_tab_global_prev(self, event):
        return self._next_tab(False, notebook=self.notebook)

    def _next_tab_file_next(self, event):
        if not self.current_file:
            return "break"
        return self._next_tab(True, notebook=self.current_file.notebook)

    def _next_tab_file_prev(self, event):
        if not self.current_file:
            return "break"
        return self._next_tab(False, notebook=self.current_file.notebook)
    
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

        file = self.current_file

        # Cancel·lar el timer del resize ràpid del canal actiu
        if hasattr(self, "_active_timer_id") and self._active_timer_id:
            file.frame.after_cancel(self._active_timer_id)

        # Programar el resize del canal actiu després de 50 ms
        self._active_timer_id = file.frame.after(25, self._resize_activ)
        
        # Cancel·lar i programar el timer global del retard de 1 segon
        if hasattr(self, "_restants_timer_id") and self._restants_timer_id:
            self.root.after_cancel(self._restants_timer_id)
        
        self._restants_timer_id = self.root.after(1000, self._resize_restants)

    # -----------------------
    def _resize_activ(self):
        """Executa el resize només del canal/pestanya activa."""
        if not self.current_file: return
        
        self.current_file.zoom._resize()
        self._active_timer_id = None

    # -----------------------
    def _resize_restants(self):
        """Executa el resize de la resta dels fitxers després de 1 segon."""
        if not self.current_file: return

        for f in self.files.values():
            if f != self.current_file:
                f.zoom._resize()

        self._restants_timer_id = None
    
    def _on_file_changed(self, event):
        notebook = event.widget
        tab_id = notebook.select()
        if not self.current_file: return

        for f in self.files.values():
            if str(f.frame) == tab_id:
                self.current_file = f
                f.capçalera.set_channel(f.current_channel)
                break

def main():
    load_colormaps() # Carrega tots els mapes de colors possibles. Ho fem abans perquè així només es carrega una vegada.
    root = Tk()
    Aplicacio(root)
    root.geometry("1200x900")  # Mida més gran

    root.protocol("WM_DELETE_WINDOW", eixir)
    root.mainloop()

if __name__ == "__main__":
    main()