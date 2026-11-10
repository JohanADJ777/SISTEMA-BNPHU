"""Modelo Material: título o recurso bibliográfico (la obra, no la copia)."""

from src.models.autor import Autor
from src.models.base import Modelo


class Material(Modelo):
    tabla = "material"
    pk = "id_material"
    campos = ("titulo", "anio", "isbn", "categoria_id")

    def __init__(self, titulo, categoria_id, anio=None, isbn=None, id_material=None):
        self.id_material = id_material
        self.titulo = titulo
        self.anio = anio
        self.isbn = isbn
        self.categoria_id = categoria_id

    # ---------- relación con Autor (tabla material_autor) ----------
    def agregar_autor(self, conexion, id_autor):
        conexion.execute(
            "INSERT OR IGNORE INTO material_autor (id_material, id_autor) VALUES (?, ?)",
            (self.id_material, id_autor),
        )
        conexion.commit()

    def autores(self, conexion):
        filas = conexion.execute(
            """SELECT a.* FROM autor a
               JOIN material_autor ma ON ma.id_autor = a.id_autor
               WHERE ma.id_material = ?""",
            (self.id_material,),
        ).fetchall()
        return [Autor._desde_fila(f) for f in filas]

    @classmethod
    def buscar_por_titulo(cls, conexion, texto):
        filas = conexion.execute(
            "SELECT * FROM material WHERE titulo LIKE ? ORDER BY titulo",
            (f"%{texto}%",),
        ).fetchall()
        return [cls._desde_fila(f) for f in filas]
