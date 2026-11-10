"""Clase base de todos los modelos.

Contiene las cuatro operaciones básicas (CRUD) escritas una sola vez.
Cada modelo solo indica su tabla, su llave primaria y sus campos.
"""


class Modelo:
    tabla = ""      # nombre de la tabla en la base de datos
    pk = ""         # nombre de la llave primaria (id)
    campos = ()     # columnas de la tabla, sin contar la llave primaria

    # ---------- utilidades internas ----------
    def _valores(self):
        return tuple(getattr(self, campo) for campo in self.campos)

    @property
    def id(self):
        return getattr(self, self.pk)

    @classmethod
    def _desde_fila(cls, fila):
        """Convierte una fila de la base de datos en un objeto."""
        if fila is None:
            return None
        datos = {campo: fila[campo] for campo in cls.campos}
        datos[cls.pk] = fila[cls.pk]
        return cls(**datos)

    def __repr__(self):
        partes = [f"{self.pk}={self.id!r}"]
        partes += [f"{c}={getattr(self, c)!r}" for c in self.campos]
        return f"{type(self).__name__}({', '.join(partes)})"

    # ---------- C: Crear ----------
    def crear(self, conexion):
        columnas = ", ".join(self.campos)
        marcas = ", ".join("?" for _ in self.campos)
        sql = f"INSERT INTO {self.tabla} ({columnas}) VALUES ({marcas})"
        cursor = conexion.execute(sql, self._valores())
        conexion.commit()
        setattr(self, self.pk, cursor.lastrowid)
        return self

    # ---------- R: Consultar ----------
    @classmethod
    def consultar(cls, conexion, id):
        sql = f"SELECT * FROM {cls.tabla} WHERE {cls.pk} = ?"
        return cls._desde_fila(conexion.execute(sql, (id,)).fetchone())

    @classmethod
    def listar(cls, conexion):
        sql = f"SELECT * FROM {cls.tabla} ORDER BY {cls.pk}"
        return [cls._desde_fila(f) for f in conexion.execute(sql).fetchall()]

    # ---------- U: Actualizar ----------
    def actualizar(self, conexion):
        asignaciones = ", ".join(f"{campo} = ?" for campo in self.campos)
        sql = f"UPDATE {self.tabla} SET {asignaciones} WHERE {self.pk} = ?"
        conexion.execute(sql, self._valores() + (self.id,))
        conexion.commit()
        return self

    # ---------- D: Eliminar ----------
    def eliminar(self, conexion):
        sql = f"DELETE FROM {self.tabla} WHERE {self.pk} = ?"
        conexion.execute(sql, (self.id,))
        conexion.commit()
        setattr(self, self.pk, None)
