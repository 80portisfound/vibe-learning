import ast
import re
from typing import List, Dict


class CodeScanner:
    """Extracts unknown code blocks and tags confusion_score.
    Ignores basic syntax (for/if/class), focuses on domain keywords.
    """

    BASIC_KEYWORDS = {
        "for", "if", "class", "def", "return", "import", "from", "as",
        "with", "try", "except", "raise", "pass", "break", "continue",
        "in", "is", "not", "and", "or", "True", "False", "None", "self",
        "elif", "else", "finally", "lambda", "yield", "async", "await",
        "global", "nonlocal", "assert", "del",
    }

    DOMAIN_KEYWORDS = {
        "encoder", "decoder", "hidden_state", "embedding", "tokenizer",
        "attention", "dropout", "batch_norm", "linear", "relu", "softmax",
        "cross_entropy", "gradient", "optimizer", "scheduler", "tensor",
        "numpy", "torch", "keras", "sklearn", "chroma", "vector", "index",
        "query", "retrieve", "generate", "token", "vocab", "mask", "padding",
        "sequence", "layer", "head", "dim", "shape", "mean", "sum", "matmul",
        "transpose", "concat", "split", "lstm", "gru", "conv", "pool",
        "flatten", "dense", "bert", "gpt", "transformer", "autoencoder",
        "backbone", "checkpoint", "inference", "train", "eval", "dataset",
        "dataloader", "collate", "sampler", "epoch", "batch", "loss",
        "accuracy", "precision", "recall", "f1", "auc", "roc",
    }

    def scan(self, code: str, file_path: str = "unknown") -> List[Dict]:
        blocks = []
        # If code looks like a diff, strip + prefixes first
        cleaned = self._clean_diff(code)
        try:
            tree = ast.parse(cleaned)
        except SyntaxError:
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                block_info = self._analyze_call(node, cleaned, file_path)
                if block_info:
                    blocks.append(block_info)

        return blocks

    def _clean_diff(self, code: str) -> str:
        lines = code.splitlines()
        cleaned_lines = []
        for line in lines:
            if line.startswith("+") and not line.startswith("+++"):
                cleaned_lines.append(line[1:])
            elif not line.startswith("-") and not line.startswith("@"):
                cleaned_lines.append(line)
        # Remove common leading whitespace to fix indentation errors
        nonempty = [ln for ln in cleaned_lines if ln.strip()]
        if not nonempty:
            return ""
        min_indent = min(len(ln) - len(ln.lstrip()) for ln in nonempty)
        dedented = [ln[min_indent:] if ln.strip() else ln for ln in cleaned_lines]
        return "\n".join(dedented)

    def _analyze_call(self, node: ast.Call, full_code: str, file_path: str) -> Dict:
        line = getattr(node, "lineno", 0)
        col = getattr(node, "col_offset", 0)
        snippet = self._extract_snippet(full_code, line)
        names = self._collect_names(node)
        unknowns = [n for n in names if n not in self.BASIC_KEYWORDS and n in self.DOMAIN_KEYWORDS]
        if not unknowns:
            return None

        confusion_score = min(len(unknowns) * 10, 100)
        block_type = self._infer_block_type(unknowns)

        return {
            "file": file_path,
            "line": line,
            "col": col,
            "code": snippet,
            "block_type": block_type,
            "unknown_keywords": unknowns,
            "confusion_score": confusion_score,
        }

    def _collect_names(self, node: ast.AST) -> List[str]:
        names = []
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                names.append(child.id)
            elif isinstance(child, ast.Attribute):
                names.append(child.attr)
        return list(set(names))

    def _extract_snippet(self, code: str, line: int, context: int = 3) -> str:
        lines = code.splitlines()
        start = max(0, line - context - 1)
        end = min(len(lines), line + context)
        return "\n".join(lines[start:end])

    def _infer_block_type(self, unknowns: List[str]) -> str:
        type_map = {
            "embedding": "Embedding",
            "tokenizer": "Tokenizer",
            "encoder": "Encoder",
            "decoder": "Decoder",
            "attention": "Attention",
            "linear": "Linear",
            "conv": "Convolution",
            "lstm": "LSTM",
            "gru": "GRU",
            "dropout": "Regularization",
            "batch_norm": "Normalization",
            "relu": "Activation",
            "softmax": "Activation",
            "optimizer": "Optimizer",
            "loss": "Loss",
            "chroma": "VectorDB",
            "query": "Retrieval",
            "index": "Indexing",
        }
        for kw in unknowns:
            if kw in type_map:
                return type_map[kw]
        return "Unknown"
