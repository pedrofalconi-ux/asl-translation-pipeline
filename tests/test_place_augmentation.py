import unittest
# import sys
# import os

# sys.path.append(os.path.abspath(os.path.join('src')))

from src.elements.place_augmentation import PlaceAugmentation

corpus = [
    ('VIAJEI PARA RECIFE ONTEM.', 'VIAJAR RECIFE&CIDADE ONTEM [PONTO]'),
    ('VIAJEI PARA ITÁLIA ONTEM CHEGUEI HOJE NO BRASIL.',
     'VIAJAR ITÁLIA&PAÍS ONTEM CHEGUAR HOJE BRASIL&PAÍS [PONTO]')
]

class TestPlaceAugmentation(unittest.TestCase):
    def test_constructor(self):
        try:
            # check if everything is ok  in PlaceAugmentation
            _ = PlaceAugmentation(path='./data/lugares.csv', max_new_sentences=1)
        except Exception as e:
            self.fail(e)

    def test_len_data_augmentation(self):
        # check if lenght passed by args is the same of output generated
        length = 10
        augmentation = PlaceAugmentation(
            path='./data/lugares.csv', max_new_sentences=length)
        generated = augmentation.process(corpus)
        self.assertEqual(length, abs(len(generated) - len(corpus)))

    def test_data_augmentation(self):
        # check expected corpus
        augmentation = PlaceAugmentation(
            path='./data/lugares.csv', max_new_sentences=-1) # define a MAX sample (in order to get all possible augmentation)
        generated = augmentation.process(corpus)
        # remove original corpus from generated  (in the pipeline this is not necessary) and selected first 5 phrases
        # we need sort the data generated in order to check if the match is correct
        generated = sorted(set(generated)-set(corpus))[:5]
        self.assertEqual(
            generated[0], ('VIAJEI PARA ACRE ONTEM CHEGUEI HOJE NO BRASIL.',
                           'VIAJAR ACRE&ESTADO ONTEM CHEGUAR HOJE BRASIL&PAÍS [PONTO]')
        )
        self.assertEqual(
            generated[1], ('VIAJEI PARA ACRE ONTEM.',
                           'VIAJAR ACRE&ESTADO ONTEM [PONTO]')
        )
        self.assertEqual(
            generated[2], ('VIAJEI PARA ALAGOAS ONTEM CHEGUEI HOJE NO BRASIL.',
                           'VIAJAR ALAGOAS&ESTADO ONTEM CHEGUAR HOJE BRASIL&PAÍS [PONTO]')
        )
        self.assertEqual(
            generated[3], ('VIAJEI PARA ALAGOAS ONTEM.',
                           'VIAJAR ALAGOAS&ESTADO ONTEM [PONTO]')
        )
        self.assertEqual(
            generated[4], ('VIAJEI PARA ALEMANHA ONTEM CHEGUEI HOJE NO BRASIL.',
                           'VIAJAR ALEMANHA&PAÍS ONTEM CHEGUAR HOJE BRASIL&PAÍS [PONTO]')
        )

if __name__ == "__main__":
    unittest.main()

# python -m unittest src/tests/test_place_augmentation.py
