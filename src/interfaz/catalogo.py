"""Catálogo: disponibilidad de cada material (usa src/reportes.py)."""

import tkinter as tk
from tkinter import ttk

from src import reportes
from src.interfaz import datos
from src.interfaz.estilos import C, PantallaBase, Tabla, fuente


class Pantalla(PantallaBase):
    def __init__(self, padre, app, texto="", **_):
        super().__init__(padre, app, "Catálogo", "Disponibilidad de los materiales")
        barra = tk.Frame(self.cuerpo, bg=C["blanco"])
        barra.pack(fill="x", pady=(0, 8))
        tk.Label(barra, text="Buscar:", font=fuente(9), fg=C["gris"], bg=C["blanco"]).pack(side="left")
        self.busqueda = tk.StringVar(value=texto)
        entrada = tk.Entry(barra, textvariable=self.busqueda, font=fuente(10), relief="flat",
                           highlightthickness=1, highlightbackground=C["linea"],
                           highlightcolor=C["acento"], width=32)
        entrada.pack(side="left", padx=8, ipady=3)
        entrada.bind("<KeyRelease>", lambda _e: self.cargar())

        tk.Label(barra, text="Categoría:", font=fuente(9), fg=C["gris"],
                 bg=C["blanco"]).pack(side="left", padx=(12, 0))
        self.categoria = tk.StringVar(value="Todas")
        combo = ttk.Combobox(barra, textvariable=self.categoria, state="readonly", width=18,
                             values=["Todas"] + [c["nombre"] for c in datos.categorias(self.con)])
        combo.pack(side="left", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.cargar())

        self.solo = tk.BooleanVar(value=False)
        tk.Checkbutton(barra, text="Solo con ejemplares disponibles", variable=self.solo,
                       command=self.cargar, font=fuente(9), bg=C["blanco"], fg=C["texto"],
                       activebackground=C["blanco"], selectcolor="white").pack(side="left", padx=8)

        self.tabla = Tabla(self.cuerpo, [("titulo", "Título", 270), ("categoria", "Categoría", 110),
                                         ("anio", "Año", 55), ("total_ejemplares", "Ejemplares", 80),
                                         ("disponibles", "Disponibles", 85),
                                         ("prestados", "Prestados", 75)],
                           alto=14, al_doble_clic=self.detalle)
        self.tabla.pack(fill="both", expand=True)
        self.pie = tk.Label(self.cuerpo, text="", font=fuente(9), fg=C["gris"], bg=C["blanco"])
        self.pie.pack(anchor="w", pady=(6, 0))
        self.cargar()

    def cargar(self):
        t = self.busqueda.get().strip().lower()
        autores = {m["id_material"]: m["autores"].lower() for m in datos.listar_materiales(self.con)}
        filas = []
        for f in reportes.catalogo(self.con):
            f = dict(f)
            if t and t not in f["titulo"].lower() and t not in autores.get(f["id_material"], "") \
                    and t not in (f["isbn"] or ""):
                continue
            if self.categoria.get() != "Todas" and f["categoria"] != self.categoria.get():
                continue
            if self.solo.get() and not f["disponibles"]:
                continue
            filas.append(f)
        self.tabla.cargar(filas, "id_material", alerta=lambda f: f["disponibles"] == 0)
        self.pie.config(text=f"{len(filas)} materiales. Haz doble clic en uno para ver sus "
                             f"ejemplares (en rojo: sin ejemplares disponibles).")

    def detalle(self):
        fila = self.tabla.valores_elegido()
        if not fila:
            return
        self.app.log("Consultó un material", fila["titulo"])
        ventana = tk.Toplevel(self)
        ventana.title(fila["titulo"])
        ventana.configure(bg=C["blanco"])
        ventana.geometry("460x330")
        ventana.transient(self.winfo_toplevel())
        autores = next((m["autores"] for m in datos.listar_materiales(self.con, fila["titulo"])
                        if str(m["id_material"]) == self.tabla.elegido()), "")
        tk.Label(ventana, text=fila["titulo"], font=fuente(13, True), fg=C["texto"],
                 bg=C["blanco"], wraplength=420, justify="left").pack(anchor="w", padx=18, pady=(16, 2))
        tk.Label(ventana, text=f"{autores or 'Autor no registrado'}  ·  {fila['categoria']}  ·  "
                               f"{fila['anio'] or 's. f.'}", font=fuente(9), fg=C["gris"],
                 bg=C["blanco"]).pack(anchor="w", padx=18)
        tabla = Tabla(ventana, [("codigo", "Código", 120), ("estado", "Estado", 120)], alto=8)
        tabla.pack(fill="both", expand=True, padx=18, pady=14)
        ejemplares = datos.ejemplares_de(self.con, int(self.tabla.elegido()))
        tabla.cargar(ejemplares, "id_ejemplar", alerta=lambda f: f["estado"] != "Disponible")
