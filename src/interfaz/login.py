"""Pantalla de inicio de sesión (prototipo 1: «Librarian Login Form», en español)."""

import tkinter as tk
from tkinter import messagebox

from src.config import RAIZ
from src.interfaz import seguridad
from src.interfaz.estilos import C, boton, fuente

RUTA_FONDO = RAIZ / "assets" / "fondo_login.png"

# Posición del recuadro gris dentro de la imagen de fondo (ya viene en el tamaño final)
CAJA_X, CAJA_Y = 22, 22


class CampoConTexto(tk.Entry):
    """Campo con borde rojo y texto de ayuda gris, como en el prototipo."""

    def __init__(self, padre, ayuda, secreto=False):
        super().__init__(padre, font=fuente(11), relief="flat", bd=0, bg="white",
                         highlightthickness=1, highlightbackground=C["borde_rojo"],
                         highlightcolor=C["borde_rojo"], insertbackground=C["texto"])
        self.ayuda, self.secreto, self.vacio = ayuda, secreto, True
        self.bind("<FocusIn>", self._entrar)
        self.bind("<FocusOut>", self._salir)
        self.bind("<Key>", self._tecla)
        self.bind("<<Paste>>", lambda _e: self._quitar_ayuda())
        self._poner_ayuda()

    def _poner_ayuda(self):
        self.vacio = True
        self.config(show="", fg="#8a8a8a")
        self.delete(0, "end")
        self.insert(0, self.ayuda)
        self.icursor(0)

    def _quitar_ayuda(self):
        if self.vacio:
            self.delete(0, "end")
            self.config(fg=C["texto"], show="•" if self.secreto else "")
            self.vacio = False

    def _entrar(self, _e):
        if self.vacio:
            self.icursor(0)      # la ayuda sigue visible hasta que se escribe algo

    def _tecla(self, e):
        if self.vacio and e.char and e.char.isprintable():
            self._quitar_ayuda()
        elif self.vacio and e.keysym in ("BackSpace", "Delete"):
            return "break"

    def _salir(self, _e):
        if not self.get():
            self._poner_ayuda()

    def texto(self):
        return "" if self.vacio else self.get()

    def vaciar(self):
        self._poner_ayuda()


class PantallaLogin(tk.Frame):
    def __init__(self, padre, app):
        self.fondo = tk.PhotoImage(file=str(RUTA_FONDO))
        super().__init__(padre, width=self.fondo.width(), height=self.fondo.height())
        self.app = app
        tk.Label(self, image=self.fondo, bd=0).place(x=0, y=0)

        izq, ancho = CAJA_X + 43, 362
        y0 = CAJA_Y
        gris = C["caja"]
        tk.Label(self, text="Formulario de acceso del bibliotecario", font=fuente(13),
                 fg=C["texto"], bg=gris).place(x=izq, y=y0 + 40)

        self.usuario = CampoConTexto(self, "Usuario")
        self.usuario.place(x=izq, y=y0 + 100, width=ancho, height=40)
        self.clave = CampoConTexto(self, "Contraseña", secreto=True)
        self.clave.place(x=izq, y=y0 + 166, width=ancho, height=40)

        boton(self, "Iniciar sesión", self.entrar).place(x=izq, y=y0 + 232, height=40)
        olvido = tk.Label(self, text="¿Olvidaste tu contraseña?", font=fuente(10, True, True),
                          fg=C["texto"], bg=gris, cursor="hand2")
        olvido.place(x=izq + ancho, y=y0 + 242, anchor="ne")
        olvido.bind("<Button-1>", lambda _e: self.olvide_clave())

        self.mensaje = tk.Label(self, text="", font=fuente(9), fg=C["rojo"], bg=gris)
        self.mensaje.place(x=izq, y=y0 + 288)

        for campo in (self.usuario, self.clave):
            campo.bind("<Return>", lambda _e: self.entrar())
        self.usuario.focus_set()

    def entrar(self):
        try:
            sesion = seguridad.autenticar(self.app.con, self.usuario.texto(), self.clave.texto())
        except seguridad.ErrorSeguridad as error:
            self.mensaje.config(text=str(error))
            self.clave.vaciar()
            self.focus_set()
            return
        self.app.mostrar_principal(sesion)

    def olvide_clave(self):
        seguridad.registrar(self.app.con, None, "Recuperación de contraseña solicitada",
                            "Pulsó «¿Olvidaste tu contraseña?»", self.usuario.texto() or None)
        messagebox.showinfo(
            "Recuperar contraseña",
            "Pronto podrás recuperar el acceso con un código enviado a tu correo.\n\n"
            "Por ahora, pide al administrador que restablezca tu contraseña.")
