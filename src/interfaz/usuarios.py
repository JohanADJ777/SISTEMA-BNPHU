"""Formulario para administrar usuarios (lectores): crear, editar y eliminar."""

import tkinter as tk
from tkinter import messagebox

from src.interfaz import datos, seguridad
from src.interfaz.estilos import C, Formulario, PantallaBase, Tabla, boton, fuente, tarjeta

CAMPOS = [("nombre", "Nombre", "texto", None),
          ("apellido", "Apellido", "texto", None),
          ("documento", "Documento (cédula)", "texto", None),
          ("telefono", "Teléfono", "texto", None),
          ("correo", "Correo electrónico", "texto", None),
          ("estado", "Estado", "combo", list(datos.ESTADOS_USUARIO))]


class Pantalla(PantallaBase):
    def __init__(self, padre, app, **_):
        super().__init__(padre, app, "Gestionar usuarios", "Registro de lectores")
        self.id_actual = None
        caja = tarjeta(self.cuerpo)
        caja.pack(fill="x")
        self.titulo_form = tk.Label(caja, text="Nuevo usuario", font=fuente(10, True),
                                    fg=C["texto"], bg=C["blanco"])
        self.titulo_form.pack(anchor="w", padx=14, pady=(10, 0))
        self.form = Formulario(caja, CAMPOS, columnas=3, fondo=C["blanco"])
        self.form.pack(fill="x", padx=14, pady=(2, 6))

        botones = tk.Frame(caja, bg=C["blanco"])
        botones.pack(fill="x", padx=14, pady=(0, 12))
        boton(botones, "Guardar", self.guardar, C["verde"]).pack(side="left")
        boton(botones, "Nuevo", self.nuevo, "#8793a0").pack(side="left", padx=8)
        self.btn_eliminar = boton(botones, "Eliminar", self.eliminar, C["rojo_t"])
        if self.sesion.rol == "Administrador":
            self.btn_eliminar.pack(side="left")
        self.form.limpiar(estado="Activo")

        barra = tk.Frame(self.cuerpo, bg=C["blanco"])
        barra.pack(fill="x", pady=(14, 6))
        tk.Label(barra, text="Buscar:", font=fuente(9), fg=C["gris"],
                 bg=C["blanco"]).pack(side="left")
        self.busqueda = tk.StringVar()
        entrada = tk.Entry(barra, textvariable=self.busqueda, font=fuente(10), relief="flat",
                           highlightthickness=1, highlightbackground=C["linea"],
                           highlightcolor=C["acento"], width=34)
        entrada.pack(side="left", padx=8, ipady=3)
        entrada.bind("<KeyRelease>", lambda _e: self.cargar())

        self.tabla = Tabla(self.cuerpo, [("nombre", "Nombre", 120), ("apellido", "Apellido", 130),
                                         ("documento", "Documento", 120),
                                         ("telefono", "Teléfono", 110),
                                         ("correo", "Correo", 220), ("estado", "Estado", 90)],
                           alto=9, al_elegir=self.elegir)
        self.tabla.pack(fill="both", expand=True)
        self.cargar()

    def cargar(self):
        self.tabla.cargar(datos.listar_usuarios(self.con, self.busqueda.get()), "id_usuario",
                          alerta=lambda f: f["estado"] != "Activo")

    def nuevo(self):
        self.id_actual = None
        self.titulo_form.config(text="Nuevo usuario")
        self.form.limpiar(estado="Activo")
        self.tabla.arbol.selection_remove(self.tabla.arbol.selection())

    def elegir(self):
        iid = self.tabla.elegido()
        if not iid:
            return
        self.id_actual = int(iid)
        fila = self.con.execute("SELECT * FROM usuario WHERE id_usuario = ?",
                                (self.id_actual,)).fetchone()
        self.form.poner(dict(fila))
        self.titulo_form.config(text=f"Editando a {fila['nombre']} {fila['apellido']}")

    def guardar(self):
        d = self.form.valores()
        try:
            if self.id_actual:
                datos.actualizar_usuario(self.con, self.id_actual, d)
                self.app.log("Usuario actualizado", f"{d['nombre']} {d['apellido']} ({d['documento']})")
                messagebox.showinfo("Usuarios", "Los datos del usuario se guardaron.")
            else:
                _, cuenta = datos.crear_usuario(self.con, d)
                self.app.log("Usuario creado", f"{d['nombre']} {d['apellido']} ({d['documento']})")
                messagebox.showinfo(
                    "Usuarios",
                    f"Usuario creado.\n\nCuenta de acceso: {cuenta}\n"
                    f"Contraseña inicial: {seguridad.CLAVE_LECTOR}")
        except datos.ErrorDatos as error:
            messagebox.showwarning("Revisa el formulario", str(error))
            return
        self.nuevo()
        self.cargar()
        self.app.refrescar_campana()

    def eliminar(self):
        if not self.id_actual:
            messagebox.showinfo("Usuarios", "Elige primero un usuario de la tabla.")
            return
        d = self.form.valores()
        if not messagebox.askyesno("Eliminar usuario",
                                   f"¿Eliminar a {d['nombre']} {d['apellido']}?"):
            return
        try:
            datos.eliminar_usuario(self.con, self.id_actual)
        except datos.ErrorDatos as error:
            messagebox.showwarning("No se pudo eliminar", str(error))
            return
        self.app.log("Usuario eliminado", f"{d['nombre']} {d['apellido']} ({d['documento']})")
        self.nuevo()
        self.cargar()
