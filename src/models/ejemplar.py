"""Modelo Ejemplar: copia física de un material (por ejemplo BNPHU-001)."""

from src.models.base import Modelo


class Ejemplar(Modelo):
    tabla = "ejemplar"
    pk = "id_ejemplar"
    campos = ("id_material", "codigo", "estado")

    def __init__(self, id_material, codigo, estado="Disponible", id_ejemplar=None):
        self.id_ejemplar = id_ejemplar
        self.id_material = id_material
        self.codigo = codigo
        self.estado = estado  # Disponible, Prestado, Mantenimiento o Baja

    @classmethod
    def disponibles_de(cls, conexion, id_material):
        """Devuelve los ejemplares de un material que se pueden prestar."""
        filas = conexion.execute(
            "SELECT * FROM ejemplar WHERE id_material = ? AND estado = 'Disponible'",
            (id_material,),
        ).fetchall()
        return [cls._desde_fila(f) for f in filas]
