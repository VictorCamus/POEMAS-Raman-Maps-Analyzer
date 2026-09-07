import threading
from tkinter import Menu, messagebox
from matplotlib.pyplot import close

from window.widgets import Progress
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
        
    def __init__(self, app):
        self.files = app.files
        self.root = app.root
        self.notebook = app.notebook
        self.label_inici = app.label_inici

        self.get_file = app.get_file
        self.set_file = app.set_file

    @property
    def current_file(self):
        return self.get_file()
    
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
                self.root.bind(tecla, lambda event, f=func: f())

            submenu.add_command(label=text, command=func, accelerator=accelerator_text)

        menu.add_cascade(label=etiqueta, menu=submenu)

    def save_file(self, func, tots=False):
        if not self.comprova_fitxer():
            return

        if tots:
            files = list(self.files.values())
        else:
            files = [self.current_file]

        progress = Progress(self.root, title="Guardant arxius", maximum=len(files))
        threading.Thread(target=self._save_thread, args=(func, files, progress), daemon=True).start()

    def _save_thread(self, func, files, progress):
        fig, ax = base_plot('', '', dim=(5, 3))

        for i, f in enumerate(files, start=1):
            if not func(f): break

            progress.update(i, text=f"Guardant: {f.name}")

        progress.finish()

        self.root.after(0, self.current_file.view.map.refresh_map)
        close(fig)