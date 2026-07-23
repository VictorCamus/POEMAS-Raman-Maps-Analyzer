import threading
from tkinter import Menu, messagebox, Toplevel, Label
from tkinter.ttk import Frame, Notebook, Progressbar
from matplotlib.pyplot import close

from window.labels import tab, build_grid
from drawing.plots import base_plot

class Condicions: # Mixin per a comprovar condicions abans d'executar accions.
    def comprova_fitxer(self): # Comprova si hi ha pestanyes obertes al notebook.
        if not self.current_file:
            messagebox.showinfo("Informació", "No hi ha cap fitxer obert.")
            return False
        return True

    def mascara_comprova(self, file): # Comprova si hi ha una màscara activa.
        if hasattr(file, 'mask'):
            messagebox.showinfo("Informació", "Lleva la màscara abans de continuar.")
            return False
        return True

    def fletxes_comprova(self, file): # Comprova si hi ha fletxes dibuixades a les pestanyes.
        if hasattr(file,'fletxa'):
            messagebox.showinfo("Informació", "No es poden guardar fitxers amb fletxes dibuixades.")
            return False
        return True

    def grain_comprova(self, file): # Comprova si hi ha una pestanya GRAIN oberta.
        if 'GRAIN' not in file.channel:
            messagebox.showinfo("Informació", "No hi ha cap arxiu GRAIN associat.")
            return False
        return True

    def condicions_guardar(self, file): # Comprova si es compleixen les condicions per a guardar un fitxer.
        return (
            self.mascara_comprova(file) and
            self.fletxes_comprova(file)
        )

REGISTRE_GESTORS = []
    
class BaseMenu(Condicions):  # Classe base per a gestionar les accions comunes de l'aplicació.
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        REGISTRE_GESTORS.append(cls)
        
    def __init__(self, app, get_current, set_current):
        self.files = app.files
        self.root = app.root
        self.notebook = app.notebook
        self.label_inici = app.label_inici

        self._get_current = get_current
        self._set_current = set_current

    @property
    def current_file(self):
        return self._get_current()

    @current_file.setter
    def current_file(self, value):
        self._set_current(value)

    def element_obert(self):
        file = self.current_file
        channel = file.current_channel if file else None
        return file, channel
    
    def create_window(self, title: str, gridBuilder: list[tuple] = None, tabConfig: list[tuple] = None, **extra):
        window = Toplevel(self.root)
        window.title(title)
        notebook = Notebook(window)                                          
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        if tabConfig:
            widgets = {}
            for tabElement in tabConfig:
                nom = tabElement[0]
                grid = gridBuilder(*tabElement)
                widgets[nom] = tab(notebook, grid, nom, **extra)  # Crea la pestanya amb la graella

            return widgets, notebook
        else:
            return build_grid(notebook, gridBuilder(), **extra), notebook
    
    def create_menu(self, etiqueta, menu, accions):
        submenu = Menu(menu, tearoff=0, font=('Helvetica', 12, 'bold'), bg='#2b2b2b', fg='#eeeeee', activebackground='#3a7ff6', activeforeground='#ffffff')

        for accio in accions:
            if accio == "SEPARATOR":
                submenu.add_separator()
                continue

            text, func = accio[0], accio[1]
            tecla = accio[2] if len(accio) == 3 else None

            accelerator_text = None
            if tecla:
                accelerator_text = tecla.replace("<", "").replace(">", "")

            submenu.add_command(
                label=text,
                command=func,
                accelerator=accelerator_text
            )

            if tecla:
                self.root.bind(tecla, lambda event, f=func: f())

        menu.add_cascade(label=etiqueta, menu=submenu)

    def save_file(self, func, tots=False):
        if not self.comprova_fitxer(): return

        win = Toplevel(self.root)
        win.title("Guardant arxius")
        win.geometry("400x120")

        label = Label(win, text="Preparant...", font=("Arial", 12))
        label.pack(pady=10)

        frame_barra = Frame(win)
        frame_barra.pack(fill="x", padx=20, pady=10)

        progress = Progressbar(
            frame_barra,
            style="Green.Horizontal.TProgressbar",
            mode="determinate"
        )
        
        progress.pack(side="left", fill="x", expand=True)

        percent_label = Label(frame_barra, text="0 %", width=5)
        percent_label.pack(side="right", padx=(10,0))

        if tots: files = list(self.files.values())
        else: files = [self.current_file]

        progress["maximum"] = len(files)

        threading.Thread(target=lambda: self._save_thread(func, files, win, label, percent_label, progress), daemon=True).start()
        
    def _save_thread(self, func, files, win, label, percent_label, progress):
        fig, ax = base_plot('', '', dim=(5,3))

        for i, f in enumerate(files, start=1):
            self.root.after(0, lambda f=f: label.config(text=f"Guardant: {f.name}"))
            result = func(f, fig, ax)
            if not result:
                break

            percent = int((i / progress["maximum"]) * 100)

            self.root.after(0, lambda i=i, percent=percent: (
                progress.config(value=i),
                percent_label.config(text=f"{percent} %")
            ))

        label.config(text="Finalitzat ✔")
        win.after(500, win.destroy)
        self.current_file.redraw()
        close(fig)