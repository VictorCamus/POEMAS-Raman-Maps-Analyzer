from tkinter.ttk import Label, Combobox, Frame
from tkinter import Entry, Label, Scale, messagebox, StringVar, DoubleVar, BooleanVar, Variable, Toplevel, Button, Radiobutton
from matplotlib import colors as mcolors

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

class Default:
    def colors(): 
        return ['black', 'blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'white',
                'orange', 'purple', 'lime', 'turquoise', 'navy']

    def fonts():
        return ['DejaVu Sans',  # font per defecte de Matplotlib
        'Arial', 'Calibri', 'Cambria', 'Courier New', 'Times New Roman', 'Verdana', 'Tahoma', 'Trebuchet MS', 'Georgia', 'Comic Sans MS'
    ]

    def scale():
        return {'Normal': 'linear', 'Logarítmica': 'log', 'SymLog': 'symlog', 'LogIt': 'logit'}

    def format():
        return {'Normal': 'normal', 'Negreta': 'bold'}
    
    def text_style():
        return {'Normal': 'normal', 'Cursiva': 'italic'}

    def line_style():
        return {'': 'None', '-': '-', '--': '--', '-.': '-.', '.': ':'}
    
    def marker_style():
        return {
            'Cap': 'None', 'Cercle': 'o', 'Quadrat': 's', 'Diamant': 'D', 'Creu': 'x', 
            'Creu petita': '+', 'Estrella': '*', 'Triangle amunt': '^', 'Triangle avall': 'v', 
            'Triangle esquerra': '<', 'Triangle dreta': '>', 'Punt': '.', 'Pixel': ','
        }
        
def rgba_to_name(rgba):
    for name, hexcode in mcolors.CSS4_COLORS.items():
        if mcolors.to_rgba(hexcode)[:3] == rgba[:3]:  # ignorar alpha
            return name
    return mcolors.to_hex(rgba)  # si no troba, retorna hex

def create_widget(type_widget, frame, text_label = None, row=0, col=0, key = None, set_value = None, callback = None, **kwargs): # Afegeix un label davant d'un objecte (entry, combobox...)
    WIDGET_MAP = {'cb': add_combobox, 'entry': add_entry, 'scale': add_scale, 'button': add_button, 'radiobutton': add_radiobuttons, 'colorcb': add_colorcombobox}
    
    def func(event=None):
        try:
            if callback: callback(widget.value.get(), key)
        except Exception as e:
            messagebox.showerror("Error en l'actualització", e)

    widget = WIDGET_MAP[type_widget](func, frame, set_value=set_value, **kwargs)
    widget._widget_type = type_widget
    
    widget.grid(row=row, column=col+1, padx=5, pady=2, sticky='nw')
    widget.value = set_value
    widget.callback = callback
    
    if text_label:
        label = Label(frame, text=text_label, font= ('Helvetica', 9, 'bold'), bg = '#2b2b2b', fg = 'white')
        label.grid(row=row, column=col, padx=5, pady=2, sticky='nw')
        widget._label = label  # afegim el label com a atribut del widget

    return widget

def add_entry(func, frame, set_value=None, state = 'normal'):
    entry = Entry(frame, textvariable=set_value, state=state, font=('Helvetica', 9))
    entry.bind('<Return>', func)
    return entry

def add_button(func, frame, set_value=None):
    return Button(frame, textvariable=set_value, command=func, font=('Helvetica', 9, 'bold'), background = '#3a7ff6', fg = 'white')

def add_radiobuttons(func, frame, set_value=None, vertical=True, options=None):
    container = Frame(frame)
    if not isinstance(options, dict):
        options = dict(zip(options, options))

    for i, (text, value) in enumerate(options.items()):
        fila = i if vertical else 0
        columna = 0 if vertical else i

        rb = Radiobutton(container, text=text, variable=set_value, value=value, command=func, bg='#2b2b2b',
            fg='white', selectcolor='#444444', activebackground='#2b2b2b', activeforeground='white', anchor='w')
        rb.grid(row=fila, column=columna, sticky='w')

    container.options = options

    return container

def add_scale(func, frame, set_value=0.5, from_=0.0, to=1.0, resolution=0.01):
    return Scale(frame, from_=from_, to=to, resolution=resolution, orient="horizontal", variable=set_value, length=150, command=func)

def add_combobox(func, frame, set_value=None, options=None):
    def internal_callback(event=None):
        set_value.set(combo.options[display_var.get()])
        func(event)
    
    if not isinstance(options, dict): options = dict(zip(options, options))

    labels = list(options.keys())
    initial_key = next((k for k, v in options.items() if v == set_value.get()), labels[0])

    display_var = StringVar(frame, value=initial_key)
    combo = Combobox(frame, values=labels, state="readonly", textvariable=display_var, font=('Helvetica', 9))
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
        set_value = mcolors.to_hex(set_value.get())
    except Exception:
        set_value = colors[0]

    main_btn = Button(frame, bg=set_value, width=4, relief="raised", command = open_palette)
    main_btn.value = set_value
    
    return main_btn

def update(func: callable, value, name: str, mode: str, figure: object, **extra):
    try:
        match mode:
            case "args": func(value, **extra)
            case "kwargs": func(**{name: value}, **extra)
            case "attr": setattr(func, name, value)
            
    except Exception as e:
        messagebox.showerror("Error en l'actualització", e)
        return

    if figure: figure.canvas.draw()

TYPE_MAP = {float: DoubleVar, bool: BooleanVar, str: StringVar, object: ObjectVar}
     
def build_grid(frame, grid, row: int = 0, col: int = 0, figure: object = None, button: object = True):
    from functools import partial

    def apply_all():
        for key, widget in widgets.items():
            widget.callback(widget.value.get(), key)

    widgets = {}

    for i, item in enumerate(grid):
        var, obj, setter = item
        
        key, type_var, init_value = var if len(var) == 3 else (var[0], var[1], None)
        obj_label, obj_widget, obj_extra = obj if len(obj) == 3 else (obj[0], obj[1], {})
        setter_func, setter_type, setter_kwargs = setter if len(setter) == 3 else (setter[0], setter[1], {})
        
        set_value = TYPE_MAP[type_var](frame, value=init_value)
        callback = partial(update, setter_func, mode = setter_type, figure=figure, **setter_kwargs)
        
        widgets[key] = create_widget(
            obj_widget, frame, text_label=obj_label, row=i+row, col=col,
            key=key, callback=callback, set_value=set_value, **obj_extra)
    
    if button:
        Button(frame, text="Aplicar", command=apply_all, font=('Helvetica', 9, 'bold'), background = '#3a7ff6', fg = 'white').grid(
            row=len(grid)+row, column=col, columnspan=2,
            padx=5, pady=5, sticky="w")

    return widgets

def tab(notebook, grid, name, **kwargs):
    tab_frame = Frame(notebook)
    notebook.add(tab_frame, text=name)
    widgets = build_grid(tab_frame, grid, **kwargs)
    return widgets

def destroy_widgets(widgets_dict): # Destrueix tots els widgets i els seus labels associats.
    for w in widgets_dict.values():
        try:
            w.destroy()
            if hasattr(w, "_label"): w._label.destroy()
        except Exception:
            pass

    widgets_dict.clear()