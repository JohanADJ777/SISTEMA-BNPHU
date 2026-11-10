"""Bitácora del sistema: todo lo que hace cada persona queda registrado aquí."""

import csv
import tkinter as tk
from tkinter import filedialog, messagebox

from src.interfaz import seguridad
from src.interfaz.estilos import C, PantallaBase, Tabla, boton, fuente


class Pantalla(PantallaBase):
    def __init__(self, padre, app, **_):
        super().__init__(padre, app, "Bitácora del sistema", "Registro de actividad")
        barra = tk.Frame(self.cuerpo, bg=C["blanco"])
        barra.pack(fill="x", pady=(0, 8))
        tk.Label(barra, text="Buscar:", font=fuente(9), fg=C["gris"], bg=C["blanco"]).pack(side="left")
        self.busqueda = tk.StringVar()
        entrada = tk.Entry(barra, textvariable=self.busqueda, font=fuente(10), relief="flat",
                           highlightthickness=1, highlightbackground=C["linea"],
                           highlightcolor=C["acento"], width=34)
        entrada.pack(side="left", padx=8, ipady=3)
        entrada.bind("<KeyRelease>", lambda _e: self.cargar())
        boton(barra, "Exportar CSV", self.exportar, C["cian"]).pack(side="right")
        boton(barra, "Actualizar", self.cargar, "#8793a0").pack(side="right", padx=8)

        self.tabla = Tabla(self.cuerpo, [("fecha_hora", "Fecha y hora", 140), ("usuario", "Usuario", 90),
                                         ("rol", "Rol", 95), ("accion", "Acción", 170),
                                         ("detalle", "Detalle", 280), ("equipo", "Equipo", 150)],
                           alto=15)
        self.tabla.pack(fill="both", expand=True)
        self.pie = tk.Label(self.cuerpo, text="", font=fuente(9), fg=C["gris"], bg=C["blanco"])
        self.pie.pack(anchor="w", pady=(6, 0))
        self.cargar()

    def _filas(self):
        return [dict(f) for f in seguridad.listar_bitacora(self.con, self.busqueda.get())]

    def cargar(self):
        filas = self._filas()
        self.tabla.cargar(filas, "id_bitacora",
                          alerta=lambda f: f["accion"] in ("Intento fallido", "Acceso bloqueado",
                                                           "Acceso denegado"))
        self.pie.config(text=f"Se muestran los últimos {len(filas)} registros. "
                             "En rojo: intentos fallidos y accesos denegados.")

    def exportar(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="bitacora.csv",
                                            filetypes=[("CSV", "*.csv")])
        if not ruta:
            return
        filas = self._filas()
        with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
            w = csv.writer(archivo)
            w.writerow(["fecha_hora", "usuario", "rol", "accion", "detalle", "equipo"])
            for f in filas:
                w.writerow([f["fecha_hora"], f["usuario"], f["rol"], f["accion"], f["detalle"],
                            f["equipo"]])
        self.app.log("Bitácora exportada", f"{len(filas)} registros")
        messagebox.showinfo("Bitácora", f"Se guardaron {len(filas)} registros en:\n{ruta}")
