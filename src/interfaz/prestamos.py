"""Formulario para registrar un préstamo."""

import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox

from src.config import DIAS_PRESTAMO
from src.interfaz import datos
from src.interfaz.estilos import C, Formulario, PantallaBase, Tabla, boton, fuente, tarjeta


class Pantalla(PantallaBase):
    def __init__(self, padre, app, **_):
        super().__init__(padre, app, "Registrar préstamo", "Entrega de material a un usuario")
        caja = tarjeta(self.cuerpo)
        caja.pack(fill="x")
        tk.Label(caja, text="Datos del préstamo", font=fuente(10, True), fg=C["texto"],
                 bg=C["blanco"]).pack(anchor="w", padx=14, pady=(10, 0))

        self.form = Formulario(caja, [("usuario", "Usuario", "combo", []),
                                      ("ejemplar", "Ejemplar disponible", "combo", []),
                                      ("dias", "Días de préstamo", "texto", None)],
                               columnas=3, fondo=C["blanco"])
        self.form.pack(fill="x", padx=14, pady=(2, 4))
        self.form.vars["dias"].set(str(DIAS_PRESTAMO))
        self.form.vars["dias"].trace_add("write", lambda *_: self._fecha())

        fila = tk.Frame(caja, bg=C["blanco"])
        fila.pack(fill="x", padx=14, pady=(0, 4))
        tk.Label(fila, text="Filtrar ejemplares:", font=fuente(9), fg=C["gris"],
                 bg=C["blanco"]).pack(side="left")
        self.filtro = tk.StringVar()
        entrada = tk.Entry(fila, textvariable=self.filtro, font=fuente(10), relief="flat",
                           highlightthickness=1, highlightbackground=C["linea"],
                           highlightcolor=C["acento"], width=30)
        entrada.pack(side="left", padx=8, ipady=3)
        entrada.bind("<KeyRelease>", lambda _e: self._cargar_ejemplares())
        self.fecha = tk.Label(fila, text="", font=fuente(9, True), fg=C["texto"], bg=C["blanco"])
        self.fecha.pack(side="right")

        botones = tk.Frame(caja, bg=C["blanco"])
        botones.pack(fill="x", padx=14, pady=(4, 12))
        boton(botones, "Registrar préstamo", self.registrar, C["verde"]).pack(side="left")
        boton(botones, "Limpiar", self.limpiar, "#8793a0").pack(side="left", padx=8)

        tk.Label(self.cuerpo, text="Últimos préstamos registrados", font=fuente(10, True),
                 fg=C["texto"], bg=C["blanco"]).pack(anchor="w", pady=(14, 6))
        self.tabla = Tabla(self.cuerpo, [("usuario", "Usuario", 170), ("titulo", "Título", 220),
                                         ("codigo_ejemplar", "Ejemplar", 90),
                                         ("fecha_prestamo", "Fecha", 90),
                                         ("fecha_limite", "Devolver antes de", 120),
                                         ("estado", "Estado", 80)], alto=7)
        self.tabla.pack(fill="both", expand=True)
        self._cargar_usuarios()
        self._cargar_ejemplares()
        self._fecha()
        self.cargar()

    def _cargar_usuarios(self):
        self.usuarios = {u["etiqueta"]: u["id_usuario"] for u in datos.usuarios_para_prestamo(self.con)}
        self.form.opciones("usuario", list(self.usuarios))

    def _cargar_ejemplares(self):
        self.ejemplares = {e["etiqueta"]: e["id_ejemplar"]
                           for e in datos.ejemplares_disponibles(self.con, self.filtro.get())}
        self.form.opciones("ejemplar", list(self.ejemplares))
        if self.form.vars["ejemplar"].get() not in self.ejemplares:
            self.form.vars["ejemplar"].set("")

    def _fecha(self):
        dias = self.form.vars["dias"].get().strip()
        if dias.isdigit() and 1 <= int(dias) <= 60:
            limite = date.today() + timedelta(days=int(dias))
            self.fecha.config(text=f"Fecha límite: {limite.strftime('%d/%m/%Y')}")
        else:
            self.fecha.config(text="")

    def cargar(self):
        self.tabla.cargar(datos.prestamos_recientes(self.con, 8))

    def limpiar(self):
        self.form.limpiar(dias=str(DIAS_PRESTAMO))
        self.filtro.set("")
        self._cargar_ejemplares()

    def registrar(self):
        d = self.form.valores()
        try:
            limite = datos.registrar_prestamo(
                self.con, self.usuarios.get(d["usuario"]), self.ejemplares.get(d["ejemplar"]),
                self.sesion.id_empleado, d["dias"])
        except datos.ErrorDatos as error:
            messagebox.showwarning("No se pudo registrar", str(error))
            return
        self.app.log("Préstamo registrado", f"{d['ejemplar']} -> {d['usuario']} (hasta {limite})")
        messagebox.showinfo("Préstamo registrado", f"El préstamo quedó registrado.\n"
                                                   f"Debe devolverse antes del {limite}.")
        self.limpiar()
        self.cargar()
        self.app.refrescar_campana()
