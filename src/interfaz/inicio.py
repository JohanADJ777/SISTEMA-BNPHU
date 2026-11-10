"""Página de inicio. El personal ve el panel de control (prototipo 2) y el lector
ve la página con buscador, populares y autores (prototipo 3); las dos comparten
las mismas consultas y el mismo buscador."""

import tkinter as tk

from src.interfaz import datos
from src.interfaz.estilos import (C, PORTADAS, PantallaBase, Tile, avatar, boton, enlace,
                                  fuente, tarjeta)


def _buscador(padre, app, ancho=None):
    """Barra de búsqueda: lleva al catálogo con el texto escrito."""
    marco = tk.Frame(padre, bg=C["morado_cl"], highlightthickness=0)
    texto = tk.StringVar()
    entrada = tk.Entry(marco, textvariable=texto, font=fuente(10), relief="flat", bd=0,
                       bg=C["morado_cl"], fg=C["texto"], insertbackground=C["texto"])
    entrada.pack(side="left", fill="x", expand=True, padx=(16, 4), ipady=8)
    ir = lambda *_: app.ir("catalogo", texto=texto.get().strip())
    lupa = tk.Label(marco, text="⌕", font=fuente(13), fg=C["verde_btn"], bg=C["morado_cl"],
                    cursor="hand2", padx=12)
    lupa.pack(side="right")
    lupa.bind("<Button-1>", ir)
    entrada.bind("<Return>", ir)
    entrada.insert(0, "Busca un título, autor o ISBN...")
    entrada.config(fg=C["gris"])

    def al_entrar(_e):
        if entrada.get().startswith("Busca un título"):
            entrada.delete(0, "end")
            entrada.config(fg=C["texto"])
    entrada.bind("<FocusIn>", al_entrar)
    return marco


def _lista(tarjeta_f, filas, vacio="Sin datos todavía."):
    if not filas:
        tk.Label(tarjeta_f, text=vacio, font=fuente(9), fg=C["gris"],
                 bg=C["blanco"]).pack(anchor="w", padx=14, pady=4)
    for texto, derecha in filas:
        f = tk.Frame(tarjeta_f, bg=C["blanco"])
        f.pack(fill="x", padx=14, pady=3)
        tk.Label(f, text=texto, font=fuente(9), fg=C["texto"], bg=C["blanco"], anchor="w",
                 wraplength=170, justify="left").pack(side="left")
        tk.Label(f, text=derecha, font=fuente(9, True), fg=C["gris"],
                 bg=C["blanco"]).pack(side="right")


def _autores(padre, filas, fondo):
    fila = tk.Frame(padre, bg=fondo)
    for a in filas:
        celda = tk.Frame(fila, bg=fondo)
        celda.pack(side="left", padx=7)
        avatar(celda, a["nombre"][:1], 46, "#d9e8e6", "#2a7f78", fondo).pack()
        corto = " ".join(a["nombre"].split()[:2])
        tk.Label(celda, text=corto, font=fuente(8), fg=C["texto"], bg=fondo,
                 wraplength=70).pack()
    return fila


