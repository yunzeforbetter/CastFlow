#!/usr/bin/env python3
"""Batch homology for origin-evolve. Connected components, one process.

stdin:  {"items":[{"id":"...","slug":"","skill":"","anchors":["method:Foo:Insert"]}]}
stdout: {"clusters":[["a","b"],["c"]]}
"""

from __future__ import print_function

import json
import sys


JACCARD_THRESHOLD = 0.5


def parse_anchors(raw):
    """Turn a frontmatter anchors value into a list of tokens."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return [p.strip() for p in text.split(",") if p.strip()]


def anchor_symbols(anchors):
    """Last ':' segment, lowercased. Empty input -> empty set."""
    symbols = set()
    for item in anchors or []:
        token = str(item).strip()
        if not token:
            continue
        symbols.add(token.split(":")[-1].lower())
    return symbols


def jaccard(a, b):
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return float(len(a & b)) / float(len(union))


def homologous(left, right):
    """True if two MEMORY-shaped dicts are homologous."""
    slug_a = str(left.get("slug") or "").strip()
    slug_b = str(right.get("slug") or "").strip()
    if slug_a and slug_a == slug_b:
        return True
    skill_a = str(left.get("skill") or "").strip()
    skill_b = str(right.get("skill") or "").strip()
    if skill_a and skill_b and skill_a == skill_b:
        return True
    set_a = anchor_symbols(left.get("anchors") or [])
    set_b = anchor_symbols(right.get("anchors") or [])
    if set_a and set_b and jaccard(set_a, set_b) >= JACCARD_THRESHOLD:
        return True
    return False


def cluster_items(items):
    """Union-find connected components. Singleton groups have size 1."""
    items = list(items or [])
    n = len(items)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            if homologous(items[i], items[j]):
                union(i, j)

    groups = {}
    order = []
    for i in range(n):
        root = find(i)
        if root not in groups:
            groups[root] = []
            order.append(root)
        ident = items[i].get("id")
        if ident is None or ident == "":
            ident = str(i)
        groups[root].append(ident)
    return {"clusters": [groups[k] for k in order]}


def main():
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    items = data.get("items") if isinstance(data, dict) else []
    result = cluster_items(items or [])
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
