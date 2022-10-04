import csv
import unittest

from elements.augmentation_intensity import IntensidadeAugmentation

# list with intensifiers
PATH_INTENSIFIERS = "data/augmentation/intensificaveis.csv"


class TestIntensityAugmentation(unittest.TestCase):
    def test_constructor(self):
        """Checks if the class has been initialized correctly"""
        try:
            _ = IntensidadeAugmentation(PATH_INTENSIFIERS, max_new_sentences=1)
        except Exception as e:
            self.fail(e)

    def test_data_without_augmentation(self):
        """Checks if augmentation works normally for without pattern for augmentation in corpus"""

        corpus = [("Eu apontei para ele.", "EU APONTAR&ALVO ELE [PONTO]")]
        length = 2
        augmentation = IntensidadeAugmentation(
            PATH_INTENSIFIERS, max_new_sentences=length
        )
        generated = augmentation.process(corpus)
        self.assertEqual(len(generated), len(corpus))

    def test_data_data_augmentation(self):
        """Checks if augmentation works normally"""

        corpus = [
            (
                "TOM SER GERALMENTE MUITO SUJO MUITO SORTUDO [PONTO]",
                "TOM GERALMENTE SUJO(+) SORTUDO(+) [PONTO]",
            ),
            ("ESTAR MUITO CANSAR [PONTO]", "EU CANSADO(+) [PONTO]"),
        ]
        length = 2
        augmentation = IntensidadeAugmentation(
            PATH_INTENSIFIERS, max_new_sentences=length
        )
        generated = augmentation.process(corpus)
        self.assertEqual(len(generated), len(corpus) + length)

    def test_duplicates_data_augmentation(self):
        """Check if augmantation contains duplicates data"""

        corpus = [("ESTAR COM MUITO MEDO [PONTO]", "EU MEDO(+) [PONTO]")]
        length = 0
        augmentation = IntensidadeAugmentation(
            PATH_INTENSIFIERS, max_new_sentences=length
        )
        generated = augmentation.process(corpus)

        for i, line in enumerate(generated):
            print(i, line)
        print("SET:")
        for i, line in enumerate(set(generated)):
            print(i, line)
        self.assertEqual(len(generated), len(set(generated)))


if __name__ == "__main__":
    unittest.main()

# PYTHONPATH=src/ python -m unittest tests/test_augmentation_intensity.py
