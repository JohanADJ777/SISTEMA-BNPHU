"""Modelo Categoria: clasificación general de los materiales."""

from src.models.base import Modelo


class Categoria(Modelo):
    tabla = "categoria"
    pk = "id_categoria"
    campos = ("nombre", "descripcion")

    def __init__(self, nombre, descripcion=None, id_categoria=None):
        self.id_categoria = id_categoria
        self.nombre = nombre
        self.descripcion = descripcion
