"""Colores, fuentes y piezas reutilizables (botones, formularios, tablas, tarjetas)."""

import tkinter as tk
from tkinter import ttk

# Colores tomados de los prototipos aprobados
C = {
    "azul": "#0b3f5f",        # barra superior y menú lateral (panel del bibliotecario)
    "azul_osc": "#082f47",
    "menu_sel": "#1e2d36",
    "acento": "#1fb3a9",
    "rojo": "#d9262c",        # botón Login
    "borde_rojo": "#d9534f",  # borde de los campos del login
    "cian": "#00c0ef",
    "verde": "#00a65a",
    "naranja": "#f39c12",
    "rojo_t": "#dd4b39",
    "morado": "#7a3fb2",      # banner de la página del lector
    "morado_cl": "#efe7f8",
    "verde_btn": "#5a9e2f",
    "fondo": "#f4f6f9",
    "blanco": "#ffffff",
    "texto": "#2b3640",
    "gris": "#7c8791",
    "linea": "#d8dee4",
    "caja": "#dddddd",
}
PORTADAS = ["#e0524b", "#2c3e50", "#e8a920", "#7a3fb2", "#2a9d8f", "#3d7be0"]
FAMILIA = "Segoe UI"


def fuente(tam=10, negrita=False, subrayada=False):
    estilo = ("bold " if negrita else "") + ("underline" if subrayada else "")
    return (FAMILIA, tam, estilo.strip() or "normal")


def oscurecer(color, factor=0.85):
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * factor), int(g * factor), int(b * factor))


def iniciar_estilos(raiz):
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    estilo.configure("Treeview", font=fuente(10), rowheight=27, background=C["blanco"],
                     fieldbackground=C["blanco"], foreground=C["texto"], borderwidth=0)
    estilo.configure("Treeview.Heading", font=fuente(10, True), background=C["azul"],
                     foreground="white", relief="flat", padding=(6, 5))
    estilo.map("Treeview.Heading", background=[("active", C["azul_osc"])])
    estilo.map("Treeview", background=[("selected", C["acento"])],
               foreground=[("selected", "white")])
    estilo.configure("TCombobox", padding=4, font=fuente(10))
    estilo.map("TCombobox", fieldbackground=[("readonly", "white")],
               background=[("readonly", "white")])
    estilo.configure("Vertical.TScrollbar", background=C["linea"], troughcolor=C["fondo"])
    raiz.option_add("*TCombobox*Listbox.font", fuente(10))


# ----------------------------------------------------------------------
# Piezas sueltas
# ----------------------------------------------------------------------
def boton(padre, texto, comando, color=None, **extra):
    color = color or C["rojo"]
    return tk.Button(padre, text=texto, command=comando, bg=color, fg="white",
                     activebackground=oscurecer(color), activeforeground="white",
                     relief="flat", bd=0, padx=16, pady=6, font=fuente(10), cursor="hand2",
                     **extra)


def enlace(padre, texto, comando, color=None, fondo=None, tam=10):
    e = tk.Label(padre, text=texto, font=fuente(tam, subrayada=True), cursor="hand2",
                 fg=color or C["texto"], bg=fondo or padre["bg"])
    e.bind("<Button-1>", lambda _e: comando())
    return e


