import unittest

from postprocess_be_agglutination import (
    build_repair_indexes,
    postprocess_line,
    split_invalid_be_token,
)


class TestPostprocessBEAgglutination(unittest.TestCase):
    def test_splits_only_invalid_wh_and_time_patterns(self):
        corpus_vocab = {"BUS", "TUESDAY"}
        glued_whitelist = {"BENOT"}

        fixed, _ = postprocess_line(
            "WHEREBEBUS BENOT TOMORROWBETUESDAY\n",
            corpus_vocab=corpus_vocab,
            glued_whitelist=glued_whitelist,
        )

        self.assertEqual(fixed, "WHERE BE BUS BENOT TOMORROW BE TUESDAY")

    def test_does_not_split_when_rest_not_in_vocab(self):
        corpus_vocab = {"BUS"}
        glued_whitelist = set()

        fixed, corrections = postprocess_line(
            "WHEREBEXYZ",
            corpus_vocab=corpus_vocab,
            glued_whitelist=glued_whitelist,
        )

        self.assertEqual(fixed, "WHEREBEXYZ")
        self.assertEqual(corrections, [])

    def test_does_not_split_when_token_exists_in_corpus(self):
        corpus_vocab = {"WHEREBEBUS", "BUS"}
        glued_whitelist = set()

        corr = split_invalid_be_token("WHEREBEBUS", corpus_vocab=corpus_vocab, glued_whitelist=glued_whitelist)
        self.assertIsNone(corr)

    def test_does_not_split_benot_or_bevery(self):
        corpus_vocab = {"VERY"}
        glued_whitelist = {"BENOT", "BEVERY"}

        fixed, _ = postprocess_line(
            "BENOT BEVERY",
            corpus_vocab=corpus_vocab,
            glued_whitelist=glued_whitelist,
        )

        self.assertEqual(fixed, "BENOT BEVERY")

    def test_does_not_split_prefix_be_without_rest(self):
        corpus_vocab = {"WHEREBE"}
        glued_whitelist = set()

        fixed, corrections = postprocess_line(
            "WHEREBE",
            corpus_vocab=corpus_vocab,
            glued_whitelist=glued_whitelist,
        )
        self.assertEqual(fixed, "WHEREBE")
        self.assertEqual(corrections, [])

    def test_does_not_split_single_letter_rest(self):
        corpus_vocab = {"M", "MONDAY"}
        glued_whitelist = set()

        fixed, corrections = postprocess_line(
            "TODAYBEM MONDAY",
            corpus_vocab=corpus_vocab,
            glued_whitelist=glued_whitelist,
        )

        self.assertEqual(fixed, "TODAYBEM MONDAY")
        self.assertEqual(corrections, [])

    def test_repairs_missing_first_char_in_rest(self):
        # WHEREBELEVATOR should become WHERE BE ELEVATOR if ELEVATOR is in vocab.
        corpus_vocab = {"ELEVATOR"}
        glued_whitelist = set()
        repair_indexes = build_repair_indexes(corpus_vocab)

        fixed, _ = postprocess_line(
            "WHEREBELEVATOR",
            corpus_vocab=corpus_vocab,
            glued_whitelist=glued_whitelist,
            repair_indexes=repair_indexes,
        )

        self.assertEqual(fixed, "WHERE BE ELEVATOR")

    def test_repairs_extra_first_char_in_rest(self):
        # WHEREBETKITCHEN -> WHERE BE KITCHEN (drop extra leading 'T')
        corpus_vocab = {"KITCHEN"}
        glued_whitelist = set()
        repair_indexes = build_repair_indexes(corpus_vocab)

        fixed, _ = postprocess_line(
            "WHEREBETKITCHEN",
            corpus_vocab=corpus_vocab,
            glued_whitelist=glued_whitelist,
            repair_indexes=repair_indexes,
        )

        self.assertEqual(fixed, "WHERE BE KITCHEN")


if __name__ == "__main__":
    unittest.main()

# Run (from repo root):
#   $env:PYTHONPATH='translation_pipeline/src'; python -m unittest translation_pipeline/tests/test_postprocess_be_agglutination.py
