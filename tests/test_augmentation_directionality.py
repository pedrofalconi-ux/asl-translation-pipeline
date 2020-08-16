import unittest
import csv
from elements.augmentation_directionality import Directionality_Augmentation

class TestDirectionalityAugmentation(unittest.TestCase):
    def test_constructor(self):
        '''Checks if the class has been initialized correctly'''
        try:
            _ = Directionality_Augmentation(max_new_sentences = 2)
        except Exception as e:
            self.fail(e)

    def test_data_data_augmentation(self):
        '''Checks if augmentation works normally'''

        corpus = [('ELA ME DAR VÁRIOS LIVRO [PONTO]','DAR_3S_2S VÁRIOS LIVRO [PONTO]')]
        length = 2
        augmentation = Directionality_Augmentation(max_new_sentences = length)
        generated = augmentation.process(corpus)
        self.assertEqual(len(generated),len(corpus) + length)

if __name__ == "__main__":
    unittest.main()

# PYTHONPATH=src/ python -m unittest tests/test_augmentation_directionality.py