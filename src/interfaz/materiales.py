"""Formulario para administrar materiales (libros, revistas...) y sus ejemplares."""

import tkinter as tk
from tkinter import messagebox

from src.interfaz import datos
from src.interfaz.estilos import C, Formulario, PantallaBase, Tabla, boton, fuente, tarjeta


class Pantalla(PantallaBase):
    def __init__(self, padre, app, **_):
        super().__init__(padre, app, "Gestionar materiales", "Libros y ejemplares")
        self.id_actual = None
        self.categorias = {c["nombre"]: c["id_categoria"] for c in datos.categorias(self.con)}

        caja = tarjeta(self.cuerpo)
        caja.pack(fill="x")
        self.titulo_form = tk.Label(caja, text="Nuevo material", font=fuente(10, True),
                                    fg=C["texto"], bg=C["blanco"])
        self.titulo_form.pack(anchor="w", padx=14, pady=(10, 0))
        self.form = Formulario(caja, [
            ("titulo", "Título", "texto", None),
            ("autores", "Autores (separados por coma)", "texto", None),
            ("categoria", "Categoría", "combo", list(self.categorias)),
            ("anio", "Año de publicación", "texto", None),
            ("isbn", "ISBN", "texto", None)], columnas=3, fondo=C["blanco"])
        self.form.pack(fill="x", padx=14, pady=(2, 6))

        botones = tk.Frame(caja, bg=C["blanco"])
        botones.pack(fill="x", padx=14, pady=(0, 6))
        boton(botones, "Guardar", self.guardar, C["verde"]).pack(side="left")
        boton(botones, "Nuevo", self.nuevo, "#8793a0").pack(side="left", padx=8)
        boton(botones, "Eliminar", self.eliminar, C["rojo_t"]).pack(side="left")
        boton(botones, "+ Agregar ejemplar", self.agregar_ejemplar, C["cian"]).pack(side="right")
        self.info = tk.Label(caja, text="", font=fuente(9), fg=C["gris"], bg=C["blanco"],
                             anchor="w", justify="left", wraplength=760)
        self.info.pack(fill="x", padx=14, pady=(0, 10))

        barra = tk.Frame(self.cuerpo, bg=C["blanco"])
        barra.pack(fill="x", pady=(12, 6))
        tk.Label(barra, text="Buscar:", font=fuente(9), fg=C["gris"], bg=C["blanco"]).pack(side="left")
        self.busqueda = tk.StringVar()
        entrada = tk.Entry(barra, textvariable=self.busqueda, font=fuente(10), relief="flat",
                           highlightthickness=1, highlightbackground=C["linea"],
                           highlightcolor=C["acento"], width=34)
        entrada.pack(side="left", padx=8, ipady=3)
        entrada.bind("<KeyRelease>", lambda _e: self.cargar())

        self.tabla = Tabla(self.cuerpo, [("titulo", "Título", 230), ("autores", "Autores", 190),
                                         ("categoria", "Categoría", 110), ("anio", "Año", 55),
                                         ("isbn", "ISBN", 120), ("ejemplares", "Ejemplares", 75)],
                           alto=8, al_elegir=self.elegir)
        self.tabla.pack(fill="both", expand=True)
        self.cargar()

    def cargar(self):
        self.tabla.cargar(datos.listar_materiales(self.con, self.busqueda.get()), "id_material")

    def nuevo(self):
        self.id_actual = None
        self.titulo_form.config(text="Nuevo material")
        self.info.config(text="")
        self.form.limpiar()
        self.tabla.arbol.selection_remove(self.tabla.arbol.selection())

    def elegir(self):
        iid = self.tabla.elegido()
        if not iid:
            return
        self.id_actual = int(iid)
        fila = next(m for m in datos.listar_materiales(self.con, "") if m["id_material"] == self.id_actual)
        d = dict(fila)
        self.form.poner(d)
        self.form.vars["categoria"].set(d["categoria"])
        self.titulo_form.config(text=f"Editando: {d['titulo']}")
        self._mostrar_ejemplares()

    def _mostrar_ejemplares(self):
        ejemplares = datos.ejemplares_de(self.con, self.id_actual)
        texto = ", ".join(f"{e['codigo']} ({e['estado']})" for e in ejemplares)
        self.info.config(text=f"Ejemplares: {texto}" if texto else "Todavía no tiene ejemplares.")

    def _datos(self):
        d = self.form.valores()
        d["categoria_id"] = self.categorias.get(d["categoria"])
        return d

    def guardar(self):
        d = self._datos()
        try:
            if self.id_actual:
                datos.actualizar_material(self.con, self.id_actual, d)
                self.app.log("Material actualizado", d["titulo"])
                messagebox.showinfo("Materiales", "Los datos del material se guardaron.")
            else:
                datos.crear_material(self.con, d)
                self.app.log("Material creado", d["titulo"])
                messagebox.showinfo("Materiales", "Material creado. Ahora puedes agregarle "
                                    "ejemplares con el botón «+ Agregar ejemplar».")
        except datos.ErrorDatos as error:
            messagebox.showwarning("Revisa el formulario", str(error))
            return
        self.nuevo()
        self.cargar()

    def agregar_ejemplar(self):
        if not self.id_actual:
            messagebox.showinfo("Materiales", "Elige primero un material de la tabla.")
            return
        codigo = datos.agregar_ejemplar(self.con, self.id_actual)
        self.app.log("Ejemplar agregado", f"{codigo} de «{self.form.valores()['titulo']}»")
        self._mostrar_ejemplares()
        self.cargar()

    def eliminar(self):
        if not self.id_actual:
            messagebox.showinfo("Materiales", "Elige primero un material de la tabla.")
            return
        titulo = self.form.valores()["titulo"]
        if not messagebox.askyesno("Eliminar material", f"¿Eliminar «{titulo}»?"):
            return
        try:
            datos.eliminar_material(self.con, self.id_actual)
        except datos.ErrorDatos as error:
            messagebox.showwarning("No se pudo eliminar", str(error))
            return
        self.app.log("Material eliminado", titulo)
        self.nuevo()
        self.cargar()