def avatar(padre, letra, diametro=36, fondo="#e3e8ed", color="#8793a0", fondo_padre=None):
    c = tk.Canvas(padre, width=diametro, height=diametro, highlightthickness=0,
                  bg=fondo_padre or padre["bg"])
    c.create_oval(1, 1, diametro - 1, diametro - 1, fill=fondo, outline="")
    c.create_text(diametro / 2, diametro / 2, text=(letra or "?").upper(), fill=color,
                  font=fuente(max(9, diametro // 3), True))
    return c


def tarjeta(padre, **extra):
    return tk.Frame(padre, bg=C["blanco"], highlightbackground=C["linea"],
                    highlightthickness=1, **extra)


class Tile(tk.Frame):
    """Cuadro de color del panel (número grande, título e icono a la derecha)."""

    def __init__(self, padre, titulo, color, icono, valor=None, comando=None):
        super().__init__(padre, bg=color, height=86, cursor="hand2" if comando else "")
        self.pack_propagate(False)
        self.grid_propagate(False)
        piezas = []
        y = 12
        if valor is not None:
            v = tk.Label(self, text=str(valor), font=fuente(20, True), fg="white", bg=color)
            v.place(x=14, y=6)
            piezas.append(v)
            y = 46
        else:
            y = 28
        t = tk.Label(self, text=titulo, font=fuente(13 if valor is None else 12),
                     fg="white", bg=color, justify="left")
        t.place(x=14, y=y)
        i = tk.Label(self, text=icono, font=fuente(22), fg="#ffffff", bg=color)
        i.place(relx=1.0, x=-14, y=12, anchor="ne")
        piezas += [t, i]
        if comando:
            for w in (self, *piezas):
                w.bind("<Button-1>", lambda _e: comando())
                w.bind("<Enter>", lambda _e: self._pintar(oscurecer(color, 0.92), piezas))
                w.bind("<Leave>", lambda _e: self._pintar(color, piezas))

    def _pintar(self, color, piezas):
        self.config(bg=color)
        for p in piezas:
            p.config(bg=color)


class Formulario(tk.Frame):
    """Rejilla de campos. campos = [(clave, etiqueta, 'texto' | 'combo', valores)]."""

    def __init__(self, padre, campos, columnas=2, fondo=None):
        super().__init__(padre, bg=fondo or padre["bg"])
        self.fondo = self["bg"]
        self.vars, self.widgets = {}, {}
        for n, (clave, etiqueta, tipo, valores) in enumerate(campos):
            fila, col = divmod(n, columnas)
            marco = tk.Frame(self, bg=self.fondo)
            marco.grid(row=fila, column=col, sticky="ew", padx=(0, 14), pady=4)
            tk.Label(marco, text=etiqueta, font=fuente(9), fg=C["gris"],
                     bg=self.fondo).pack(anchor="w")
            var = tk.StringVar()
            if tipo == "combo":
                w = ttk.Combobox(marco, textvariable=var, values=valores or [], state="readonly")
                w.pack(fill="x", ipady=3)
            else:
                w = tk.Entry(marco, textvariable=var, font=fuente(10), relief="flat", bd=0,
                             bg="white", fg=C["texto"], highlightthickness=1,
                             highlightbackground=C["linea"], highlightcolor=C["acento"])
                w.pack(fill="x", ipady=5)
            self.vars[clave], self.widgets[clave] = var, w
        for c in range(columnas):
            self.columnconfigure(c, weight=1, uniform="campos")

    def valores(self):
        return {k: v.get().strip() for k, v in self.vars.items()}

    def poner(self, datos):
        for k, v in self.vars.items():
            valor = datos.get(k)
            v.set("" if valor is None else str(valor))

    def limpiar(self, **por_defecto):
        for k, v in self.vars.items():
            v.set(por_defecto.get(k, ""))

    def opciones(self, clave, valores):
        self.widgets[clave]["values"] = valores


class Tabla(tk.Frame):
    """Tabla con barra de desplazamiento. columnas = [(clave, título, ancho)]."""

    def __init__(self, padre, columnas, alto=10, al_elegir=None, al_doble_clic=None):
        super().__init__(padre, bg=C["blanco"], highlightbackground=C["linea"],
                         highlightthickness=1)
        self.claves = [c[0] for c in columnas]
        self.arbol = ttk.Treeview(self, columns=self.claves, show="headings", height=alto,
                                  selectmode="browse")
        for clave, titulo, ancho in columnas:
            self.arbol.heading(clave, text=titulo, anchor="w")
            self.arbol.column(clave, width=ancho, minwidth=50, anchor="w")
        barra = ttk.Scrollbar(self, orient="vertical", command=self.arbol.yview)
        self.arbol.configure(yscrollcommand=barra.set)
        self.arbol.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.arbol.tag_configure("par", background="#ffffff")
        self.arbol.tag_configure("impar", background="#f3f6f9")
        self.arbol.tag_configure("alerta", foreground=C["rojo_t"])
        if al_elegir:
            self.arbol.bind("<<TreeviewSelect>>", lambda _e: al_elegir())
        if al_doble_clic:
            self.arbol.bind("<Double-1>", lambda _e: al_doble_clic())

    def cargar(self, filas, id_col=None, alerta=None):
        """Llena la tabla. `alerta(fila)` devuelve True para pintar la fila en rojo."""
        self.arbol.delete(*self.arbol.get_children())
        for n, fila in enumerate(filas):
            f = dict(fila)
            etiquetas = ["par" if n % 2 == 0 else "impar"]
            if alerta and alerta(f):
                etiquetas.append("alerta")
            self.arbol.insert("", "end", iid=str(f[id_col]) if id_col else str(n),
                              values=["" if f.get(c) is None else f[c] for c in self.claves],
                              tags=tuple(etiquetas))

    def elegido(self):
        sel = self.arbol.selection()
        return sel[0] if sel else None

    def valores_elegido(self):
        sel = self.elegido()
        return dict(zip(self.claves, self.arbol.item(sel, "values"))) if sel else None


class PantallaBase(tk.Frame):
    """Marco común de las secciones: título, ruta de navegación y cuerpo."""

    def __init__(self, padre, app, titulo, subtitulo=""):
        super().__init__(padre, bg=C["blanco"])
        self.app = app
        cab = tk.Frame(self, bg=C["blanco"])
        cab.pack(fill="x", padx=24, pady=(14, 6))
        tk.Label(cab, text=titulo, font=fuente(11, True), fg=C["texto"],
                 bg=C["blanco"]).pack(side="left")
        tk.Label(cab, text=subtitulo, font=fuente(10), fg=C["gris"],
                 bg=C["blanco"]).pack(side="left", padx=(10, 0), pady=(2, 0))
        ruta = "⌂ Inicio" if titulo in ("Inicio", "Panel") else f"⌂ Inicio   {titulo}"
        tk.Label(cab, text=ruta, font=fuente(9), fg=C["gris"],
                 bg=C["blanco"]).pack(side="right")
        tk.Frame(self, bg=C["linea"], height=1).pack(fill="x", padx=24)
        self.cuerpo = tk.Frame(self, bg=C["blanco"])
        self.cuerpo.pack(fill="both", expand=True, padx=24, pady=12)

    @property
    def con(self):
        return self.app.con

    @property
    def sesion(self):
        return self.app.sesion
