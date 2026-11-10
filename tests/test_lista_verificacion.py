"""Ejecuta la lista de verificación con unittest:

    python -m unittest discover -s tests -t .
"""

import unittest

from tests import lista_verificacion as lista


class ListaDeVerificacion(unittest.TestCase):
    def test_lista_completa(self):
        for r in lista.RESULTADOS:
            with self.subTest(r["prueba"]):
                ok, obtenido = r["fn"]()
                self.assertTrue(ok, f"{r['prueba']}: se esperaba «{r['esperado']}» "
                                    f"y se obtuvo «{obtenido}»")


if __name__ == "__main__":
    unittest.main()
