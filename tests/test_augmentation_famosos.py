import unittest
import csv

from elements.augmentation_famosos import FamososAugmentation

# lista com todos os famosos
PATH_FAMOSOS = 'data/augmentation/famosos.csv'

class TestFamososAugmentation(unittest.TestCase):
    def test_constructor(self):
        # verifica se a classe foi inicializada corretamente
        try:
            _ = FamososAugmentation(path=PATH_FAMOSOS, max_new_sentences=1)
        except Exception as e:
            self.fail(e)

    def test_data_without_augmentation(self):
        # verifica se o tamanho do corpus eh modificado sem ter nenhum dado referente a famosos para ser aumentado
        corpus = [
            ('COMO PODER PASSAR TEMPO [INTERROGAÇÃO]', 'COMO PODER&POSSIBILIDADE PASSAR&TEMPO [INTERROGAÇÃO]'),
            ('COMO PODER AGRADECER [INTERROGAÇÃO]', 'COMO PODER&POSSIBILIDADE AGRADECER ELE [INTERROGAÇÃO]')
        ]
        augmentation = FamososAugmentation(
            path=PATH_FAMOSOS, max_new_sentences=50)
        generated = augmentation.process(corpus)
        self.assertEqual(len(generated), len(corpus))

    def test_len_data_augmentation(self):
        # verifica o tamanho de frases geradas a partir de um corpus com dados de famosos
        corpus = [
            ('ERNESTO ARAÚJO CONVERSAR COM JAIR BOLSONARO DEPOIS ERNESTO ARAÚJO SAIR [PONTO]',
             'ERNESTO_ARAÚJO&FAMOSO CONVERSAR JAIR_BOLSONARO&FAMOSO DEPOIS ERNESTO_ARAÚJO&FAMOSO SAIR [PONTO]'),
            ('ABRAHAM WEINTRAUB CONVERSAR COM JAIR BOLSONARO [PONTO]',
            'ABRAHAM_WEINTRAUB&FAMOSO CONVERSAR JAIR_BOLSONARO&FAMOSO [PONTO]')
        ]
        length = 1000
        augmentation = FamososAugmentation(
            path=PATH_FAMOSOS, max_new_sentences=length)
        generated = augmentation.process(corpus)
        self.assertEqual(len(generated), len(corpus) + length)

    def test_max_data_augmentation(self):
        # verufuca o tamanho do corpus aumentado
        corpus = [(
            'ERNESTO ARAÚJO CONVERSAR COM JAIR BOLSONARO DEPOIS ERNESTO ARAÚJO SAIR [PONTO]',
            'ERNESTO_ARAÚJO&FAMOSO CONVERSAR JAIR_BOLSONARO&FAMOSO DEPOIS ERNESTO_ARAÚJO&FAMOSO SAIR [PONTO]'
        )]
        length = 0
        augmentation = FamososAugmentation(
            path=PATH_FAMOSOS, max_new_sentences=length)
        generated = augmentation.process(corpus)
        # 48 (tamanho da lista de famosos)
        self.assertEqual(len(generated), 54*53)

    def test_duplicates_data_augmentation(self):
        # verufuca o tamanho do corpus aumentado
        corpus = [(
            'ABRAHAM WEINTRAUB CONVERSAR COM JAIR BOLSONARO [PONTO]',
            'ABRAHAM_WEINTRAUB&FAMOSO CONVERSAR JAIR_BOLSONARO&FAMOSO [PONTO]',
        )]
        length = 0
        augmentation = FamososAugmentation(
            path=PATH_FAMOSOS, max_new_sentences=length)
        generated = augmentation.process(corpus)
        self.assertEqual(len(generated), len(set(generated)))

if __name__ == "__main__":
    unittest.main()

# PYTHONPATH=src/ python -m unittest tests/test_augmentation_famosos.py