class Pantalla(PantallaBase):
    def __init__(self, padre, app, **_):
        if app.sesion.es_personal:
            super().__init__(padre, app, "Panel", "Panel de control")
            self._panel_personal()
        else:
            super().__init__(padre, app, "Inicio", f"Hola, {app.sesion.nombre.split()[0]}")
            self._pagina_lector()

    # ------------------------------------------------------------------
    def _panel_personal(self):
        e = datos.estadisticas(self.con)
        c = self.cuerpo
        _buscador(c, self.app).pack(fill="x", pady=(0, 12))

        rejilla = tk.Frame(c, bg=C["blanco"])
        rejilla.pack(fill="x")
        for col in range(4):
            rejilla.columnconfigure(col, weight=1, uniform="t")
        primera = [("Usuarios activos", C["cian"], "☷", e["usuarios"], None),
                   ("Préstamos activos", C["verde"], "➤", e["prestamos"], "devoluciones"),
                   ("Materiales", C["rojo_t"], "▤", e["materiales"], "catalogo"),
                   ("Atrasados", C["naranja"], "⚠", e["atrasados"], "devoluciones")]
        segunda = [("Gestionar\nmateriales", C["rojo_t"], "▤", "materiales"),
                   ("Gestionar\nusuarios", C["naranja"], "☺", "usuarios"),
                   ("Registrar\npréstamo", C["cian"], "➤", "prestamos"),
                   ("Préstamos y\ndevoluciones", C["verde"], "↺", "devoluciones")]
        for n, (titulo, color, icono, valor, destino) in enumerate(primera):
            Tile(rejilla, titulo, color, icono, valor,
                 (lambda d=destino: self.app.ir(d)) if destino else None
                 ).grid(row=0, column=n, sticky="ew", padx=6, pady=6)
        for n, (titulo, color, icono, destino) in enumerate(segunda):
            Tile(rejilla, titulo, color, icono, None,
                 lambda d=destino: self.app.ir(d)).grid(row=1, column=n, sticky="ew", padx=6, pady=6)

        fila = tk.Frame(c, bg=C["blanco"])
        fila.pack(fill="both", expand=True, pady=(10, 0))
        for col in range(3):
            fila.columnconfigure(col, weight=1, uniform="c")

        t1 = tarjeta(fila)
        t1.grid(row=0, column=0, sticky="nsew", padx=6)
        tk.Label(t1, text="Más solicitados", font=fuente(10, True), fg=C["texto"],
                 bg=C["blanco"]).pack(anchor="w", padx=14, pady=(10, 4))
        _lista(t1, [(p["titulo"], f"{p['veces']}") for p in datos.populares(self.con, 5)])

        t2 = tarjeta(fila)
        t2.grid(row=0, column=1, sticky="nsew", padx=6)
        tk.Label(t2, text="Próximos vencimientos", font=fuente(10, True), fg=C["texto"],
                 bg=C["blanco"]).pack(anchor="w", padx=14, pady=(10, 4))
        _lista(t2, [(f"{p['titulo']}\n{p['usuario']}", p["fecha_limite"][5:])
                    for p in datos.por_vencer(self.con, 4)], "No hay préstamos activos.")

        t3 = tarjeta(fila)
        t3.grid(row=0, column=2, sticky="nsew", padx=6)
        tk.Label(t3, text="Resumen del inventario", font=fuente(10, True), fg=C["texto"],
                 bg=C["blanco"]).pack(anchor="w", padx=14, pady=(10, 4))
        _lista(t3, [("Ejemplares en total", e["ejemplares"]),
                    ("Disponibles", e["disponibles"]),
                    ("Prestados", e["ejemplares"] - e["disponibles"]),
                    ("Autores registrados", e["autores"])])

    # ------------------------------------------------------------------
    def _pagina_lector(self):
        c = self.cuerpo
        c.columnconfigure(0, weight=1)
        c.columnconfigure(1, weight=0, minsize=230)
        izq = tk.Frame(c, bg=C["blanco"])
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        der = tk.Frame(c, bg=C["blanco"])
        der.grid(row=0, column=1, sticky="nsew")

        _buscador(izq, self.app).pack(fill="x", pady=(0, 12))

        banner = tk.Frame(izq, bg=C["morado"], height=118)
        banner.pack(fill="x")
        banner.pack_propagate(False)
        tk.Label(banner, text="MATERIALES MÁS LEÍDOS\nDE ESTOS MESES", font=fuente(15, True),
                 fg="white", bg=C["morado"], justify="left").place(x=22, y=14)
        tk.Label(banner, text="Mira los títulos que más se piden en la biblioteca.",
                 font=fuente(9), fg="#e5d8f4", bg=C["morado"]).place(x=22, y=62)
        boton(banner, "VER AHORA", lambda: self.app.ir("catalogo"),
              C["verde_btn"]).place(x=22, y=84, height=26)
        tk.Label(banner, text="📖", font=fuente(44), fg="#d8c3ee",
                 bg=C["morado"]).place(relx=1.0, x=-30, rely=0.5, anchor="e")

        cab = tk.Frame(izq, bg=C["blanco"])
        cab.pack(fill="x", pady=(14, 4))
        tk.Label(cab, text="Populares", font=fuente(11, True), fg=C["texto"],
                 bg=C["blanco"]).pack(side="left")
        enlace(cab, "Ver todo", lambda: self.app.ir("catalogo"), C["verde_btn"],
               C["blanco"], 9).pack(side="left", padx=10)
        portadas = tk.Frame(izq, bg=C["blanco"])
        portadas.pack(fill="x")
        for n, p in enumerate(datos.populares(self.con, 5)):
            f = tk.Frame(portadas, bg=C["blanco"])
            f.pack(side="left", padx=(0, 12))
            tapa = tk.Frame(f, bg=PORTADAS[n % len(PORTADAS)], width=96, height=118)
            tapa.pack()
            tapa.pack_propagate(False)
            tk.Label(tapa, text=p["titulo"], font=fuente(9, True), fg="white",
                     bg=PORTADAS[n % len(PORTADAS)], wraplength=84, justify="center"
                     ).pack(expand=True)
            tk.Label(f, text=p["categoria"], font=fuente(8), fg=C["gris"],
                     bg=C["blanco"]).pack(pady=(3, 0))

        cab2 = tk.Frame(izq, bg=C["blanco"])
        cab2.pack(fill="x", pady=(14, 6))
        tk.Label(cab2, text="Autores destacados", font=fuente(11, True), fg=C["texto"],
                 bg=C["blanco"]).pack(side="left")
        _autores(izq, datos.autores_destacados(self.con, 7), C["blanco"]).pack(anchor="w")

        total, activos = datos.leidos_por(self.con, self.sesion.id_usuario)
        e = datos.estadisticas(self.con)
        datos_f = tk.Frame(izq, bg=C["blanco"])
        datos_f.pack(fill="x", pady=(14, 0))
        for n, (num, texto, color) in enumerate([(total, "Préstamos realizados", C["verde_btn"]),
                                                  (e["autores"], "Autores", C["acento"]),
                                                  (activos, "En préstamo ahora", C["morado"])]):
            t = tarjeta(datos_f)
            t.pack(side="left", fill="x", expand=True, padx=(0 if n == 0 else 8, 0))
            tk.Label(t, text=str(num), font=fuente(15, True), fg=color,
                     bg=C["blanco"]).pack(side="left", padx=(12, 6), pady=8)
            tk.Label(t, text=texto, font=fuente(9), fg=C["gris"], bg=C["blanco"]
                     ).pack(side="left")

        # Columna derecha: próximos vencimientos del lector
        t = tarjeta(der)
        t.pack(fill="x")
        tk.Label(t, text="Mis próximos vencimientos", font=fuente(10, True), fg=C["texto"],
                 bg=C["blanco"]).pack(anchor="w", padx=14, pady=(10, 4))
        _lista(t, [(p["titulo"], p["fecha_limite"][5:])
                   for p in datos.por_vencer(self.con, 5, self.sesion.id_usuario)],
               "No tienes préstamos activos.")
        caja = tk.Frame(der, bg=C["morado"])
        caja.pack(fill="x", pady=(14, 0))
        tk.Label(caja, text="Consulta tu historial\ny renueva tu lectura", font=fuente(11, True),
                 fg="white", bg=C["morado"], justify="center").pack(padx=14, pady=(18, 8))
        boton(caja, "Mis préstamos", lambda: self.app.ir("mis_prestamos"),
              C["verde_btn"]).pack(pady=(0, 18))
