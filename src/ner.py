"""NER detector backed by LiquidAI/LFM2.5-Encoder-350M-PII-Detector

Loading and inference follow the setup verified on LinuxONE (LFM25-PII-Hybrid-Summary.ipynb):
a pinned revision from a local Hugging Face cache, the official hybrid decode, and in the
"hybrid" mode the model on NNPA with every Lfm2ShortConv block on CPU.

Needs torch + transformers (+ torch-nnpa for "hybrid"); they are not project dependencies
and are only imported when [ner] is enabled.
"""

import importlib.util
import os
import re
import sys

from pathlib import Path
from types import MethodType, ModuleType, SimpleNamespace
from typing import Any, Literal

from loguru import logger

MODEL_ID = "LiquidAI/LFM2.5-Encoder-350M-PII-Detector"
# trust_remote_code runs the repo's Python code: only use this reviewed and verified revision
REVISION = "b8c9cf3d2d6ae52501b35a27ba46f271449c9ce2"
# The official decode truncates beyond this, so longer texts are rejected instead (fail closed)
MAX_TOKENS = 2048
# Synthetic only; used to check that the hybrid mode gives the same spans as CPU
SELF_CHECK_TEXT = "Synthetic test: Jane Example, email jane@example.com. 合成测试：姓名张敏，邮箱 zhang@example.com。"


class TextTooLongError(ValueError):
    pass


def short_label(entity_type: str) -> str:
    """identity.person_name -> PERSON_NAME (used in placeholders like [PERSON_NAME_1])"""
    return re.sub(r"[^A-Z0-9]+", "_", entity_type.rsplit(".", 1)[-1].upper()).strip("_") or "PII"


class LfmPiiDetector:
    """Matches privacy_engine.NerDetector: (text, entity types) -> [(start, end, label)]"""

    def __init__(self, cache_dir: Path, mode: Literal["cpu", "hybrid"] = "cpu", local_files_only: bool = True):
        import torch

        from huggingface_hub import hf_hub_download
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        if mode == "hybrid":
            import torch_nnpa  # noqa: F401  registers the nnpa device

        self._torch = torch
        torch.set_num_threads(max(1, min(4, len(os.sched_getaffinity(0)))))
        cache = str(cache_dir)
        hub = {"revision": REVISION, "cache_dir": cache, "local_files_only": local_files_only}

        helper = Path(hf_hub_download(MODEL_ID, "pii_hybrid_decode.py", **hub))
        hf_hub_download(MODEL_ID, "context_cued.py", **hub)
        self._decode = _load_module(helper)
        self._tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=False, **hub)
        model = AutoModelForTokenClassification.from_pretrained(
            MODEL_ID,
            code_revision=REVISION,
            trust_remote_code=True,
            use_safetensors=True,
            dtype=torch.float32,
            attn_implementation="eager",
            **hub,
        ).to("cpu").eval()
        self._model = _CheckedLogits(model)

        baseline = self._spans(SELF_CHECK_TEXT)
        if mode == "hybrid":
            model.nnpa()
            names = _shortconv_on_cpu(model)
            model.eval()
            # Never call model.nnpa() again after this: it would move the ShortConv blocks back
            if self._spans(SELF_CHECK_TEXT) != baseline:
                raise RuntimeError("NNPA hybrid mode gives different spans than CPU on the self-check")
            logger.info(f"NER model on NNPA, {len(names)} ShortConv block(s) on CPU; self-check passed")
        else:
            logger.info("NER model on CPU; self-check passed")

    def __call__(self, text: str, entities: list[str]) -> list[tuple[int, int, str]]:
        wanted = set(entities)
        if not wanted or not text:
            return []
        return [(s["start"], s["end"], short_label(s["type"])) for s in self._spans(text) if s["type"] in wanted]

    def _spans(self, text: str) -> list[dict[str, Any]]:
        tokens = len(self._tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"])
        if tokens > MAX_TOKENS:
            raise TextTooLongError(f"text has {tokens} tokens, at most {MAX_TOKENS} are supported")
        with self._torch.inference_mode():
            raw = self._decode.model_spans(text, self._tokenizer, self._model)
        return self._decode.hybrid_spans(text, raw)


class _CheckedLogits:
    """What pii_hybrid_decode.model_spans needs from the model; refuses NaN / Inf logits"""

    def __init__(self, model):
        self.model = model
        self.config = model.config

    @property
    def device(self):
        return self.model.device

    def __call__(self, **inputs):
        import torch

        logits = self.model(**inputs).logits.detach().float().to("cpu")
        if not torch.isfinite(logits).all().item():
            raise RuntimeError("NER model returned NaN / Inf logits")
        return SimpleNamespace(logits=logits)


def _load_module(path: Path) -> ModuleType:
    # pii_hybrid_decode imports context_cued from the same dir at call time
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _shortconv_on_cpu(model) -> list[str]:
    """NNPA's Conv1d returns a wrong shape ([1,1024,3,17] instead of [1,1024,17]), so every
    Lfm2ShortConv block (incl. its in / out projections) runs on CPU; the rest stays on NNPA"""
    names = []
    for name, module in model.named_modules():
        if type(module).__name__ != "Lfm2ShortConv":
            continue
        devices = {str(p.device).split(":")[0] for p in module.parameters()}
        if devices != {"nnpa"}:
            raise RuntimeError(f"{name}: expected parameters on nnpa, got {devices}")
        original = module.forward
        module.to("cpu")
        module.forward = MethodType(_cpu_forward(original), module)
        names.append(name)
    if not names:
        raise RuntimeError("No Lfm2ShortConv modules found; the NNPA hybrid workaround does not apply")
    return names


def _cpu_forward(original):
    import torch

    def forward(self, hidden_states, *args, **kwargs):
        if not torch.is_inference_mode_enabled():
            raise RuntimeError("The ShortConv CPU fallback is inference only")
        if kwargs.get("past_key_values") is not None or (args and args[0] is not None):
            raise RuntimeError("The ShortConv CPU fallback doesn't support a cache")
        result = original(hidden_states.to("cpu"), *_to_cpu(args), **_to_cpu(kwargs))
        if not isinstance(result, torch.Tensor) or tuple(result.shape) != tuple(hidden_states.shape):
            raise RuntimeError("CPU ShortConv did not preserve its input shape")
        return result.to(hidden_states.device)

    return forward


def _to_cpu(value):
    import torch

    if isinstance(value, torch.Tensor):
        return value.to("cpu")
    if isinstance(value, dict):
        return {k: _to_cpu(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return type(value)(_to_cpu(v) for v in value)
    return value


def warn_if_low_memory(min_gib: float = 4.0) -> None:
    """The notebook's conservative threshold before loading the model (not a measured minimum)"""
    try:
        meminfo = Path("/proc/meminfo").read_text()
    except OSError:
        return
    match = re.search(r"^MemAvailable:\s+(\d+) kB", meminfo, re.M)
    if match and int(match.group(1)) / 1024**2 < min_gib:
        logger.warning(f"Less than {min_gib:.0f} GiB memory available; loading the NER model may fail")
