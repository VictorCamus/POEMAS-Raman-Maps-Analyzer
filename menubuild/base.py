import threading
from tkinter import Menu, messagebox
from matplotlib.pyplot import close
from functools import partial

from window.widgets import Progress
from drawing.plots import base_plot

REGISTRE_GESTORS = []
    
class BaseMenu:  # Classe base per a gestionar les accions comunes de l'aplicació.
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

        self.submenu = Menu(app.menu, tearoff=0, font=('Helvetica', 12, 'bold'), bg='#2b2b2b', fg='#eeeeee', activebackground='#3a7ff6', activeforeground='#ffffff')

    @property
    def current_file(self):
        return self.get_file()
    
    def add_tab(self, text = None, func = None, shortcut = None, file_check = True, args = None, kwargs = None):
        if not text:
            self.submenu.add_separator()
            return
        
        if func is None:
            raise ValueError(f"El menú '{text}' no té cap funció associada.")

        if args is None: args = ()
        if kwargs is None: kwargs = {}
        
        command = partial(func, *args, **kwargs)

        if file_check: command = partial(self._executa_amb_fitxer, command)
        if shortcut: self.root.bind(f'<{shortcut}>', lambda event, f=command: f())

        self.submenu.add_command(label=text, command=command, accelerator=shortcut)

    def _executa_amb_fitxer(self, command):
        if self.comprova_fitxer():
            return command()

    def comprova_fitxer(self): # Comprova si hi ha pestanyes obertes al notebook.
        if not self.current_file:
            messagebox.showinfo("Informació", "No hi ha cap fitxer obert.")
            return False
        
        return True