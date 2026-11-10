"""Perfil de la persona que inició sesión y cambio de contraseña."""

import tkinter as tk
from tkinter import messagebox

from src.interfaz import seguridad
from src.interfaz.estilos import C, PantallaBase, avatar, boton, fuente, tarjeta


class Pantalla(PantallaBase):
    def __init__(self, padre, app, **_):
        super().__init__(padre, app, "Mi perfil", "Tus datos y tu contraseña")
        s = self.sesion
        fila = tk.Frame(self.cuerpo, bg=C["blanco"])
        fila.pack(fill="x")

        datos_f = tarjeta(fila)
        datos_f.pack(side="left", fill="both", expand=True, padx=(0, 10))
        avatar(datos_f, s.mostrar[:1], 70, "#e3e8ed", "#7d8995", C["blanco"]).pack(pady=(18, 6))
        tk.Label(datos_f, text=s.nombre, font=fuente(13, True), fg=C["texto"],
                 bg=C["blanco"]).pack()
        ultimo = seguridad.ultimo_acceso(self.con, s.usuario)
        for etiqueta, valor in (("Usuario", s.usuario), ("Rol", s.rol),
                                ("Último acceso", ultimo or "Es tu primer acceso")):
            f = tk.Frame(datos_f, bg=C["blanco"])
            f.pack(fill="x", padx=24, pady=3)
            tk.Label(f, text=etiqueta, font=fuente(9), fg=C["gris"], bg=C["blanco"]).pack(side="left")
            tk.Label(f, text=valor, font=fuente(10), fg=C["texto"], bg=C["blanco"]).pack(side="right")
        tk.Frame(datos_f, height=16, bg=C["blanco"]).pack()

        clave_f = tarjeta(fila)
        clave_f.pack(side="left", fill="both", expand=True, padx=(10, 0))
        tk.Label(clave_f, text="Cambiar contraseña", font=fuente(11, True), fg=C["texto"],
                 bg=C["blanco"]).pack(anchor="w", padx=20, pady=(16, 6))
        self.campos = {}
        for clave, etiqueta in (("actual", "Contraseña actual"), ("nueva", "Contraseña nueva"),
                                ("repetir", "Repite la contraseña nueva")):
            tk.Label(clave_f, text=etiqueta, font=fuente(9), fg=C["gris"],
                     bg=C["blanco"]).pack(anchor="w", padx=20)
            e = tk.Entry(clave_f, show="•", font=fuente(10), relief="flat", bd=0,
                         highlightthickness=1, highlightbackground=C["linea"],
                         highlightcolor=C["acento"])
            e.pack(fill="x", padx=20, pady=(0, 8), ipady=5)
            self.campos[clave] = e
        boton(clave_f, "Guardar contraseña", self.cambiar, C["verde"]).pack(anchor="w", padx=20,
                                                                              pady=(2, 18))

    def cambiar(self):
        try:
            seguridad.cambiar_clave(self.con, self.sesion, self.campos["actual"].get(),
                                    self.campos["nueva"].get(), self.campos["repetir"].get())
        except seguridad.ErrorSeguridad as error:
            messagebox.showwarning("Contraseña", str(error))
            return
        for e in self.campos.values():
            e.delete(0, "end")
        messagebox.showinfo("Contraseña", "Tu contraseña se cambió correctamente.")
