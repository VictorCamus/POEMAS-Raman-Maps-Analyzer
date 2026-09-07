from tkinter.ttk import Label, Combobox, Frame, Progressbar
from tkinter import Entry, Label, Scale, messagebox, StringVar, DoubleVar, IntVar, BooleanVar, Variable, Toplevel, Button, Radiobutton, Checkbutton
from matplotlib import colors as mcolors
from functools import partial
from typing import Callable, Any, Literal
import threading

class ObjectVar(Variable):
    _default = None

    def __init__(self, master=None, value=None, name=None):
        Variable.__init__(self, master, name)
        self._value = value

    def set(self, value):
        self._value = value
        self._tk.globalsetvar(self._name, value)  # per compatibilitat interna

    def get(self):
        return self._value

TYPE_MAP = {float: DoubleVar, int: IntVar, bool: BooleanVar, str: StringVar, object: ObjectVar}

class Widget:
    def __init__(self, key: str, var_type: type, init: Any = None,
                 text: str = '', widget: str = 'entry', widget_kwargs: dict | None = None,
                 setter: Callable | None = None, mode: str = "args", setter_kwargs: dict | None = None,
                 canvas = None):

        self.key = key
        self.var_type = var_type
        self.init = init

        self.text = text
        self.widget_type = widget
        self.widget_kwargs = {} if widget_kwargs is None else widget_kwargs

        if setter is not None:
            self.callback = partial(self._update, setter, mode = mode, canvas = canvas,
                                    **setter_kwargs if setter_kwargs is not None else {})
        else: self.callback = None

    def add(self, frame, row = 0, col = 0):
        self.value = TYPE_MAP[self.var_type](frame, value=self.init)
        self.widget = WIDGET_MAP[self.widget_type](self._func, frame, set_value=self.value, **self.widget_kwargs)

        if self.text:
            label = Label(frame, text=self.text, font=('Helvetica', 9, 'bold'), bg='#2b2b2b', fg='white')
            label.grid(row=row, column=col, padx=5, pady=2, sticky='nw')
            self.label = label  # afegim el label com a atribut del widget
            col = col + 1

        self.widget.grid(row=row, column=col, padx=5, pady=2, sticky='nw')

    def set(self, value):
        self.value.set(value)

        if self.widget_type == 'cb':
            key = next(key for key, val in self.widget.options.items() if val == value)
            self.widget.set(key)

    def get(self):
        return self.value.get()

    def config(self, *args, **kwargs):
        return self.widget.config(*args, **kwargs)

    def _func(self, event = None):
            if self.callback:
                self.callback(self.get(), self.key)

    @staticmethod
    def _update(func: callable, value, name: str, mode: str, canvas = None, **extra):
        try:
            match mode:
                case "args": func(value, **extra)
                case "kwargs": func(**{name: value}, **extra)
                case "attr": setattr(func, name, value)
                case "dict": func[name] = value
                case _: raise ValueError(f"Mode d'actualització desconegut: {mode!r}")

        except Exception as e:
            messagebox.showerror("Error en l'actualització", str(e))
            return

        if canvas: canvas.draw_idle()

class Default:
    @staticmethod
    def colors(): 
        return ['black', 'blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'white',
                'orange', 'purple', 'lime', 'turquoise', 'navy']

    @staticmethod
    def fonts():
        return ['DejaVu Sans',  # font per defecte de Matplotlib
        'Arial', 'Calibri', 'Cambria', 'Courier New', 'Times New Roman', 'Verdana', 'Tahoma', 'Trebuchet MS', 'Georgia', 'Comic Sans MS'
    ]

    @staticmethod
    def scale():
        return {'Normal': 'linear', 'Logarítmica': 'log', 'SymLog': 'symlog', 'LogIt': 'logit'}

    @staticmethod
    def format():
        return {'Normal': 'normal', 'Negreta': 'bold'}

    @staticmethod
    def text_style():
        return {'Normal': 'normal', 'Cursiva': 'italic'}

    @staticmethod
    def line_style():
        return {'': 'None', '-': '-', '--': '--', '-.': '-.', '.': ':'}

    @staticmethod
    def marker_style():
        return {
            'Cap': 'None', 'Cercle': 'o', 'Quadrat': 's', 'Diamant': 'D', 'Creu': 'x', 
            'Creu petita': '+', 'Estrella': '*', 'Triangle amunt': '^', 'Triangle avall': 'v', 
            'Triangle esquerra': '<', 'Triangle dreta': '>', 'Punt': '.', 'Pixel': ','
        }

def add_entry(func, frame, set_value=None, width = 18, **kwargs):
    entry = Entry(frame, textvariable=set_value, font=('Helvetica', 9), width = width, **kwargs)
    entry.bind('<Return>', func)
    return entry

def add_button(func, frame, set_value=None):
    return Button(frame, textvariable=set_value, command=func, font=('Helvetica', 9, 'bold'), background = '#3a7ff6', fg = 'white')

def add_checkbutton(func, frame, set_value=None, text="", **kwargs):
    return Checkbutton(frame, text=text, variable=set_value, command=func,
        bg='#2b2b2b', fg='white', selectcolor='#444444', activebackground='#2b2b2b',
        activeforeground='white', anchor='w', **kwargs)

