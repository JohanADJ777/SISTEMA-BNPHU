"""Préstamos activos y registro de devoluciones (personal) / historial del lector."""

import tkinter as tk
from tkinter import messagebox

from src import reportes
from src.interfaz import datos
from src.interfaz.estilos import C, PantallaBase, Tabla, boton, fuente


class Pantalla(PantallaBase):
    def __init__(self, padre, app, **_):
        super().__init__(padre, app, "Préstamos y devoluciones", "Materiales que están fuera")
        barra = tk.Frame(self.cuerpo, bg=C["blanco"])
        barra.pack(fill="x", pady=(0, 8))
        tk.Label(barra, text="Buscar:", font=fuente(9), fg=C["gris"], bg=C["blanco"]).pack(side="left")
        self.busqueda = tk.StringVar()
        entrada = tk.Entry(barra, textvariable=self.busqueda, font=fuente(10), relief="flat",
                           highlightthickness=1, highlightbackground=C["linea"],
                           highlightcolor=C["acento"], width=34)
        entrada.pack(side="left", padx=8, ipady=3)
        entrada.bind("<KeyRelease>", lambda _e: self.cargar())
        boton(barra, "Registrar devolución", self.devolver, C["verde"]).pack(side="right")
        self.resumen = tk.Label(barra, text="", font=fuente(9), fg=C["gris"], bg=C["blanco"])
        self.resumen.pack(side="right", padx=14)

        self.tabla = Tabla(self.cuerpo, [("usuario", "Usuario", 170), ("codigo_ejemplar", "Ejemplar", 90),
                                         ("titulo", "Título", 230), ("fecha_prestamo", "Prestado", 90),
                                         ("fecha_limite", "Fecha límite", 95),
                                         ("estado", "Estado", 80)], alto=14)
        self.tabla.pack(fill="both", expand=True)
        tk.Label(self.cuerpo, text="Las filas en rojo están atrasadas. Elige una y pulsa "
                 "«Registrar devolución».", font=fuente(9), fg=C["gris"],
                 bg=C["blanco"]).pack(anchor="w", pady=(6, 0))
        self.cargar()

    def cargar(self):
        t = self.busqueda.get().strip().lower()
        filas = [dict(f) for f in reportes.prestamos_activos(self.con)
                 if not t or t in f["usuario"].lower() or t in f["titulo"].lower()
                 or t in f["codigo_ejemplar"].lower()]
        self.tabla.cargar(filas, "id_prestamo", alerta=lambda f: f["estado"] == "Atrasado")
        self.resumen.config(text=f"{len(filas)} préstamos activos")

    def devolver(self):
        fila = self.tabla.valores_elegido()
        if not fila:
            messagebox.showinfo("Devoluciones", "Elige primero un préstamo de la tabla.")
            return
        if not messagebox.askyesno("Registrar devolución",
                                   f"¿Se devolvió «{fila['titulo']}» ({fila['codigo_ejemplar']})?"):
            return
        try:
            datos.devolver_prestamo(self.con, int(self.tabla.elegido()))
        except datos.ErrorDatos as error:
            messagebox.showwarning("No se pudo registrar", str(error))
            return
        self.app.log("Devolución registrada", f"{fila['codigo_ejemplar']} de {fila['usuario']}")
        self.cargar()
        self.app.refrescar_campana()


class MisPrestamos(PantallaBase):
    """Historial de préstamos de la persona que inició sesión (solo lectura)."""

    def __init__(self, padre, app, **_):
        super().__init__(padre, app, "Mis préstamos", "Tu historial en la biblioteca")
        documento = self.con.execute("SELECT documento FROM usuario WHERE id_usuario = ?",
                                     (self.sesion.id_usuario,)).fetchone()[0]
        filas = [dict(f) for f in reportes.historial_usuario(self.con, documento)][::-1]
        tabla = Tabla(self.cuerpo, [("titulo", "Título", 260), ("codigo_ejemplar", "Ejemplar", 90),
                                    ("fecha_prestamo", "Prestado", 95),
                                    ("fecha_limite", "Fecha límite", 100),
                                    ("fecha_devolucion", "Devuelto", 95), ("estado", "Estado", 85)],
                      alto=14)
        tabla.pack(fill="both", expand=True)
        tabla.cargar(filas, "id_prestamo", alerta=lambda f: f["estado"] == "Atrasado")
        tk.Label(self.cuerpo, text="Si un préstamo aparece en rojo, devuélvelo lo antes posible.",
                 font=fuente(9), fg=C["gris"], bg=C["blanco"]).pack(anchor="w", pady=(6, 0))
