"""Ventana principal: barra superior, menú lateral y zona de contenido.

Fusiona los dos prototipos: el panel azul del bibliotecario (menú lateral y
cuadros de colores) y la página del lector (buscador, populares y autores).
El menú cambia según el rol de quien entró.
"""

import tkinter as tk

from src.interfaz import (bitacora, catalogo, datos, devoluciones, inicio, materiales,
                          perfil, prestamos, seguridad, usuarios)
from src.interfaz.estilos import C, avatar, fuente

# clave -> (texto del menú, icono, clase de la pantalla)
SECCIONES = {
    "inicio": ("Panel de control", "▦", inicio.Pantalla),
    "perfil": ("Mi perfil", "☺", perfil.Pantalla),
    "usuarios": ("Gestionar usuarios", "☷", usuarios.Pantalla),
    "materiales": ("Gestionar materiales", "▤", materiales.Pantalla),
    "catalogo": ("Catálogo", "⌕", catalogo.Pantalla),
    "prestamos": ("Registrar préstamo", "➤", prestamos.Pantalla),
    "devoluciones": ("Préstamos y devoluciones", "↺", devoluciones.Pantalla),
    "mis_prestamos": ("Mis préstamos", "↺", devoluciones.MisPrestamos),
    "bitacora": ("Bitácora del sistema", "✎", bitacora.Pantalla),
}


