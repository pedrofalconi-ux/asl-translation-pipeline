import unittest
import csv

from elements.augmentation_places import PlacesAugmentation

# lista com todos os places
PATH_PLACES = 'data/augmentation/lugares.csv'

class TestPlacesAugmentation(unittest.TestCase):
    def test_constructor(self):
        # verifica se a classe foi inicializada corretamente
        try:
            _ = PlacesAugmentation(path=PATH_PLACES, max_new_sentences=1)
        except Exception as e:
            self.fail(e)

    def test_data_without_augmentation(self):
        # verifica se o tamanho do corpus eh modificado sem ter nenhum dado referente a places para ser aumentado
        corpus = [
            ('COMO PODER PASSAR TEMPO [INTERROGAÇÃO]', 'COMO PODER&POSSIBILIDADE PASSAR&TEMPO [INTERROGAÇÃO]'),
            ('COMO PODER AGRADECER [INTERROGAÇÃO]', 'COMO PODER&POSSIBILIDADE AGRADECER ELE [INTERROGAÇÃO]')
        ]
        augmentation = PlacesAugmentation(
            path=PATH_PLACES, max_new_sentences=50)
        generated = augmentation.process(corpus)
        self.assertEqual(len(generated), len(corpus))

    def test_len_data_augmentation(self):
        # verifica o tamanho de frases geradas a partir de um corpus com dados de places
        corpus = [
            ('SAIR BRASIL PARA CHINA VOLTAR PARA BRASIL [PONTO]', 'SAIR BRASIL&PAÍS PARA CHINA&PAÍS VOLTAR BRASIL&PAÍS [PONTO]'),
            ('CHEGAR ONTEM ALEMANHA VIAJAR PARA ARGENTINA [PONTO]', 'CHEGAR ONTEM ALEMANHA&PAÍS VIAJAR PARA ARGENTINA&PAÍS [PONTO]')
        ]
        length = 1000
        augmentation = PlacesAugmentation(
            path=PATH_PLACES, max_new_sentences=length)
        generated = augmentation.process(corpus)
        self.assertEqual(len(generated), len(corpus) + length)

    def test_max_data_augmentation(self):
        # verufuca o tamanho do corpus aumentado
        corpus = [(
            'CHEGAR ONTEM ALEMANHA VIAJAR PARA ARGENTINA [PONTO]',
            'CHEGAR ONTEM ALEMANHA&PAÍS VIAJAR PARA ARGENTINA&PAÍS [PONTO]'
        )]
        length = 0
        augmentation = PlacesAugmentation(
            path=PATH_PLACES, max_new_sentences=length)
        generated = augmentation.process(corpus)
        # 48 (tamanho da lista de lugares)
        self.assertEqual(len(generated), 48*47)

    def test_duplicates_data_augmentation(self):
        # verufuca o tamanho do corpus aumentado
        corpus = [
            ('CHEGAR ONTEM ALEMANHA VIAJAR PARA ARGENTINA [PONTO]',
             'CHEGAR ONTEM ALEMANHA&PAÍS VIAJAR PARA ARGENTINA&PAÍS [PONTO]')
        ]
        length = 0
        augmentation = PlacesAugmentation(
            path=PATH_PLACES, max_new_sentences=length)
        generated = augmentation.process(corpus)
        self.assertEqual(len(generated), len(set(generated)))

if __name__ == "__main__":
    unittest.main()

# PYTHONPATH=src/ python -m unittest tests/test_augmentation_places.py
