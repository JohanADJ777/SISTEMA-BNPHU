"""Punto de entrada de las interfaces del Sistema de préstamos BNPHU.

Para ejecutarlo (desde la carpeta del proyecto):  python app.py
(main.py sigue siendo la prueba de consola y BORRA la base de datos: no lo uses
 si quieres conservar tus datos.)
"""

import sqlite3
import tkinter as tk
from tkinter import messagebox

from src.config import NOMBRE_PROYECTO, RUTA_BD
from src.database import conectar, inicializar
from src.interfaz import datos, seguridad
from src.interfaz.estilos import iniciar_estilos
from src.interfaz.login import PantallaLogin
from src.interfaz.ventana_principal import VentanaPrincipal


class Aplicacion:
    def __init__(self):
        self.con = conectar()
        self.sesion = None
        self.raiz = tk.Tk()
        self.raiz.title(NOMBRE_PROYECTO)
        iniciar_estilos(self.raiz)
        self.raiz.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.pantalla = None
        self.preparar_base()
        self.mostrar_login()

    def preparar_base(self):
        existe = self.con.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                  "AND name='usuario'").fetchone()
        if not existe:                       # base vacía: se crea con tus archivos .sql
            inicializar(self.con)
        seguridad.preparar(self.con)
        datos.actualizar_atrasos(self.con)

    def centrar(self, ancho, alto):
        x = (self.raiz.winfo_screenwidth() - ancho) // 2
        y = max(0, (self.raiz.winfo_screenheight() - alto) // 2 - 20)
        self.raiz.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _cambiar(self, pantalla):
        if self.pantalla is not None:
            self.pantalla.destroy()
        self.pantalla = pantalla
        pantalla.pack(fill="both", expand=True)

    def mostrar_login(self):
        self.sesion = None
        self.raiz.minsize(1, 1)
        self.raiz.resizable(False, False)
        login = PantallaLogin(self.raiz, self)
        self._cambiar(login)
        self.raiz.update_idletasks()
        self.centrar(int(login["width"]), int(login["height"]))

    def mostrar_principal(self, sesion):
        self.sesion = sesion
        datos.actualizar_atrasos(self.con)
        self.raiz.resizable(True, True)
        self.raiz.minsize(980, 620)
        self.centrar(1120, 700)
        self._cambiar(VentanaPrincipal(self.raiz, self))

    def cerrar_sesion(self):
        seguridad.registrar(self.con, self.sesion, "Cierre de sesión", "Salió del sistema")
        self.mostrar_login()

    def cerrar(self):
        if self.sesion:
            seguridad.registrar(self.con, self.sesion, "Cierre de sesión",
                                "Cerró la ventana del programa")
        self.con.close()
        self.raiz.destroy()

    def ejecutar(self):
        self.raiz.mainloop()


if __name__ == "__main__":
    try:
        Aplicacion().ejecutar()
    except sqlite3.Error as error:
        messagebox.showerror(
            "Base de datos",
            f"No se pudo preparar {RUTA_BD.name}:\n{error}\n\n"
            "Si el mensaje habla de los archivos .sql, revisa la carpeta sql.\n"
            "Si la base ya existe y está incompleta, ejecuta reparar_base.py.")