class VentanaPrincipal(tk.Frame):
    def __init__(self, padre, app):
        super().__init__(padre, bg=C["blanco"])
        self.app = app
        self.con, self.sesion = app.con, app.sesion
        self.filas, self.actual, self.pantalla = {}, None, None
        self._barra_superior()
        cuerpo = tk.Frame(self, bg=C["blanco"])
        cuerpo.pack(fill="both", expand=True)
        self._menu_lateral(cuerpo)
        derecha = tk.Frame(cuerpo, bg=C["blanco"])
        derecha.pack(side="left", fill="both", expand=True)
        tk.Label(derecha, text="© Biblioteca BNPHU. Todos los derechos reservados.",
                 font=fuente(9), fg=C["gris"], bg=C["blanco"]).pack(side="bottom", pady=6)
        self.contenido = tk.Frame(derecha, bg=C["blanco"])
        self.contenido.pack(fill="both", expand=True)
        self.ir("inicio")

    # ------------------------------------------------------------------
    def _barra_superior(self):
        barra = tk.Frame(self, bg=C["azul"], height=52)
        barra.pack(fill="x")
        barra.pack_propagate(False)

        marca = tk.Frame(barra, bg=C["azul"])
        marca.pack(side="left", padx=14)
        tk.Label(marca, text="▤", font=fuente(13), fg=C["azul"], bg="white",
                 width=2).pack(side="left")
        tk.Label(marca, text="BNPHU", font=fuente(12, True), fg="white",
                 bg=C["azul"]).pack(side="left", padx=8)

        titulo = ("Panel del bibliotecario" if self.sesion.es_personal
                  else "Biblioteca BNPHU")
        tk.Label(barra, text=titulo, font=fuente(15), fg="white",
                 bg=C["azul"]).place(relx=0.5, rely=0.5, anchor="center")

        derecha = tk.Frame(barra, bg=C["azul"])
        derecha.pack(side="right", padx=14)
        campana = tk.Frame(derecha, bg=C["azul"])
        campana.pack(side="left", padx=(0, 16))
        tk.Label(campana, text="🔔", font=fuente(13), fg="white", bg=C["azul"]).pack()
        self.insignia = tk.Label(campana, text="0", font=fuente(7, True), fg="white",
                                 bg=C["rojo"], padx=3)
        self.insignia.place(relx=1.0, y=0, anchor="ne")
        avatar(derecha, self.sesion.mostrar[:1], 34, "#e3e8ed", "#7d8995",
               C["azul"]).pack(side="left")
        usuario = tk.Menubutton(derecha, text=f"{self.sesion.mostrar} ▾", font=fuente(10),
                                fg="white", bg=C["azul"], activebackground=C["azul_osc"],
                                activeforeground="white", relief="flat", bd=0, cursor="hand2")
        menu = tk.Menu(usuario, tearoff=0, font=fuente(10))
        menu.add_command(label="Mi perfil", command=lambda: self.ir("perfil"))
        menu.add_separator()
        menu.add_command(label="Cerrar sesión", command=self.app.cerrar_sesion)
        usuario["menu"] = menu
        usuario.pack(side="left", padx=6)
        self.refrescar_campana()

    def _menu_lateral(self, padre):
        lado = tk.Frame(padre, bg=C["azul"], width=222)
        lado.pack(side="left", fill="y")
        lado.pack_propagate(False)

        perfil_f = tk.Frame(lado, bg=C["azul"])
        perfil_f.pack(fill="x", padx=14, pady=(18, 4))
        avatar(perfil_f, self.sesion.mostrar[:1], 58, "#e3e8ed", "#7d8995",
               C["azul"]).pack(side="left")
        textos = tk.Frame(perfil_f, bg=C["azul"])
        textos.pack(side="left", padx=12)
        tk.Label(textos, text="¡Bienvenido!", font=fuente(9), fg="white",
                 bg=C["azul"]).pack(anchor="w")
        tk.Label(textos, text=self.sesion.mostrar, font=fuente(12, True), fg="white",
                 bg=C["azul"], wraplength=110, justify="left").pack(anchor="w")
        tk.Label(lado, text="General", font=fuente(14, True), fg="white", bg=C["azul"]
                 ).pack(anchor="w", padx=14, pady=(14, 0))
        tk.Frame(lado, bg="white", height=2, width=64).pack(anchor="w", padx=14, pady=(2, 12))

        for clave in seguridad.MENU_POR_ROL[self.sesion.rol]:
            texto, icono, _ = SECCIONES[clave]
            if clave == "inicio" and not self.sesion.es_personal:
                texto = "Inicio"
            self._fila_menu(lado, clave, texto, icono)
        self._fila_menu(lado, "salir", "Cerrar sesión", "✕", self.app.cerrar_sesion)

    def _fila_menu(self, padre, clave, texto, icono, accion=None):
        fila = tk.Frame(padre, bg=C["azul"], cursor="hand2")
        fila.pack(fill="x")
        marca = tk.Frame(fila, bg=C["azul"], width=4)
        marca.pack(side="left", fill="y")
        etiqueta = tk.Label(fila, text=f"{icono}   {texto}", font=fuente(10), fg="white",
                            bg=C["azul"], anchor="w", padx=12, pady=9, cursor="hand2")
        etiqueta.pack(side="left", fill="x", expand=True)
        self.filas[clave] = (fila, marca, etiqueta)
        for w in (fila, etiqueta):
            w.bind("<Button-1>", lambda _e, c=clave, a=accion: a() if a else self.ir(c))
            w.bind("<Enter>", lambda _e, c=clave: self._pintar(c, hover=True))
            w.bind("<Leave>", lambda _e, c=clave: self._pintar(c))

    def _pintar(self, clave, hover=False):
        fila, marca, etiqueta = self.filas[clave]
        activo = clave == self.actual
        fondo = C["menu_sel"] if activo or hover else C["azul"]
        for w in (fila, etiqueta):
            w.config(bg=fondo)
        marca.config(bg=C["acento"] if activo else fondo)

    # ------------------------------------------------------------------
    def ir(self, clave, **opciones):
        """Cambia de sección (y deja constancia en la bitácora)."""
        if not self.sesion.puede(clave):
            seguridad.registrar(self.con, self.sesion, "Acceso denegado",
                                f"Intentó abrir «{clave}»")
            return
        anterior, self.actual = self.actual, clave
        if self.pantalla is not None:
            self.pantalla.destroy()
        clase = SECCIONES[clave][2]
        self.pantalla = clase(self.contenido, self, **opciones)
        self.pantalla.pack(fill="both", expand=True)
        for k in self.filas:
            self._pintar(k)
        if clave != anterior:
            self.log("Abrió una sección", SECCIONES[clave][0])
        self.refrescar_campana()

    def log(self, accion, detalle=""):
        seguridad.registrar(self.con, self.sesion, accion, detalle)

    def refrescar_campana(self):
        datos.actualizar_atrasos(self.con)
        n = datos.atrasados_de(self.con, None if self.sesion.es_personal
                               else self.sesion.id_usuario)
        self.insignia.config(text=str(n))
        if n:
            self.insignia.place(relx=1.0, y=0, anchor="ne")
        else:
            self.insignia.place_forget()
