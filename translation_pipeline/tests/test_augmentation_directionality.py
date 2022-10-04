import csv
import unittest

from elements.augmentation_directionality import Directionality_Augmentation


class TestDirectionalityAugmentation(unittest.TestCase):
    def test_constructor(self):
        """Checks if the class has been initialized correctly"""
        try:
            _ = Directionality_Augmentation(max_new_sentences=2)
        except Exception as e:
            self.fail(e)

    def test_without_augmentation(self):
        """Checks if augmentation works normally"""

        corpus = [
            (
                "ELE PEDIR ELA SE ELA CONHECER ELE [PONTO]",
                "PERGUNTAR_3S_3S CONHECER [PONTO]",
            ),
            ("ESTAR MUITO CANSAR [PONTO]", "EU CANSADO(+) [PONTO]"),
        ]
        length = 2
        augmentation = Directionality_Augmentation(max_new_sentences=length)
        generated = augmentation.process(corpus)
        self.assertEqual(len(generated), len(corpus))

    def test_data_augmentation(self):
        """Checks if augmentation works normally"""

        corpus = [
            ("ELA ME DAR VÁRIOS LIVRO [PONTO]", "DAR_3S_2S VÁRIOS LIVRO [PONTO]"),
            (
                "ELE PEDIR ELA SE ELA CONHECER ELE [PONTO]",
                "PERGUNTAR_3S_3S CONHECER [PONTO]",
            ),
            (
                "DEFENDER JESUÍTAS QUE HAVER SER EXPULSOS MARQUÊS POMBAL UM MIL SETECENTOS E CINQUENTA E NOVE DECLARAR NÃO ESQUECER NUNCA BOM ENSINAMENTO INSTRUÇÃO QUE ELES DAR EU [PONTO]",
                "DEFENDER JESUÍTA EXPULSAR MARQUÊS POMBAL ANO&DATA um mil setecentos e cinquenta e nove DECLARAR NÃO_ESQUECER NUNCA ENSINAR_1S_2S INSTRUÇÃO DAR_3S_2S [PONTO]",
            ),
        ]
        length = 5
        augmentation = Directionality_Augmentation(max_new_sentences=length)
        generated = augmentation.process(corpus)
        self.assertEqual(len(generated), len(corpus) + length)


if __name__ == "__main__":
    unittest.main()

# PYTHONPATH=src/ python -m unittest tests/test_augmentation_directionality.py