def add_radiobuttons(func, frame, set_value=None, direction = 'v', options=None):
    container = Frame(frame)
    if not isinstance(options, dict):
        options = dict(zip(options, options))

    for i, (text, value) in enumerate(options.items()):
        match direction:
            case 'v': row, column = i, 0
            case 'h': row, column = 0, i
            case _: raise ValueError(f"Error en la direcció: {direction}")

        rb = Radiobutton(container, text=text, variable=set_value, value=value, command=func, bg='#2b2b2b',
            fg='white', selectcolor='#444444', activebackground='#2b2b2b', activeforeground='white', anchor='w')
        rb.grid(row=row, column=column, sticky='w')

    container.options = options

    return container

def add_scale(func, frame, set_value= None, orient: Literal["horizontal", "vertical"] = "horizontal", **kwargs):
    return Scale(frame, command=func, variable=set_value, orient = orient, **kwargs)

def add_combobox(func, frame, set_value=None, options=None, width = 18):
    def internal_callback(event=None):
        set_value.set(combo.options[display_var.get()])
        func(event)

    if not isinstance(options, dict): options = dict(zip(options, options))

    labels = list(options.keys())

    if labels: initial_key = next((k for k, v in options.items() if v == set_value.get()), labels[0])
    else: initial_key = ''

    display_var = StringVar(frame, value=initial_key)
    combo = Combobox(frame, values=labels, state="readonly", textvariable=display_var, font=('Helvetica', 9), width = width)

    combo.options = options
    combo.bind("<<ComboboxSelected>>", internal_callback)

    return combo

def add_colorcombobox(func, frame, set_value=None, colors=None, cols=8):
    if colors is None: colors = Default.colors()

    def open_palette():
        popup = Toplevel(frame)
        popup.wm_overrideredirect(True)  # sense decoració finestra

        x = main_btn.winfo_rootx()
        y = main_btn.winfo_rooty() + main_btn.winfo_height()
        popup.geometry(f"+{x}+{y}")

        def select_color(color):
            main_btn.value.set(color)
            main_btn.config(bg=color)
            popup.destroy()

            func(color)

        # Graella de colors
        for i, c in enumerate(colors):
            r = i // cols
            col = i % cols

            btn = Button(popup, bg=c, width=2, height=1, command=lambda col=c: select_color(col))
            btn.grid(row=r, column=col, padx=1, pady=1)

        # Tancar si perds focus
        popup.bind("<FocusOut>", lambda e: popup.destroy())
        popup.focus_set()

    try:
        value = mcolors.to_hex(set_value.get())
    except Exception:
        value = colors[0]

    main_btn = Button(frame, bg=value, width=4, relief="raised", command = open_palette)
    main_btn.value = set_value

    return main_btn

WIDGET_MAP = {'cb': add_combobox,
              'entry': add_entry,
              'scale': add_scale,
              'button': add_button,
              'radiobutton': add_radiobuttons,
              'checkbutton': add_checkbutton,
              'colorcb': add_colorcombobox}

def create_tab(notebook, name):
    tab = Frame(notebook)
    notebook.add(tab, text=name)
    return tab

class Progress:
    def __init__(self, root, title="Processant", maximum=100):
        self.root = root
        self.value = 0
        self.maximum = maximum

        self.cancel_event = threading.Event()

        self.win = Toplevel(root)
        self.win.title(title)
        self.win.resizable(False, False)
        self.win.transient(self.root)
        self.win.lift()
        self.win.geometry("400x120")

        self.label = Label(self.win, text="Preparant...", font=("Arial", 12))
        self.label.pack(pady=10)

        frame_barra = Frame(self.win)
        frame_barra.pack(fill="x", padx=20, pady=10)

        self.bar = Progressbar(frame_barra, style="Green.Horizontal.TProgressbar", mode="determinate")
        self.bar.pack(side="left", fill="x", expand=True)

        self.percent_label = Label(frame_barra, text="0 %", width=5)
        self.percent_label.pack(side="right", padx=(10, 0))

        self.cancel_button = Button(self.win, text="Cancel·lar", command=self.cancel)
        self.cancel_button.pack(anchor = "e", padx = 20, pady = 5)

        self.bar["maximum"] = maximum

        self.win.protocol("WM_DELETE_WINDOW", self.cancel)

    def update(self, value=None, text=None):
        if value is not None:
            self.value = value

        percent = int((self.value / self.maximum) * 100)

        def _update():
            self.bar["value"] = self.value
            self.percent_label.config(text=f"{percent} %")

            if text is not None:
                self.label.config(text=text)

        self.root.after(0, _update)

    def increment(self, text=None):
        self.value += 1
        self.update(text=text)

    def cancel(self):
        self.cancel_event.set()

        self.label.config(text="Cancel·lant...")
        self.cancel_button.config(state="disabled")

    def cancelled(self):
        return self.cancel_event.is_set()

    def finish(self, text="Finalitzat ✔"):
        def _finish():
            if not self.win.winfo_exists(): return

            self.label.config(text=text)
            self.cancel_button.config(state="disabled")
            self.win.after(500, self.win.destroy)

        self.root.after(0, _finish)