"""Pruebas de litología inferida e intervalos de edad de exportar_vectores."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import exportar_vectores as V  # noqa: E402
import litologia as T  # noqa: E402


class Litologia(unittest.TestCase):
    def test_nombre_manda(self):
        self.assertEqual(T.inferir("Granodioritas de Los Pelambres", "con xenolitos de andesita")[0], "Plutónicas")

    def test_depositos(self):
        self.assertEqual(T.inferir("Gravas del río Huasco", "Depósitos aterrazados")[0], "Depósitos no consolidados")

    def test_ambiente_de_respaldo(self):
        self.assertEqual(T.inferir("Plutón Chivato", None, None, "AMBIENTE PLUTONICO"), ("Plutónicas", []))

    def test_sin_nada(self):
        self.assertEqual(T.inferir("Formación Totoralillo")[0], T.SIN_LITO)


class Edades(unittest.TestCase):
    def test_epoca_y_combinadas(self):
        self.assertEqual(V.intervalo_texto("Mioceno"), (23.03, 5.333))
        self.assertEqual(V.intervalo_texto("Cretácico Sup-Paleoceno"), (100.5, 56.0))
        self.assertIsNone(V.intervalo_texto("T-EPOCA-19"))

    def test_geocronologica_manda(self):
        self.assertEqual(V.edad_unidad("Mioceno", "Mioceno", None, None, "96", "63")[:2], (96.0, 63.0))

    def test_epocas_que_toca(self):
        self.assertEqual(V.epocas_que_toca(23.03, 5.333), ["Mioceno"])
        self.assertIn("Eoceno", V.epocas_que_toca(66.0, 23.03))   # Paleógeno completo
        self.assertEqual(V.epocas_que_toca(0.0117, 0), ["Holoceno"])

    def test_ambiente(self):
        self.assertEqual(V.ambiente_canon("AMBIENTE VOLCANICO SEDIMENTARIO"), "Volcánico-sedimentario")
        self.assertEqual(V.ambiente_canon("Unidad Intrusiva"), "Plutónico / intrusivo")


if __name__ == "__main__":
    unittest.main()
