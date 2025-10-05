#!/usr/bin/env python3
"""Report example POS changes between two JSONL extractions."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, Mapping, Set


ExampleMap = Dict[str, Dict[str, Set[str]]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two JSONL dumps and report how many example sentences "
            "changed the part-of-speech they are attached to for selected "
            "words."
        )
    )
    parser.add_argument("--old", required=True, help="JSONL file with strict boundary disabled")
    parser.add_argument("--new", required=True, help="JSONL file with strict boundary enabled")
    parser.add_argument("--words", required=True, help="Path to newline-delimited word list")
    return parser.parse_args()


def _load_word_list(path: Path) -> list[str]:
    words: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            word = line.strip()
            if word:
                words.append(word)
    return words


def _load_examples(path: Path) -> ExampleMap:
    mapping: ExampleMap = defaultdict(lambda: defaultdict(set))
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            word = data.get("word") or ""
            pos = data.get("pos") or ""
            if not word or not pos:
                continue
            for sense in data.get("senses", []) or []:
                examples: Iterable[Mapping[str, str]] = sense.get("examples", []) or []
                for example in examples:
                    text = (example.get("text") or "").strip()
                    if not text:
                        continue
                    mapping[word][text].add(pos)
    return mapping


def _count_changes(word: str, old_map: ExampleMap, new_map: ExampleMap) -> tuple[int, int, int]:
    old_examples = old_map.get(word, {})
    new_examples = new_map.get(word, {})
    changed = 0
    all_texts = set(old_examples) | set(new_examples)
    for text in all_texts:
        if old_examples.get(text, set()) != new_examples.get(text, set()):
            changed += 1
    return changed, len(old_examples), len(new_examples)


def main() -> None:
    args = parse_args()
    old_path = Path(args.old)
    new_path = Path(args.new)
    words_path = Path(args.words)

    words = _load_word_list(words_path)
    old_map = _load_examples(old_path)
    new_map = _load_examples(new_path)

    header = f"{'Word':<10}{'Changed':>10}{'OldUnique':>12}{'NewUnique':>12}"
    print(header)
    print("-" * len(header))
    for word in words:
        changed, old_total, new_total = _count_changes(word, old_map, new_map)
        print(f"{word:<10}{changed:>10}{old_total:>12}{new_total:>12}")


if __name__ == "__main__":
    main()
