import re
from typing import List, Dict


class ShapeTracker:
    """Tracks tensor/data shape changes using Python list perspective only.
    No math symbols (R, sum, sigma). Falls back to LLM prompt generation.
    """

    SHAPE_HINTS = {
        "tokenizer": {
            "input": ["str"],
            "operations": ["tokenizer"],
            "output": ["token_ids"],
            "analogy": "str.split() -> list of ints",
        },
        "encode": {
            "input": ["str_list", "N"],
            "operations": ["tokenizer", "embedding_lookup", "mean"],
            "output": ["matrix", "N", "768"],
            "analogy": "Dictionary.get() -> 768-length list",
        },
        "model.encode": {
            "input": ["str_list", "N"],
            "operations": ["tokenizer", "embedding_lookup", "mean"],
            "output": ["matrix", "N", "768"],
            "analogy": "Dictionary.get() -> 768-length list",
        },
        "AutoModel.from_pretrained": {
            "input": ["str"],
            "operations": ["load_weights"],
            "output": ["model_object"],
            "analogy": "loading a config dict from disk",
        },
        "last_hidden_state": {
            "input": ["batch", "seq", "hidden"],
            "operations": ["forward_pass"],
            "output": ["batch", "seq", "hidden"],
            "analogy": "3D list: [batch][seq][hidden]",
        },
        "nn.Linear": {
            "input": ["batch", "seq", "in_features"],
            "operations": ["matrix_multiply"],
            "output": ["batch", "seq", "out_features"],
            "analogy": "each inner list length changes from in -> out",
        },
        "nn.Conv2d": {
            "input": ["batch", "channels", "height", "width"],
            "operations": ["sliding_window"],
            "output": ["batch", "out_channels", "new_h", "new_w"],
            "analogy": "grid shrinks based on window size",
        },
        "mean": {
            "input": ["N", "dim"],
            "operations": ["average"],
            "output": ["dim"],
            "analogy": "average of N lists -> one list",
        },
        "sum": {
            "input": ["N", "dim"],
            "operations": ["add_all"],
            "output": ["dim"],
            "analogy": "summing N lists element-wise -> one list",
        },
        "softmax": {
            "input": ["batch", "seq", "classes"],
            "operations": ["normalize"],
            "output": ["batch", "seq", "classes"],
            "analogy": "each inner list values become probabilities summing to 1.0",
        },
        "reshape": {
            "input": ["..."],
            "operations": ["rearrange"],
            "output": ["target_shape"],
            "analogy": "repacking same items into different sized boxes",
        },
    }

    def track(self, blocks: List[Dict]) -> List[Dict]:
        results = []
        unknown_blocks = []

        for block in blocks:
            matched = False
            for keyword, hint in self.SHAPE_HINTS.items():
                if keyword in block.get("unknown_keywords", []) or keyword in block.get("code", ""):
                    results.append({
                        "block": block,
                        "input_shape": hint["input"],
                        "operations": hint["operations"],
                        "output_shape": hint["output"],
                        "code_analogy": hint["analogy"],
                        "source": "static_analysis",
                        "confidence": "high",
                    })
                    matched = True
                    break
            if not matched:
                unknown_blocks.append(block)

        if unknown_blocks:
            fallback_results = self.llm_infer_shapes(unknown_blocks)
            results.extend(fallback_results)

        return results

    def llm_infer_shapes(self, unknown_blocks: List[Dict]) -> List[Dict]:
        """When static analysis fails, generate an LLM prompt.
        In production, call LLM API. Here we return a structured placeholder
        that includes the prompt so the user can paste it into any LLM.
        """
        results = []
        for block in unknown_blocks:
            prompt = (
                "Below is a Python code block. Infer the tensor/array shape flow.\n"
                "Explain ONLY in Python list perspective. No math symbols (R, sum, sigma).\n\n"
                "Code:\n"
                f"{block['code']}"
            )
            results.append({
                "block": block,
                "shape_flow": f"[fallback] see generated prompt for LLM",
                "llm_prompt": prompt,
                "source": "llm_fallback",
                "confidence": "medium",
            })
        return results
