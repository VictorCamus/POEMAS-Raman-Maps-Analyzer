import sys
from tkinter import Tk, ttk, Menu, TclError

from menubuild import BuildMenu
from drawing.colormap import load_colormaps

def eixir():
    sys.exit()

class Aplicacio: # Classe principal de l'aplicació que gestiona la interfície gràfica.
    def __init__(self, root):
        self.root = root
        self.current_file = None
        self.files = dict()

        self._active_timer_id = None
        self._restants_timer_id = None
        self.drag_tab = None

        self.notebook = ttk.Notebook(self.root) # Crea un notebook per a les pestanyes.
        self.notebook.pack(fill='both', expand=True)

        self._init_message()
        self._init_menu()
        self._init_style()
        self._init_binds()

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

    def _init_binds(self):
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
        """Executa el resize només del canal/pestanya activa."""
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
            self.drag_tab = self.notebook.index(f"@{event.x},{event.y}")
        except TclError:
            self.drag_tab = None

    def _on_drag(self, event):
        if self.drag_tab is None: return

        try:
            target = self.notebook.index(f"@{event.x},{event.y}")
        except TclError:
            return

        if target == self.drag_tab: return

        # Mou la pestanya
        self.notebook.insert(target, self.drag_tab)

        # Reordena el diccionari de fitxers
        keys = list(self.files.keys())
        name = keys.pop(self.drag_tab)
        keys.insert(target, name)

        old_files = dict(self.files)
        self.files.clear()

        for k in keys:
            self.files[k] = old_files[k]

        # Actualitza l'índex que s'està arrossegant
        self.drag_tab = target

    def _on_release(self, event):
        self.drag_tab = None

def main():
    load_colormaps() # Carrega tots els mapes de colors possibles. Ho fem abans perquè així només es carrega una vegada.
    root = Tk()
    Aplicacio(root)
    root.geometry("1200x900")  # Mida més gran

    root.protocol("WM_DELETE_WINDOW", eixir)
    root.mainloop()

if __name__ == "__main__":
    main()