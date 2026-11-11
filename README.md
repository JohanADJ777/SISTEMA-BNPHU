# Sistema de préstamos BNPHU

Aplicación de escritorio para llevar los préstamos de la Biblioteca Nacional Pedro Henríquez
Ureña (BNPHU): usuarios, materiales, ejemplares (las copias físicas), préstamos y devoluciones.
Está hecha en Python con Tkinter para las pantallas y SQLite para guardar los datos.

Autor: Johan Almanzar de Jesús
Curso: 5toC, Politécnico El Ave María
Docente: Robinson Sánchez

## Qué hace

- Inicio de sesión con tres roles: Administrador, Empleado y Lector.
- Gestionar usuarios (lectores): crear, editar y eliminar, con validación de documento, correo y teléfono.
- Gestionar materiales y sus ejemplares, con autores y categorías.
- Catálogo con búsqueda y estado de cada ejemplar.
- Registrar préstamos y devoluciones. Los préstamos que pasan de su fecha límite se marcan como atrasados.
- Bitácora: guarda en la base de datos todo lo que se hace en el sistema (entradas, intentos fallidos, cambios).
- Seguridad: las contraseñas se guardan cifradas y la cuenta se bloquea 5 minutos después de 5 intentos fallidos.

## Cómo empezar

Necesitas Python 3.10 o superior. No hay que instalar nada más (Tkinter y SQLite vienen con Python).

```
git clone https://github.com/JohanADJ777/SISTEMA-BNPHU.git
cd SISTEMA-BNPHU
python app.py
```

La primera vez que se abre, el programa crea la base `bnphu.db` con los archivos de la carpeta
`sql` y carga datos de ejemplo. No hay que preparar nada a mano.

## Cuentas para probar

| Rol           | Usuario        | Contraseña   |
|---------------|----------------|--------------|
| Administrador | admin          | admin123     |
| Empleado      | aperez         | empleado123  |
| Lector        | ana.martinez   | lector123    |

Cada empleado y cada lector de los datos de ejemplo tiene su cuenta. A un empleado le sirven la
contraseña `empleado123` y a un lector `lector123`. Se puede cambiar desde Mi perfil.

Qué ve cada rol: el Administrador ve todo, incluida la bitácora. El Empleado ve todo menos la
bitácora. El Lector solo ve el inicio, el catálogo, sus préstamos y su perfil.

## Cómo está organizado

El programa está dividido en capas. Cada una solo habla con la que tiene debajo:

```
proyecto_base/
├── app.py                   # Abre la aplicación con pantallas
├── main.py                  # Prueba por consola (BORRA la base y la crea de nuevo)
├── reparar_base.py          # Arregla una base ya creada sin perder datos
├── conexion.py              # Comprueba la conexión a la base
├── editar_bd.py             # Ejemplo de cómo cambiar datos desde Python
├── requirements.txt         # Dependencias (ninguna externa)
├── sql/
│   ├── esquema.sql          # Tablas, índices y vistas
│   └── datos.sql            # Datos de ejemplo
├── assets/                  # Imágenes de las pantallas
├── src/
│   ├── config.py            # Capa de configuración: rutas y valores generales
│   ├── database.py          # Capa de acceso a datos: conexión y creación de la base
│   ├── models/              # Capa de modelos: una clase por tabla
│   ├── reportes.py          # Consultas de solo lectura (catálogo, préstamos activos)
│   └── interfaz/
│       ├── datos.py         # Capa de lógica: reglas y validaciones de las pantallas
│       ├── seguridad.py     # Cuentas, roles, bloqueo y bitácora
│       └── (pantallas)      # login, inicio, usuarios, materiales, catálogo,
│                            # préstamos, devoluciones, bitácora, perfil
└── tests/
    ├── lista_verificacion.py       # 66 pruebas por capa, con [OK] o [ERROR]
    └── test_lista_verificacion.py  # La misma lista para unittest
```

Las pantallas no escriben SQL: le piden las cosas a `datos.py`, que aplica las reglas y usa los
modelos, y los modelos hablan con la base a través de `database.py`.

## Cómo probar que funciona

```
python tests/lista_verificacion.py
```

Corre 66 pruebas sobre una copia temporal de la base (la tuya no se toca) y al final muestra una
línea como `RESULTADO: 66 pruebas correctas de 66 | 0 con error`.

## Si algo falla

- Si la base quedó a medias por un error anterior: cierra cualquier programa que tenga abierto
  `bnphu.db` y ejecuta `python reparar_base.py`. Guarda un respaldo en la carpeta `respaldo` antes
  de cambiar nada.
- No uses `main.py` si quieres conservar tus datos, porque borra la base y la vuelve a crear.
