import csv
import logging
import os

import datasets
import numpy as np
import torch

os.environ["TOKENIZERS_PARALLELISM"] = "false"

from artifact import get_artifact_directory, get_artifact_directory_by_hash
from elements.element import PipelineElement
from registry import register_element
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from utils import add_submodule_to_sys_path, resolve_relative_path

logger = logging.getLogger(__name__)


class TransformersResultsElement(PipelineElement):
    """Output CSV file with test results."""

    name = "transformers_results"
    dont_use_cache = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self._train_hash = kwargs["train_hash"]
            self._artifact_folder_path = get_artifact_directory()
            self._corpus_path = resolve_relative_path(kwargs["corpus_file"])

            self._train_link_folder = get_artifact_directory_by_hash(self._train_hash)
            self._checkpoint_path = os.path.realpath(
                os.path.join(self._train_link_folder, "Checkpoints")
            )
        except KeyError:
            raise ValueError("`results` requires a `corpus_file` parameter.")

        self._bleu = datasets.load_metric("bleu")
        self._sacrebleu = datasets.load_metric("sacrebleu")
        self._meteor = datasets.load_metric("meteor")

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._tokenizer = AutoTokenizer.from_pretrained(self._checkpoint_path)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(self._checkpoint_path)
        self._model.to(self._device)

        from strsimpy.levenshtein import Levenshtein

        self._levenshtein = Levenshtein()

        add_submodule_to_sys_path("vlibras-translate")
        from vlibras_translate import postprocessing

        self._postprocessor = postprocessing.Postprocessor()

    def translate(self, text, task="translate Portuguese to Gloss: "):
        # Tokenizer will automatically set [BOS] <text> [EOS]
        inputs = self._tokenizer(
            task + text,
            padding="max_length",
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )
        input_ids = inputs.input_ids.to(self._device)
        attention_mask = inputs.attention_mask.to(self._device)

        outputs = self._model.generate(
            input_ids,
            attention_mask=attention_mask,
            num_beams=4,
            num_return_sequences=1,
            do_sample=False,
            max_new_tokens=256,
        )
        # all special tokens including will be removed
        return self._tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]

    def _calculate_scores(self, gi_model, gi_gold):
        return (100 - self._levenshtein.distance(gi_model, gi_gold)) / 100

    def process(self, data=None):
        results_folder = os.path.join(self._artifact_folder_path, "Results")
        setname = self._corpus_path.split(os.path.sep)[-1].split(".")[0]
        results_csv_path = os.path.join(results_folder, f"{setname}.csv")

        os.makedirs(results_folder, exist_ok=True)

        predictions = []
        references = []

        with open(results_csv_path, "w") as results_csv_file:
            csv_writer = csv.writer(results_csv_file)
            csv_writer.writerow(
                [
                    "PT",
                    "GI (Padrão Ouro)",
                    "GI (Gerado pela rede)",
                    "Score",
                    "Resultado",
                ]
            )

            result_count = {
                "OK": 0,
                "Parcial": 0,
                "Incorreto": 0,
            }
            total_results = 0

            for pt, gi in data:
                gi_model = self._postprocessor.postprocess(self.translate(pt))
                gi_gold = self._postprocessor.postprocess(gi)

                predictions.append(gi_model)
                references.append(gi_gold)

                score = self._calculate_scores(gi_model, gi_gold)
                if score == 1:
                    result = "OK"
                elif score > 0.85:
                    result = "Parcial"
                else:
                    result = "Incorreto"
                result_count[result] += 1
                total_results += 1

                csv_writer.writerow(
                    [pt, gi_gold, gi_model, f"{round(score * 100, 2)}%", result]
                )
            csv_writer.writerow([""])
            for result in result_count:
                csv_writer.writerow(
                    [
                        f"{result}: {round(100 * result_count[result] / total_results, 2)}%"
                    ]
                )

            predictions = [p.split() for p in predictions]
            references = [[r.split()] for r in references]

            bleu_output = self._bleu.compute(
                predictions=predictions, references=references, max_order=4
            )
            sacrebleu_output = self._sacrebleu.compute(
                predictions=predictions, references=references
            )
            meteor_output = self._meteor.compute(
                predictions=predictions, references=references
            )

            eval_metrics = {
                "bleu4": round(np.mean(bleu_output["bleu"]), 3),
                "sacrebleu": round(sacrebleu_output["score"], 3),
                "meteor": round(meteor_output["meteor"], 3),
            }
            csv_writer.writerow([""])
            for metric in eval_metrics:
                csv_writer.writerow([f"{metric}: {eval_metrics[metric]}"])


# Add element to the registry.
register_element(TransformersResultsElement)
