import csv
import os

import torch

os.environ["TOKENIZERS_PARALLELISM"] = "false"

from artifact import get_artifact_directory, get_artifact_directory_by_hash
from elements.element import PipelineElement
from registry import register_element
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from utils import add_submodule_to_sys_path, resolve_relative_path


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
            self._cfg_path = resolve_relative_path(kwargs["parameters"])

            self._train_link_folder = get_artifact_directory_by_hash(self._train_hash)
            self._checkpoint_path = os.path.realpath(
                os.path.join(self._train_link_folder, "Checkpoints")
            )
        except KeyError:
            raise ValueError("`results` requires a `corpus_file` parameter.")

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._tokenizer = AutoTokenizer.from_pretrained(self._checkpoint_path)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(self._checkpoint_path)

        from strsimpy.levenshtein import Levenshtein

        self._levenshtein = Levenshtein()

        add_submodule_to_sys_path("vlibras-translate")
        from vlibras_translate import postprocessing

        self._postprocessor = postprocessing.Postprocessor()

    def translate(self, text):
        # Tokenizer will automatically set [BOS] <text> [EOS]
        inputs = self._tokenizer(
            text,
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
            num_beams=1,
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


# Add element to the registry.
register_element(TransformersResultsElement)
