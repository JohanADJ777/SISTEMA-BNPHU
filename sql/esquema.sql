CREATE TABLE IF NOT EXISTS categoria (
    id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT NOT NULL UNIQUE,
    descripcion  TEXT
);

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre     TEXT NOT NULL,
    apellido   TEXT NOT NULL,
    documento  TEXT NOT NULL UNIQUE,
    telefono   TEXT,
    correo     TEXT,
    estado     TEXT NOT NULL DEFAULT 'Activo'
               CHECK (estado IN ('Activo', 'Inactivo', 'Suspendido'))
);

CREATE TABLE IF NOT EXISTS empleado (
    id_empleado     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    apellido        TEXT NOT NULL,
    cargo           TEXT NOT NULL,
    usuario_sistema TEXT NOT NULL UNIQUE,
    estado          TEXT NOT NULL DEFAULT 'Activo'
                    CHECK (estado IN ('Activo', 'Inactivo'))
);

CREATE TABLE IF NOT EXISTS autor (
    id_autor INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre   TEXT NOT NULL,
    apellido TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS material (
    id_material  INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo       TEXT NOT NULL,
    anio         INTEGER CHECK (anio IS NULL OR anio BETWEEN 1000 AND 2100),
    isbn         TEXT UNIQUE,
    categoria_id INTEGER NOT NULL,
    FOREIGN KEY (categoria_id) REFERENCES categoria (id_categoria)
);


CREATE TABLE IF NOT EXISTS material_autor (
    id_material INTEGER NOT NULL,
    id_autor    INTEGER NOT NULL,
    PRIMARY KEY (id_material, id_autor),
    FOREIGN KEY (id_material) REFERENCES material (id_material),
    FOREIGN KEY (id_autor)    REFERENCES autor (id_autor)
);

CREATE TABLE IF NOT EXISTS ejemplar (
    id_ejemplar INTEGER PRIMARY KEY AUTOINCREMENT,
    id_material INTEGER NOT NULL,
    codigo      TEXT NOT NULL UNIQUE,
    estado      TEXT NOT NULL DEFAULT 'Disponible'
                CHECK (estado IN ('Disponible', 'Prestado', 'Mantenimiento', 'Baja')),
    FOREIGN KEY (id_material) REFERENCES material (id_material)
);

CREATE TABLE IF NOT EXISTS prestamo (
    id_prestamo      INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario       INTEGER NOT NULL,
    id_ejemplar      INTEGER NOT NULL,
    id_empleado      INTEGER NOT NULL,
    fecha_prestamo   TEXT NOT NULL,   
    fecha_limite     TEXT NOT NULL,
    fecha_devolucion TEXT,            
    estado           TEXT NOT NULL DEFAULT 'Activo'
                     CHECK (estado IN ('Activo', 'Atrasado', 'Devuelto')),
    FOREIGN KEY (id_usuario)  REFERENCES usuario (id_usuario),
    FOREIGN KEY (id_ejemplar) REFERENCES ejemplar (id_ejemplar),
    FOREIGN KEY (id_empleado) REFERENCES empleado (id_empleado),
    CHECK (fecha_limite >= fecha_prestamo),
    CHECK (fecha_devolucion IS NULL OR fecha_devolucion >= fecha_prestamo)
);


CREATE INDEX IF NOT EXISTS ix_material_titulo    ON material (titulo);
CREATE INDEX IF NOT EXISTS ix_material_categoria ON material (categoria_id);
CREATE INDEX IF NOT EXISTS ix_ejemplar_material  ON ejemplar (id_material);
CREATE INDEX IF NOT EXISTS ix_ejemplar_estado    ON ejemplar (estado);
CREATE INDEX IF NOT EXISTS ix_prestamo_usuario   ON prestamo (id_usuario);
CREATE INDEX IF NOT EXISTS ix_prestamo_ejemplar  ON prestamo (id_ejemplar);
CREATE INDEX IF NOT EXISTS ix_prestamo_empleado  ON prestamo (id_empleado);
CREATE INDEX IF NOT EXISTS ix_prestamo_estado    ON prestamo (estado);

CREATE UNIQUE INDEX IF NOT EXISTS ux_prestamo_abierto
    ON prestamo (id_ejemplar) WHERE fecha_devolucion IS NULL;


CREATE VIEW IF NOT EXISTS vista_catalogo AS
SELECT m.id_material,
       m.titulo,
       m.anio,
       m.isbn,
       c.nombre AS categoria,
       COUNT(e.id_ejemplar) AS total_ejemplares,
       COALESCE(SUM(CASE WHEN e.estado = 'Disponible'    THEN 1 ELSE 0 END), 0) AS disponibles,
       COALESCE(SUM(CASE WHEN e.estado = 'Prestado'      THEN 1 ELSE 0 END), 0) AS prestados,
       COALESCE(SUM(CASE WHEN e.estado = 'Mantenimiento' THEN 1 ELSE 0 END), 0) AS mantenimiento
FROM material m
INNER JOIN categoria c ON c.id_categoria = m.categoria_id
LEFT JOIN  ejemplar  e ON e.id_material  = m.id_material
GROUP BY m.id_material, m.titulo, m.anio, m.isbn, c.nombre;

CREATE VIEW IF NOT EXISTS vista_disponibilidad AS
SELECT e.id_ejemplar,
       e.codigo,
       m.titulo,
       c.nombre AS categoria,
       e.estado
FROM ejemplar e
INNER JOIN material  m ON m.id_material  = e.id_material
INNER JOIN categoria c ON c.id_categoria = m.categoria_id;

CREATE VIEW IF NOT EXISTS vista_historial_prestamos AS
SELECT p.id_prestamo,
       u.nombre || ' ' || u.apellido   AS usuario,
       u.documento,
       e.codigo                        AS codigo_ejemplar,
       m.titulo,
       emp.nombre || ' ' || emp.apellido AS empleado,
       p.fecha_prestamo,
       p.fecha_limite,
       p.fecha_devolucion,
       p.estado
FROM prestamo p
INNER JOIN usuario  u   ON u.id_usuario   = p.id_usuario
INNER JOIN ejemplar e   ON e.id_ejemplar  = p.id_ejemplar
INNER JOIN material m   ON m.id_material  = e.id_material
INNER JOIN empleado emp ON emp.id_empleado = p.id_empleado;
