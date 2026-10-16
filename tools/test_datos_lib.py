"""Pruebas de datos_lib.py. Sin dependencias: python -I -X utf8 -m unittest tools.test_datos_lib  (o python tools/test_datos_lib.py)"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import datos_lib as L  # noqa: E402


class Epocas(unittest.TestCase):
    def test_mioceno_y_bordes(self):
        self.assertEqual(L.clasificar_edad(9.1)[2], "Mioceno")
        self.assertEqual(L.clasificar_edad(5.333)[2], "Mioceno")   # el límite pertenece al intervalo más joven... de abajo
        self.assertEqual(L.clasificar_edad(5.332)[2], "Plioceno")
        self.assertEqual(L.clasificar_edad(23.02)[2], "Mioceno")
        self.assertEqual(L.clasificar_edad(23.03)[2], "Oligoceno")

    def test_era_y_periodo(self):
        self.assertEqual(L.clasificar_edad(9.1)[:2], ("Cenozoico", "Neógeno"))
        self.assertEqual(L.clasificar_edad(120)[2], "Cretácico Inferior")
        self.assertEqual(L.clasificar_edad(1877)[0], "Precámbrico")
        self.assertEqual(L.clasificar_edad(None), (None, None, None))
        self.assertEqual(L.clasificar_edad(float("nan")), (None, None, None))


class Edades(unittest.TestCase):
    def test_unidades(self):
        self.assertEqual(L.edad_a_ma(9.1, "Ma ± 2σ")[0], 9.1)
        self.assertAlmostEqual(L.edad_a_ma(12000, "a 14C AP ± 1σ")[0], 0.012)
        self.assertAlmostEqual(L.edad_a_ma(12000, "AP")[0], 0.012)
        self.assertAlmostEqual(L.edad_a_ma(5, "ka AP ± 2σ")[0], 0.005)   # 'ka' manda sobre 'AP'
        self.assertAlmostEqual(L.edad_a_ma(1.2, "Ga ± 2σ")[0], 1200.0)

    def test_sin_unidad_se_infiere_y_se_marca(self):
        self.assertEqual(L.edad_a_ma(30, None, "K-Ar"), (30.0, 1.0, True))
        ma, _, inf = L.edad_a_ma(8000, None, "14C")
        self.assertAlmostEqual(ma, 0.008)
        self.assertTrue(inf)
        ma, _, inf = L.edad_a_ma(119000, None, "Resonancia electromagnética")   # >4.600 «Ma» = años
        self.assertAlmostEqual(ma, 0.119)
        self.assertTrue(inf)

    def test_nulo(self):
        self.assertEqual(L.edad_a_ma(None, "Ma"), (None, None, False))


class Metodos(unittest.TestCase):
    def test_grafias(self):
        for t, esperado in [("Uranio - Plomo (U-Pb)", "U-Pb"), ("Urano - Plomo (U-Pb)", "U-Pb"),
                            ("Potasio - Argon (K-Ar)", "K-Ar"), ("Potasio - Argón (K-Ar)", "K-Ar"),
                            ("Argón40 - Argón39 (40Ar-39Ar)", "Ar-Ar"), ("Argon - Argon (Ar-Ar)", "Ar-Ar"),
                            ("Carbono 14 (14C)", "14C"), ("Trazas de fisión", "Trazas de fisión"),
                            (None, "Sin método"), ("", "Sin método")]:
            self.assertEqual(L.normalizar_metodo(t), esperado, t)

    def test_desconocido_se_conserva(self):
        self.assertEqual(L.normalizar_metodo("Resonancia electromagnética"), "Resonancia electromagnética")


class Dominios(unittest.TestCase):
    XML = ("<GPCodedValueDomain2><DomainName>D</DomainName><CodedValues>"
           "<CodedValue><Name>Ma</Name><Code>DAT-UNIDAD-1</Code></CodedValue>"
           "<CodedValue><Name>Roca</Name><Code>DAT-TP-M-2</Code></CodedValue></CodedValues></GPCodedValueDomain2>")

    def test_parsear_y_resolver(self):
        dom = L.parsear_dominios([self.XML])["D"]
        self.assertEqual(L.resolver("DAT-UNIDAD-1", dom), "Ma")
        self.assertEqual(L.resolver("DAT-UNIDAD-1;DAT-TP-M-2", dom), "Ma; Roca")
        self.assertEqual(L.resolver("otro", dom), "otro")
        self.assertIsNone(L.resolver(None, dom))

    def test_respaldo_solo_para_codigos_no_ambiguos(self):
        doms = {"A": {"DAT-UNIDAD-1": "Ma", "0": "No"}, "B": {"DAT-UNIDAD-1": "Ma", "0": "Izq"}}
        r = L.codigos_unicos(doms)
        self.assertEqual(r.get("DAT-UNIDAD-1"), "Ma")
        self.assertNotIn("0", r)                       # códigos numéricos sueltos significan cosas distintas
        self.assertEqual(L.resolver("DAT-UNIDAD-1", None, r), "Ma")
        conflicto = L.codigos_unicos({"A": {"X-1": "uno"}, "B": {"X-1": "otro"}})
        self.assertNotIn("X-1", conflicto)

    def test_xml_malo_no_revienta(self):
        self.assertEqual(L.parsear_dominios(["<no es xml"]), {})
        self.assertEqual(L.campos_con_dominio("<no es xml"), {})


class Texto(unittest.TestCase):
    def test_periodo_epoca(self):
        self.assertEqual(L.periodo_epoca_de_texto("Serravalliano (Mioceno Medio alto)"), ("Neógeno", "Mioceno"))
        self.assertEqual(L.periodo_epoca_de_texto("Paleoceno"), ("Paleógeno", "Paleoceno"))   # no confundir con Eoceno
        self.assertEqual(L.periodo_epoca_de_texto("Jurásico Medio"), ("Jurásico", None))
        self.assertEqual(L.periodo_epoca_de_texto(None, ""), (None, None))


class Columnar(unittest.TestCase):
    def test_ida_y_vuelta(self):
        textos = ["a", "b", None, "a", "  ", float("nan")]
        c = L.columna(textos)
        self.assertEqual(c["d"], ["a", "b"])
        self.assertEqual(L.decodificar(c), ["a", "b", None, "a", None, None])
        nums = [1.5, None, 3]
        self.assertEqual(L.decodificar(L.columna(nums)), nums)

    def test_canonicalizar_une_variantes(self):
        m = L.canonicalizar(['Biotita'] * 3 + ['biotita', 'Anfíbola', 'Anf bola', 'Zircón', 'circon', 'roca total', 'Roca Total'])
        self.assertEqual(m['biotita'], 'Biotita')
        self.assertEqual(m['Anf bola'], 'Anfíbola')
        self.assertEqual(m['Zircón'], m['circon'])
        self.assertEqual(m['roca total'], m['Roca Total'])

    def test_estado_region(self):
        self.assertEqual(L.normalizar_estado('Paralizada'), 'Paralizado')
        self.assertIsNone(L.normalizar_estado('20% Mn'))
        self.assertEqual(L.normalizar_region("Libertador General Bernardo O&#039;Higgins-Metropolitana"), "O'Higgins|Metropolitana")
        self.assertEqual(L.normalizar_region('Area Fronteriza Chile-Argentina'), L.FRONTERA)


if __name__ == "__main__":
    unittest.main()
