"""NER detector backed by LiquidAI/LFM2.5-Encoder-350M-PII-Detector

Needs torch + transformers, which are not project dependencies: they are only imported when
[ner] model_path is configured.
"""

import importlib.util
import re
import sys

from pathlib import Path
from types import ModuleType

# The official decode (pii_hybrid_decode.predict) silently truncates at 2048 tokens, so long
# texts are split into overlapping token windows first
WINDOW_TOKENS = 1800
OVERLAP_TOKENS = 200


def short_label(entity_type: str) -> str:
    """identity.person_name -> PERSON_NAME (used in placeholders like [PERSON_NAME_1])"""
    return re.sub(r"[^A-Z0-9]+", "_", entity_type.rsplit(".", 1)[-1].upper()).strip("_") or "PII"


def token_windows(offsets: list[tuple[int, int]], size: int, overlap: int) -> list[tuple[int, int]]:
    """(start, end) char ranges covering all tokens, `size` tokens each, overlapping by `overlap`"""
    windows = []
    for i in range(0, len(offsets), size - overlap):
        chunk = offsets[i : i + size]
        windows.append((chunk[0][0], chunk[-1][1]))
        if i + size >= len(offsets):
            break
    return windows


def _load_module(model_dir: Path, name: str) -> ModuleType:
    # pii_hybrid_decode imports context_cued from the same dir at call time
    sys.path.insert(0, str(model_dir))
    spec = importlib.util.spec_from_file_location(name, model_dir / f"{name}.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"{name}.py not found in {model_dir}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LfmPiiDetector:
    """Matches privacy_engine.NerDetector: (text, entity types) -> [(start, end, label)]"""

    def __init__(self, model_dir: Path):
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        # trust_remote_code runs the model repo's Python code: only load a reviewed local copy
        self._tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True, local_files_only=True)
        self._model = AutoModelForTokenClassification.from_pretrained(
            model_dir, trust_remote_code=True, local_files_only=True
        ).eval()
        self._decode = _load_module(model_dir, "pii_hybrid_decode")

    def __call__(self, text: str, entities: list[str]) -> list[tuple[int, int, str]]:
        wanted = set(entities)
        if not wanted or not text:
            return []
        offsets = self._tokenizer(text, return_offsets_mapping=True, add_special_tokens=False)["offset_mapping"]
        found: set[tuple[int, int, str]] = set()
        for start, end in token_windows(offsets, WINDOW_TOKENS, OVERLAP_TOKENS):
            for span in self._decode.predict(text[start:end], self._tokenizer, self._model):
                if span["type"] in wanted:
                    found.add((start + span["start"], start + span["end"], short_label(span["type"])))
        # Duplicates from overlapping windows are removed above; partial overlaps are resolved by the engine
        return sorted(found)
