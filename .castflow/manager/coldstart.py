"""Ephemeral cold-start skeleton: package atoms, one dependency tree, no ledger.

Facts are type-name references (`using` is not an edge). Atoms are packages the
repo already has (GameLogic Modules/<Feature>, tools/<Name>, asmdef, vendor).
A bottom-up merge of that package graph cuts one tree; `--target 8` and
`--target 30` are two layers of the same tree. Roles (tool / engine / feature /
adapter / bootstrap) are rules, not a second clustering. One selected node is
one skill. Clusters of files are not modules and are not skills.

This is not the deleted `scan.py` / `manager.py scan` / `/api/scan` entry,
and it never writes STATE.yaml, INVENTORY.md, GRAPH.md, or a knowledge graph.
"""

from __future__ import print_function

import copy
import os
import re
import shutil

from installer.validate import validate_skill_dir

from .config import load_config, normalize_language

SCRIPT_EXTS = frozenset((
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts",
    ".vue", ".svelte", ".astro",
    ".py", ".pyw", ".pyi",
    ".cs", ".csx", ".fs", ".fsx", ".fsi", ".vb",
    ".java", ".kt", ".kts", ".scala", ".sc", ".groovy", ".clj", ".cljs", ".cljc",
    ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".m", ".mm",
    ".go", ".rs", ".swift",
    ".dart", ".php", ".rb", ".rake", ".lua",
    ".ex", ".exs", ".hs", ".ml", ".zig", ".nim", ".pl", ".r", ".jl",
    ".sh", ".ps1", ".sql", ".proto", ".sol",
))

# Path segment, compared case-insensitively. Whole subtree is out of scope.
SKIP_SEGMENTS = frozenset((
    "library", "packages", "obj", "temp", "node_modules", "vendor", ".git",
    "castflow", ".castflow", ".castflow-runtime",
    ".claude", ".agents", ".cursor", ".grok",
    "packagecache",
))

LOW_PRIORITY_SEGMENTS = frozenset((
    "util", "utils", "common", "shared", "test", "tests", "editor", "editors",
))

# Default checkbox layer. Coarser and finer targets are cuts of one merge list.
DEFAULT_TARGET = 16
ROLES = frozenset(("tool", "engine", "feature", "adapter", "bootstrap"))
_ROLE_ORDER = {"feature": 0, "engine": 1, "tool": 2, "adapter": 3, "bootstrap": 4}

# Leading directories that are not a package boundary.
_GENERIC_DIR = frozenset((
    "assets", "scripts", "script", "src", "source",
))
_VENDOR_SEGMENTS = frozenset((
    "thirdparty", "third-party", "amplify", "amplifyshadereditor",
    "spine", "dotween", "odin", "plugins",
))
_TOOL_IDS = frozenset((
    "util", "utils", "common", "shared",
))
# Large adapter/engine/tool packages stay visible instead of swallowing each other.
_PIN_FILES = 80

LEDGER_NAMES = frozenset((
    "STATE.yaml", "INVENTORY.md", "GRAPH.md", "PREFLIGHT.md", "CLAIMS.yaml",
    "knowledge-graph.json",
))

_CS_DECL = re.compile(
    r"\b(?:class|struct|interface|enum|record|delegate)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)"
)
_PY_DECL = re.compile(
    r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.M,
)
_IDENT = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\b")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT = re.compile(r"//.*?$", re.M)
_PY_COMMENT = re.compile(r"#.*?$", re.M)
_STRING = re.compile(
    r'@"(?:""|[^"])*"|"(?:\\.|[^"\\])*"'
    r"|'(?:\\.|[^'\\])*'"
)
_USING_LINE = re.compile(r"^\s*using\b")
_PROTOCOL = re.compile(r"^(Send|Handle|OnGc|Cg)[A-Z]")
_EMPTY_ENUM = re.compile(
    r"\benum\s+([A-Za-z_][A-Za-z0-9_]*)\b[^{;]*\{\s*\}",
    re.S,
)
_UI_PATH = re.compile(
    r"(^|[\\/])(UI|View|Window|Panel|Presenter|Flow|SceneFlow)([\\/]|$)",
    re.I,
)
_UI_TYPE = re.compile(
    r"(UI|View|Window|Panel|Presenter|Flow|SceneFlow)",
)
_ENTRY_DECL = re.compile(
    r"(Window|Panel|View|Page|Dialog|Flow|Presenter)$"
)


def _posix(path):
    return path.replace("\\", "/")


def _segments(path):
    return [part for part in re.split(r"[\\/]", path) if part and part != "."]


def is_excluded_path(path):
    """True when any path segment is a CastFlow, Library, Packages, or asset tree."""
    for part in _segments(path):
        if part.lower() in SKIP_SEGMENTS:
            return True
    return False


def is_low_priority_path(path):
    for part in _segments(path):
        if part.lower() in LOW_PRIORITY_SEGMENTS:
            return True
    return False


def _kebab(name):
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name or "")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text or "module"


def _clean_line(line, ext, in_block):
    """Return (cleaned line, still_in_block). Line count stays aligned with the file."""
    if ext in (".py", ".pyw", ".pyi"):
        return _STRING.sub('""', _PY_COMMENT.sub("", line)), False
    out = []
    i = 0
    while i < len(line):
        if in_block:
            end = line.find("*/", i)
            if end < 0:
                return "".join(out), True
            i = end + 2
            in_block = False
            continue
        if line.startswith("/*", i):
            end = line.find("*/", i + 2)
            if end < 0:
                return "".join(out), True
            i = end + 2
            continue
        if line.startswith("//", i):
            break
        out.append(line[i])
        i += 1
    return _STRING.sub('""', "".join(out)), False


def _decl_names(text, ext):
    if ext in (".py", ".pyw", ".pyi"):
        return _PY_DECL.findall(text)
    return _CS_DECL.findall(text)


def empty_enum_names(text, ext):
    if ext not in (".cs", ".csx"):
        return set()
    cleaned = []
    in_block = False
    for line in (text or "").splitlines():
        piece, in_block = _clean_line(line, ext, in_block)
        cleaned.append(piece)
    return set(_EMPTY_ENUM.findall("\n".join(cleaned)))


def parse_script(text, ext):
    """Return (declared type names, per-line reference idents, original lines).

    Reference idents on a declaration line omit the name being declared.
    `using` lines contribute nothing. Comments and strings are not edges.
    """
    decls = []
    seen = set()
    line_refs = []
    original = (text or "").splitlines()
    in_block = False
    for line in original:
        cleaned, in_block = _clean_line(line, ext, in_block)
        for name in _decl_names(cleaned, ext):
            if name not in seen:
                seen.add(name)
                decls.append(name)
        if _USING_LINE.match(cleaned):
            line_refs.append([])
            continue
        idents = _IDENT.findall(cleaned)
        declared_here = set(_decl_names(cleaned, ext))
        if declared_here:
            idents = [ident for ident in idents if ident not in declared_here]
        line_refs.append(idents)
    return decls, line_refs, original


def _dir_parts(path):
    parts = _segments(path)
    if parts and "." in os.path.basename(parts[-1]):
        parts = parts[:-1]
    return parts


def _file_has_entry(path, decls):
    """UI/Flow path or an entry-shaped type. Protocol Send/Handle names are not entries."""
    if _UI_PATH.search(path or ""):
        return True
    for name in decls or []:
        if _PROTOCOL.match(name):
            continue
        if _ENTRY_DECL.search(name):
            return True
    return False


def _editor_or_test(path):
    for part in _segments(path):
        if part.lower() in ("editor", "editors", "test", "tests"):
            return True
    return False


def _vendorish(path):
    for part in _segments(path):
        low = part.lower()
        if low in _VENDOR_SEGMENTS or "amplify" in low:
            return True
    return False


def _prepare_asmdefs(files, asmdef_dirs):
    """Return (longest-first asmdef list, dirs that contain GameLogic Modules)."""
    indexed = []
    for item in asmdef_dirs or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            directory, stem = item[0], item[1]
        else:
            directory = item
            stem = os.path.splitext(os.path.basename(str(item)))[0]
        directory = _posix(str(directory)).strip("/")
        if not directory or is_excluded_path(directory):
            continue
        indexed.append((directory, stem))
    indexed.sort(key=lambda pair: (-len(pair[0]), pair[0]))
    has_modules = set()
    for item in files:
        low = [part.lower() for part in _dir_parts(item["path"])]
        if "gamelogic" not in low:
            continue
        if "modules" not in low and "module" not in low:
            continue
        path = item["path"]
        for directory, _stem in indexed:
            prefix = directory + "/"
            if path.startswith(prefix):
                has_modules.add(directory)
                break
    return indexed, has_modules


def _deepest_asmdef(path, indexed):
    for directory, stem in indexed:
        if path.startswith(directory + "/"):
            return directory, stem
    return None


def _fallback_atom(parts):
    low = [part.lower() for part in parts]
    for broad in ("framework", "extensions", "rendering", "gamelogic"):
        if broad in low:
            index = low.index(broad)
            nxt = parts[index + 1] if index + 1 < len(parts) else parts[index]
            return _kebab(broad + "-" + nxt)
    dirs = list(parts)
    while dirs and dirs[0].lower() in _GENERIC_DIR:
        dirs.pop(0)
    if not dirs:
        return "root"
    return _kebab(dirs[0])


def _atom_identity(path, indexed, has_modules):
    """Package atom for one script. Not a file and not a two-segment path bucket."""
    parts = _dir_parts(path)
    low = [part.lower() for part in parts]
    if not parts:
        return "root", "path"
    if any(seg == "tuyoo.protocol" or seg.endswith(".protocol") for seg in low):
        return "protocol", "adapter-path"
    if "tools" in low and "protocol" in low:
        return "protocol", "adapter-path"
    if any("amplify" in seg for seg in low):
        return "amplify-shader-editor", "adapter-path"
    for index, seg in enumerate(low):
        if seg in ("thirdparty", "third-party"):
            if index + 1 < len(parts):
                return "vendor-" + _kebab(parts[index + 1]), "adapter-path"
            return "vendor", "adapter-path"
    if "gamelogic" in low:
        for index, seg in enumerate(low):
            if seg in ("modules", "module") and index + 1 < len(parts):
                return _kebab(parts[index + 1]), "feature-dir"
    for index, seg in enumerate(low):
        if seg == "tools" and index + 1 < len(parts):
            return "tools-" + _kebab(parts[index + 1]), "tool-path"
    found = _deepest_asmdef(path, indexed)
    if found is not None:
        directory, stem = found
        atom_id = _kebab(stem)
        if directory in has_modules:
            return atom_id + "-core", "residue"
        return atom_id, "asmdef"
    return _fallback_atom(parts), "path"


_KIND_RANK = {
    "path": 0,
    "asmdef": 1,
    "residue": 1,
    "tool-path": 2,
    "mechanism": 3,
    "feature-dir": 4,
    "adapter-path": 4,
}

_VIEW_SEGS = frozenset(("ui", "view", "views"))
_SHARED_VIEW_LEAVES = frozenset(("common", "shared", "util", "utils"))
_MECHANISM_LEAVES = frozenset((
    "components", "component", "event", "events", "ugui", "widget", "widgets",
    "core", "base", "contract", "contracts", "host", "internal",
))
_GENERIC_DECLS = frozenset((
    "object", "string", "ui", "item", "config", "keyvaluepair", "type", "text",
    "log", "time", "color", "rect", "format", "int", "float", "bool", "boolean",
    "list", "dictionary", "action", "task", "event", "args", "data", "info",
    "base", "context",
))


def _feature_ids(files, indexed, has_modules):
    found = set()
    for item in files:
        atom_id, kind = _atom_identity(item["path"], indexed, has_modules)
        if kind == "feature-dir":
            found.add(atom_id)
    return found


def _view_assignment(path, feature_ids):
    """Attach Feature/UI/<Feature> to that feature. Shared leaves stay put.

    A UI/View directory that is the host itself (contracts, components, or
    files sitting directly in it under a framework tree) becomes one mechanism
    atom instead of riding inside the grab-bag parent.
    """
    parts = _dir_parts(path)
    low = [part.lower() for part in parts]
    if "modules" in low or "module" in low:
        return None
    for index, seg in enumerate(low):
        if seg not in _VIEW_SEGS:
            continue
        previous = low[index - 1] if index else ""
        nested = previous not in _GENERIC_DIR and previous not in ("",)
        if index + 1 < len(parts):
            leaf = _kebab(parts[index + 1])
            if leaf in _SHARED_VIEW_LEAVES:
                return None
            if leaf in feature_ids:
                return leaf, "feature-dir"
            if nested and (leaf in _MECHANISM_LEAVES or "framework" in low):
                return "ui-mechanism", "mechanism"
            return None
        if nested:
            return "ui-mechanism", "mechanism"
        return None
    return None


def _parse_files(sources):
    files = []
    for raw_path in sorted(sources):
        rel = _posix(raw_path).lstrip("/")
        if is_excluded_path(rel):
            continue
        ext = os.path.splitext(rel)[1].lower()
        if ext not in SCRIPT_EXTS:
            continue
        decls, line_refs, lines = parse_script(sources[raw_path], ext)
        files.append({
            "path": rel,
            "ext": ext,
            "decls": decls,
            "line_refs": line_refs,
            "lines": lines,
            "empty_enums": empty_enum_names(sources[raw_path], ext),
        })
    return files


def _build_atoms(files, asmdef_dirs):
    """Group scripts into packages. Edge weight is distinct declared types."""
    indexed, has_modules = _prepare_asmdefs(files, asmdef_dirs)
    feature_ids = _feature_ids(files, indexed, has_modules)
    grouped = {}
    for item in files:
        assigned = _view_assignment(item["path"], feature_ids)
        if assigned:
            atom_id, kind = assigned
        else:
            atom_id, kind = _atom_identity(item["path"], indexed, has_modules)
        bucket = grouped.get(atom_id)
        if bucket is None:
            bucket = {
                "id": atom_id,
                "kind": kind,
                "paths": [],
                "decls": [],
                "owners": {},
                "empty_enums": set(),
                "entries": 0,
                "symbol_fanin": {},
                "members": [atom_id],
            }
            grouped[atom_id] = bucket
        elif _KIND_RANK.get(kind, 0) >= _KIND_RANK.get(bucket["kind"], 0):
            bucket["kind"] = kind
        bucket["paths"].append(item["path"])
        if _file_has_entry(item["path"], item["decls"]):
            bucket["entries"] += 1
        for name in item["decls"]:
            bucket["owners"].setdefault(name, item["path"])
            if name not in bucket["decls"]:
                bucket["decls"].append(name)
        bucket["empty_enums"].update(item["empty_enums"])
        item["atom"] = atom_id
    owners = {}
    for atom in grouped.values():
        for name in atom["decls"]:
            owners.setdefault(name, set()).add(atom["id"])
    unique = {}
    for name, ids in owners.items():
        if len(ids) == 1:
            unique[name] = next(iter(ids))
    edges = {}
    for item in files:
        src = item["atom"]
        for idents in item["line_refs"]:
            for ident in idents:
                dst = unique.get(ident)
                if not dst or dst == src:
                    continue
                edges.setdefault((src, dst), set()).add(ident)
                fan = grouped[dst]["symbol_fanin"]
                fan[ident] = fan.get(ident, 0) + 1
    atoms = []
    for atom in grouped.values():
        atom["paths"] = sorted(atom["paths"])
        atom["file_count"] = len(atom["paths"])
        atom["role"] = None
        atoms.append(atom)
    atoms.sort(key=lambda item: item["id"])
    return atoms, edges


def _match_rule(atom, rules):
    """Longest path prefix wins. An exact atom id always wins."""
    if not rules:
        return None
    best = None
    for pattern, role in rules:
        if role not in ROLES:
            continue
        pattern = _posix(pattern or "").strip()
        if not pattern:
            continue
        if pattern == atom["id"]:
            return role
        prefix = pattern.rstrip("/")
        plen = len(prefix)
        for path in atom["paths"]:
            if path == prefix or path.startswith(prefix + "/"):
                if best is None or plen > best[0]:
                    best = (plen, role)
                break
    if best is None:
        return None
    return best[1]


def _fan_sets(atom_id, edges):
    inbound = set()
    outbound = set()
    for (src, dst), names in edges.items():
        if not names:
            continue
        if dst == atom_id and src != atom_id:
            inbound.add(src)
        elif src == atom_id and dst != atom_id:
            outbound.add(dst)
    return inbound, outbound


def _apply_roles(atoms, edges, role_rules):
    """Label each atom. Rules override. Metrics do not run a second clustering."""
    for atom in atoms:
        forced = _match_rule(atom, role_rules)
        inbound, outbound = _fan_sets(atom["id"], edges)
        atom["frequency"] = len(inbound)
        atom["inbound"] = inbound
        atom["outbound"] = outbound
        if forced:
            atom["role"] = forced
            continue
        paths = atom["paths"]
        if atom["kind"] == "adapter-path" or any(_vendorish(path) for path in paths):
            atom["role"] = "adapter"
            continue
        if paths and all(_editor_or_test(path) for path in paths):
            atom["role"] = "adapter"
            continue
        if atom["id"] in _TOOL_IDS:
            atom["role"] = "tool"
            continue
        if atom["kind"] == "tool-path":
            # Editor/test tools are adapters. Other tool trees stay tools even if a
            # window type shows up; they are not gameplay features.
            editorish = "editor" in atom["id"] or atom["id"].endswith("-test") or atom["id"].endswith("-tests")
            if editorish or (paths and all(_editor_or_test(path) for path in paths)):
                atom["role"] = "adapter"
            else:
                atom["role"] = "tool"
            continue
        if atom["id"] in ("main", "bootstrap", "app", "program") and atom["file_count"] <= 3:
            atom["role"] = "bootstrap"
            continue
        if atom["kind"] == "mechanism":
            atom["role"] = "engine"
            continue
        if atom["kind"] in ("residue", "asmdef"):
            # A grab-bag assembly is infrastructure, even if some types look like windows.
            if atom["frequency"] >= 2 or atom["file_count"] >= 40:
                atom["role"] = "engine"
            elif atom["frequency"] or atom["file_count"] >= 8:
                atom["role"] = "tool"
            else:
                atom["role"] = "tool"
            continue
        denom = len(inbound) + len(outbound)
        instability = (float(len(outbound)) / float(denom)) if denom else 1.0
        if atom["kind"] == "feature-dir":
            atom["role"] = "feature"
            continue
        if atom["id"].startswith(("framework-", "extensions-", "rendering-", "gamelogic-")):
            atom["role"] = "engine" if atom["frequency"] >= 2 or atom["file_count"] >= 40 else "tool"
            continue
        if len(inbound) >= 2 and atom["entries"] == 0 and instability <= 0.45:
            atom["role"] = "engine"
            continue
        if atom["entries"]:
            atom["role"] = "feature"
            continue
        if len(inbound) == 1 and atom["id"] not in _TOOL_IDS:
            atom["role"] = "feature"
            continue
        if not inbound and not outbound:
            atom["role"] = "tool"
            continue
        if instability <= 0.35 and atom["entries"] == 0:
            atom["role"] = "tool"
            continue
        atom["role"] = "feature"


def _edge_weight(members_a, members_b, edges):
    weight = 0
    left = members_a if isinstance(members_a, set) else set(members_a)
    right = members_b if isinstance(members_b, set) else set(members_b)
    for src in left:
        for dst in right:
            weight += len(edges.get((src, dst), ()))
            weight += len(edges.get((dst, src), ()))
    return weight


def _recompute_group(node, edges):
    members = set(node["members"])
    inbound = set()
    outbound = set()
    for (src, dst), names in edges.items():
        if not names:
            continue
        src_in = src in members
        dst_in = dst in members
        if src_in and not dst_in:
            outbound.add(dst)
        elif dst_in and not src_in:
            inbound.add(src)
    node["frequency"] = len(inbound)
    node["inbound"] = inbound
    node["outbound"] = outbound


def _pinned(node):
    return node["file_count"] >= _PIN_FILES and node["role"] in ("adapter", "engine", "tool")


def _solid(node):
    return (
        node["role"] == "feature"
        and node["file_count"] >= 3
        and (node["entries"] > 0 or node["kind"] == "feature-dir")
    )


def _prefer_survivor(left, right):
    if left["file_count"] != right["file_count"]:
        return left if left["file_count"] > right["file_count"] else right
    if left["frequency"] != right["frequency"]:
        return left if left["frequency"] > right["frequency"] else right
    if left["id"] <= right["id"]:
        return left
    return right


def _absorb(survivor, other):
    survivor["members"] = sorted(set(survivor["members"]) | set(other["members"]))
    survivor["paths"] = sorted(set(survivor["paths"]) | set(other["paths"]))
    survivor["file_count"] = len(survivor["paths"])
    survivor["entries"] = survivor["entries"] + other["entries"]
    if other.get("kind") == "feature-dir":
        survivor["kind"] = "feature-dir"
    seen = set(survivor["decls"])
    for name in other["decls"]:
        if name not in seen:
            seen.add(name)
            survivor["decls"].append(name)
    for name, count in (other.get("symbol_fanin") or {}).items():
        survivor["symbol_fanin"][name] = survivor["symbol_fanin"].get(name, 0) + count
    for name, path in (other.get("owners") or {}).items():
        survivor["owners"].setdefault(name, path)
    survivor["empty_enums"] = set(survivor.get("empty_enums") or ()) | set(other.get("empty_enums") or ())


def _feature_dir(node):
    return node.get("kind") == "feature-dir"


def _best_pair(nodes, edges, allow_zero_solid, allow_pinned, allow_features):
    best = None
    ids = sorted(nodes)
    for index, left in enumerate(ids):
        for right in ids[index + 1:]:
            first = nodes[left]
            second = nodes[right]
            if first["role"] != second["role"]:
                continue
            if first["role"] == "bootstrap":
                continue
            if first.get("kind") == "mechanism" or second.get("kind") == "mechanism":
                continue
            feature_pair = _feature_dir(first) or _feature_dir(second)
            both_features = _feature_dir(first) and _feature_dir(second)
            if feature_pair and not (allow_features and both_features):
                continue
            if (_pinned(first) or _pinned(second)) and not allow_pinned:
                continue
            if _pinned(first) and _pinned(second):
                continue
            weight = _edge_weight(first["members"], second["members"], edges)
            both = _solid(first) and _solid(second)
            if both and weight == 0 and not allow_zero_solid:
                continue
            rank = (
                1 if feature_pair else 0,
                1 if both else 0,
                0 if weight else 1,
                -weight,
                min(first["file_count"], second["file_count"]),
                left,
                right,
            )
            if best is None or rank < best[0]:
                best = (rank, left, right, both_features)
    if best is None:
        return None
    return best[1], best[2], best[3]


def build_merges(atoms, edges):
    """One merge list. Earlier merges are safer. Later cuts only replay a prefix."""
    nodes = {}
    for atom in atoms:
        nodes[atom["id"]] = copy.deepcopy(atom)
    merges = []
    guard = 0
    limit = max(len(nodes) + 2, 2)
    while len(nodes) > 1 and guard < limit:
        guard += 1
        pair = _best_pair(nodes, edges, False, False, False)
        if pair is None:
            pair = _best_pair(nodes, edges, True, False, False)
        if pair is None:
            pair = _best_pair(nodes, edges, True, True, False)
        if pair is None:
            pair = _best_pair(nodes, edges, True, True, True)
        if pair is None:
            break
        left, right, _feature_pair = pair
        _recompute_group(nodes[left], edges)
        _recompute_group(nodes[right], edges)
        keep = _prefer_survivor(nodes[left], nodes[right])
        drop = nodes[right] if keep is nodes[left] else nodes[left]
        _absorb(keep, drop)
        _recompute_group(keep, edges)
        merges.append((keep["id"], drop["id"], _feature_pair))
        del nodes[drop["id"]]
    return merges


def _clone_node(atom):
    return {
        "id": atom["id"],
        "kind": atom["kind"],
        "role": atom["role"],
        "paths": list(atom["paths"]),
        "decls": list(atom["decls"]),
        "owners": dict(atom.get("owners") or {}),
        "empty_enums": set(atom.get("empty_enums") or ()),
        "entries": atom["entries"],
        "members": list(atom["members"]),
        "file_count": atom["file_count"],
        "symbol_fanin": dict(atom.get("symbol_fanin") or {}),
        "frequency": atom.get("frequency") or 0,
    }


def cut_tree(atoms, merges, edges, target, protect_features=False):
    """Replay `merges` until `target` nodes remain. A coarser cut replays more.

    Feature directories stay unmerged when `protect_features` is set, so a
    default cut lists gameplay modules instead of gluing them into a framework.
    Target 8 turns protection off and is still a later prefix of the same list.
    """
    nodes = {}
    for atom in atoms:
        nodes[atom["id"]] = _clone_node(atom)
    goal = target if target and target > 0 else 1
    for keep_id, drop_id, feature_pair in merges:
        if len(nodes) <= goal:
            break
        if protect_features and feature_pair:
            break
        if keep_id not in nodes or drop_id not in nodes:
            continue
        _absorb(nodes[keep_id], nodes[drop_id])
        _recompute_group(nodes[keep_id], edges)
        del nodes[drop_id]
    return list(nodes.values())


def cut_contains(coarse, fine):
    """True when every coarse node is a union of fine nodes from the same tree."""
    fine_of = {}
    fine_sets = {}
    for card in fine:
        atoms = [item["id"] for item in (card.get("atoms") or [])]
        fine_sets[card["id"]] = set(atoms)
        for atom_id in atoms:
            if atom_id in fine_of:
                return False
            fine_of[atom_id] = card["id"]
    seen = set()
    for card in coarse:
        big = [item["id"] for item in (card.get("atoms") or [])]
        if len(big) != len(set(big)):
            return False
        parts = {}
        for atom_id in big:
            if atom_id not in fine_of:
                return False
            parts.setdefault(fine_of[atom_id], []).append(atom_id)
            seen.add(atom_id)
        union = set()
        for fine_id, chunk in parts.items():
            if set(chunk) != fine_sets[fine_id]:
                return False
            union |= set(chunk)
        if union != set(big):
            return False
    return seen == set(fine_of)


def _engine_deps(node, by_id, edges):
    members = set(node["members"])
    found = []
    for (src, dst), names in sorted(edges.items()):
        if not names or src not in members or dst in members:
            continue
        other = by_id.get(dst)
        if other and other.get("role") == "engine" and dst not in found:
            found.append(dst)
    found.sort(key=lambda atom_id: (-(by_id[atom_id].get("frequency") or 0), atom_id))
    return found[:3]


def _atom_dossier(atom):
    symbols = sorted(
        atom["decls"],
        key=lambda name: (-(atom["symbol_fanin"].get(name, 0)), name),
    )
    return {
        "id": atom["id"],
        "name": symbols[0] if symbols else atom["id"],
        "frequency": atom.get("frequency") or 0,
        "paths": list(atom["paths"]),
        "script_dirs": sorted({_posix(os.path.dirname(path)) or "." for path in atom["paths"]}),
        "scope_paths": list(atom["paths"][:8]),
        "core_symbols": symbols,
        "symbol_fanin": dict(atom.get("symbol_fanin") or {}),
        "role": atom.get("role"),
        "entries": atom.get("entries") or 0,
    }


def _to_card(node, by_id, edges, target):
    symbols = sorted(
        node["decls"],
        key=lambda name: (-(node["symbol_fanin"].get(name, 0)), name),
    )
    top = symbols[0] if symbols else node["id"]
    dirs = sorted({_posix(os.path.dirname(path)) or "." for path in node["paths"]})
    scope = []
    owners = node.get("owners") or {}
    for name in symbols:
        owner = owners.get(name)
        if owner and owner not in scope:
            scope.append(owner)
        if len(scope) >= 8:
            break
    if not scope:
        scope = list(node["paths"][:8])
    role = node["role"] or "tool"
    nested = []
    for atom_id in node["members"]:
        nested.append(_atom_dossier(by_id[atom_id]))
    nested.sort(key=lambda item: (-item["frequency"], item["id"]))
    skill = "" if role == "bootstrap" else "programmer-{}-skill".format(node["id"])
    if role in ("adapter", "tool") or node.get("kind") == "mechanism":
        skill = ""
    responsibility = (
        "{role} {mid} around {top}. "
        "Referenced by {freq} other packages. "
        "One skill covers this node; nested packages are evidence, not skills."
    ).format(role=role, mid=node["id"], top=top, freq=node["frequency"])
    return {
        "id": node["id"],
        "name": node["id"],
        "role": role,
        "responsibility": responsibility,
        "script_dirs": dirs,
        "scope_paths": scope,
        "core_symbols": symbols,
        "symbol_fanin": dict(node["symbol_fanin"]),
        "suggested_skill": skill,
        "recommend": "no",
        "recommend_reason": "",
        "frequency": node["frequency"],
        "low_priority": False,
        "empty_enums": sorted(node.get("empty_enums") or []),
        "paths": list(node["paths"]),
        "entries": node["entries"],
        "file_count": node["file_count"],
        "kind": node.get("kind"),
        "target": target,
        "atoms": nested,
        "engine_deps": _engine_deps(node, by_id, edges),
    }


def _id_confusion(left, right):
    """Higher means the two module ids are easy to mix up. Zero means leave them."""
    if not left or not right or left == right:
        return 0
    if left.endswith("-" + right) or right.endswith("-" + left):
        return 3
    if left.startswith(right + "-") or right.startswith(left + "-"):
        return 3
    return 0


def nearest_sibling(card, cards):
    """One other module id, or empty. Prefers the closest name, then the shorter id."""
    best = ""
    best_score = 0
    own = card.get("id") or ""
    for other in cards or []:
        oid = other.get("id") or ""
        score = _id_confusion(own, oid)
        if score > best_score or (score == best_score and score and (not best or (len(oid), oid) < (len(best), best))):
            best_score = score
            best = oid
    return best if best_score else ""


def programmer_description(card, language=None):
    """Always-on sentence. The trigger is the module id, never a hot declaration.

    Cold start does not repeat the id in parentheses. A missing neighbor
    yields a per-id sentence, not one shared NOT.
    """
    mid = card.get("id") or "module"
    sibling = (card.get("not_sibling") or "").strip()
    lang = normalize_language(
        language if language is not None else card.get("language")
    )
    named = sibling and sibling != mid
    if lang == "zh":
        tail = "NOT {}。".format(sibling) if named else "NOT {} 以外的工作。".format(mid)
        return "改本仓库的 {0}。当用户点名 {0}。{1}".format(mid, tail)
    tail = "NOT {}.".format(sibling) if named else "NOT work outside {}.".format(mid)
    return "Change {0} in this repo. Use when the user names {0}. {1}".format(mid, tail)


def _mixed_bundle(card):
    atoms = card.get("atoms") or []
    if len(atoms) > 1:
        return True
    if card.get("kind") == "mechanism":
        return False
    return False


def _apply_recommend(cards):
    for card in cards:
        card["not_sibling"] = nearest_sibling(card, cards)
    engines = [
        card for card in cards
        if card["role"] == "engine"
        and card["frequency"] > 0
        and card.get("kind") != "mechanism"
        and not _mixed_bundle(card)
    ]
    engines.sort(key=lambda card: (-card["frequency"], -card["file_count"], card["id"]))
    top = {card["id"] for card in engines[:2]}
    for card in cards:
        blocked = (
            card["role"] in ("adapter", "tool", "bootstrap")
            or card.get("kind") == "mechanism"
            or _mixed_bundle(card)
        )
        if blocked:
            card["recommend"] = "no"
            card["suggested_skill"] = ""
            if card["role"] == "bootstrap":
                card["recommend_reason"] = "bootstrap is not a skill"
            elif card.get("kind") == "mechanism":
                card["recommend_reason"] = "framework mechanism stays listed and is not a default skill"
            elif _mixed_bundle(card):
                card["recommend_reason"] = "unrelated packages stay listed and are not one default skill"
            elif card["role"] == "adapter":
                card["recommend_reason"] = "adapter stays listed and unchecked"
            else:
                card["recommend_reason"] = "tool stays listed and unchecked"
        elif card["role"] == "feature" and card.get("entries", 0) > 0:
            card["recommend"] = "yes"
            card["recommend_reason"] = "feature with an entry; one skill for this node"
        elif card["id"] in top:
            card["recommend"] = "yes"
            card["recommend_reason"] = "one engine package; not a default grab-bag"
        elif card["frequency"] == 0:
            card["recommend"] = "no"
            card["recommend_reason"] = "no other package references it yet"
        else:
            card["recommend"] = "no"
            card["recommend_reason"] = "listed; not a default skill"
        card["low_priority"] = card["recommend"] != "yes"


def _sort_cards(cards):
    cards.sort(key=lambda card: (
        0 if card["recommend"] == "yes" else 1,
        _ROLE_ORDER.get(card["role"], 9),
        -card["frequency"],
        card["id"],
    ))
    return cards


def analyze_graph(sources, target=None, asmdef_dirs=None, role_rules=None):
    """Return `(cards, atoms, edges)`. Atoms are the evidence-card input.

    `target` is a layer of one merge tree, not a new clustering.
    """
    goal = DEFAULT_TARGET if target is None else int(target)
    if goal < 1:
        goal = 1
    files = _parse_files(sources)
    if not files:
        return [], [], {}
    atoms, edges = _build_atoms(files, asmdef_dirs)
    _apply_roles(atoms, edges, role_rules or [])
    merges = build_merges(atoms, edges)
    # Targets above 8 keep Modules/<Feature> nodes. Target 8 may fold them,
    # and that fold is a later prefix of the same merge list.
    grouped = cut_tree(atoms, merges, edges, goal, protect_features=goal > 8)
    by_id = {atom["id"]: atom for atom in atoms}
    cards = [_to_card(node, by_id, edges, goal) for node in grouped]
    _apply_recommend(cards)
    return _sort_cards(cards), atoms, edges


def analyze_sources(sources, target=None, asmdef_dirs=None, role_rules=None):
    """Build the selectable cut. `target` is a layer of one merge tree, not a new clustering."""
    cards, _atoms, _edges = analyze_graph(
        sources, target=target, asmdef_dirs=asmdef_dirs, role_rules=role_rules,
    )
    return cards


def load_role_rules(root):
    """Optional project overrides. Read-only. Missing file means no overrides.

    Lines are `atom-id-or-path-prefix<space>role`. This is not a scan ledger.
    """
    path = os.path.join(root, ".castflow-runtime", "module-roles.txt")
    if not os.path.isfile(path):
        return []
    rules = []
    with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2 or parts[-1] not in ROLES:
                continue
            pattern = " ".join(parts[:-1]).strip()
            rules.append((pattern, parts[-1]))
    return rules


def iter_product_files(root):
    """Yield (relative posix path, absolute path) for product scripts. Writes nothing."""
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        kept = []
        for name in sorted(dirnames):
            rel_dir = _posix(os.path.relpath(os.path.join(dirpath, name), root))
            if is_excluded_path(rel_dir):
                continue
            kept.append(name)
        dirnames[:] = kept
        for name in sorted(filenames):
            ext = os.path.splitext(name)[1].lower()
            if ext not in SCRIPT_EXTS:
                continue
            full = os.path.join(dirpath, name)
            rel = _posix(os.path.relpath(full, root))
            if is_excluded_path(rel):
                continue
            yield rel, full


def read_product_tree(root):
    """Return (sources, asmdef list). Writes nothing."""
    root = os.path.abspath(root)
    sources = {}
    asmdefs = []
    for dirpath, dirnames, filenames in os.walk(root):
        kept = []
        for name in sorted(dirnames):
            rel_dir = _posix(os.path.relpath(os.path.join(dirpath, name), root))
            if is_excluded_path(rel_dir):
                continue
            kept.append(name)
        dirnames[:] = kept
        rel_dir = _posix(os.path.relpath(dirpath, root))
        if rel_dir == ".":
            rel_dir = ""
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = name if not rel_dir else rel_dir + "/" + name
            if name.lower().endswith(".asmdef"):
                asmdefs.append((rel_dir, os.path.splitext(name)[0]))
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in SCRIPT_EXTS:
                continue
            if is_excluded_path(rel):
                continue
            try:
                with open(full, "r", encoding="utf-8-sig", errors="replace") as handle:
                    sources[rel] = handle.read()
            except OSError:
                continue
    return sources, asmdefs


def read_product_sources(root):
    sources, _asmdefs = read_product_tree(root)
    return sources


def scan_product(root, target=None):
    """Walk `root` once and return module cards. Writes nothing."""
    cards, _sources = load_sources(root, target=target)
    return cards


def format_summary(cards):
    """Selectable cut. `atom` lines are packages inside the node, not extra modules."""
    atom_total = 0
    for card in cards:
        atom_total += len(card.get("atoms") or [])
    target = DEFAULT_TARGET
    if cards:
        target = cards[0].get("target", DEFAULT_TARGET)
    lines = [
        "modules: {}".format(len(cards)),
        "atoms: {}".format(atom_total),
        "order: role-then-fanin",
        "target: {}".format(target),
    ]
    for card in cards:
        atom_ids = [item["id"] for item in (card.get("atoms") or [])]
        lines.append("{}\t{}\t{}\t{}\t{}\t{}".format(
            card["id"],
            card["frequency"],
            len(atom_ids),
            card["recommend"],
            card.get("role") or "",
            ",".join(atom_ids),
        ))
        for atom in card.get("atoms") or []:
            symbols = ",".join((atom.get("core_symbols") or [])[:8])
            lines.append("atom\t{}\t{}\t{}\t{}".format(
                card["id"], atom["id"], atom["frequency"], symbols,
            ))
    return "\n".join(lines) + "\n"

def select_cards(cards, selected_ids):
    """Return cards for the chosen ids, in the requested selection order."""
    by_id = {card["id"]: card for card in cards}
    chosen = []
    for raw in selected_ids:
        module_id = (raw or "").strip()
        if not module_id:
            continue
        if module_id not in by_id:
            raise KeyError(module_id)
        chosen.append(by_id[module_id])
    return chosen


def _yaml_list(values):
    if not values:
        return " []"
    lines = [""]
    for value in values:
        lines.append("  - {}".format(value))
    return "\n".join(lines)


def _cover_dirs(paths):
    """Drop a directory that already sits under another directory in the set."""
    kept = []
    for path in sorted(set(paths), key=lambda item: (item.count("/"), item)):
        if any(path == root or path.startswith(root + "/") for root in kept):
            continue
        kept.append(path)
    return sorted(kept)


def focus_script_dirs(dirs, limit=6):
    """Collapse nested script directories to a few roots.

    The queue card is a search hint for skill generation, not a file list.
    Symbols and individual scripts are found again under these roots.
    """
    current = []
    for raw in dirs or []:
        path = _posix(raw).strip("/")
        if path and path != ".":
            current.append(path)
    current = _cover_dirs(current)
    while len(current) > limit:
        groups = {}
        for path in current:
            parent = path.rsplit("/", 1)[0] if "/" in path else ""
            groups.setdefault(parent, []).append(path)
        candidates = [
            (parent, kids)
            for parent, kids in groups.items()
            if parent and len(kids) >= 2
        ]
        if not candidates:
            break
        parent, kids = min(candidates, key=lambda item: (-(len(item[1]) - 1), item[0]))
        current = [path for path in current if path not in set(kids)]
        current.append(parent)
        current = _cover_dirs(current)
    if len(current) > limit:
        current = sorted(current, key=lambda path: (path.count("/"), len(path), path))[:limit]
    return sorted(current)


def queue_dir(project_root):
    return os.path.join(project_root, ".castflow-runtime", "_skill-gen-queue")


def skill_dir(project_root, module_id):
    return os.path.join(
        project_root, ".castflow-runtime", "skills",
        "programmer-{}-skill".format(module_id),
    )


def write_selected_queue(project_root, cards):
    """Persist only the selected cards. Removes any previous queue files first."""
    path = queue_dir(project_root)
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path)
    written = []
    language = normalize_language(load_config(project_root).get("language"))
    for index, card in enumerate(cards, 1):
        name = "{:02d}-{}.yaml".format(index, card["id"])
        full = os.path.join(path, name)
        atom_ids = [item["id"] for item in (card.get("atoms") or [])]
        body = (
            "status: pending\n"
            "language: {language}\n"
            "id: {id}\n"
            "name: {name}\n"
            "role: {role}\n"
            "responsibility: {responsibility}\n"
            "script_dirs:{dirs}\n"
            "atoms:{atoms}\n"
            "suggested_skill: {skill}\n"
        ).format(
            language=language,
            id=card["id"],
            name=card["name"],
            role=card.get("role") or "",
            responsibility=card["responsibility"].replace("\n", " "),
            dirs=_yaml_list(focus_script_dirs(card.get("script_dirs") or [])),
            atoms=_yaml_list(atom_ids),
            skill=card.get("suggested_skill") or "",
        )
        with open(full, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
        written.append(full)
    return written


def delete_queue(project_root):
    path = queue_dir(project_root)
    if os.path.isdir(path):
        shutil.rmtree(path)
    return not os.path.exists(path)


def _is_decl_line(line, symbol, ext):
    for name in _decl_names(line, ext):
        if name == symbol:
            return True
    return False


def _ui_context(path, line):
    if _UI_PATH.search(path or ""):
        return True
    return bool(_UI_TYPE.search(line or ""))


def collect_call_sites(sources, card, limit=8):
    """Real non-declaration uses of the card's type names.

    `sources` is `{relative path: raw text}`. Hits must lie on this module's
    cluster files. Definition lines, `using` lines, empty enums, and protocol
    Send/Handle symbols (unless the hit is in a UI/Flow context) are not
    call sites.
    """
    allowed = set(card.get("paths") or [])
    for atom in (card.get("atoms") or []) + (card.get("clusters") or []):
        allowed.update(atom.get("paths") or [])
    symbols = [
        name for name in (card.get("core_symbols") or [])
        if name and name not in set(card.get("empty_enums") or [])
        and not _PROTOCOL.match(name)
    ]
    if not symbols:
        return []
    wanted = set(symbols)
    scope = set(card.get("scope_paths") or [])
    hits = []
    for rel in sorted(sources):
        path = _posix(rel)
        if allowed and path not in allowed:
            continue
        if is_excluded_path(path):
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext not in SCRIPT_EXTS:
            continue
        _decls, line_refs, lines = parse_script(sources[rel], ext)
        for index, idents in enumerate(line_refs):
            if not idents:
                continue
            line = lines[index] if index < len(lines) else ""
            if _USING_LINE.match(line):
                continue
            for symbol in symbols:
                if symbol not in idents:
                    continue
                if symbol not in wanted:
                    continue
                if _is_decl_line(line, symbol, ext):
                    continue
                if _PROTOCOL.match(symbol) and not _ui_context(path, line):
                    continue
                stripped = line.strip()
                if "{{" in stripped or "}}" in stripped:
                    continue
                if any(ch in stripped for ch in "\u2192\u2713\u2717\u2605"):
                    continue
                hits.append({
                    "symbol": symbol,
                    "path": path,
                    "line": index + 1,
                    "text": line.strip(),
                    "outside_scope": path not in scope,
                })
    # Prefer cross-file / out-of-scope hits, then stable path, and keep the
    # hottest symbols first. Cap at `limit` distinct (path, line, symbol).
    fanin = card.get("symbol_fanin") or {}
    hits.sort(key=lambda hit: (
        0 if hit["outside_scope"] else 1,
        -fanin.get(hit["symbol"], 0),
        hit["symbol"],
        hit["path"],
        hit["line"],
    ))
    chosen = []
    seen = set()
    used_symbols = []
    for hit in hits:
        key = (hit["path"], hit["line"], hit["symbol"])
        if key in seen:
            continue
        seen.add(key)
        chosen.append(hit)
        if hit["symbol"] not in used_symbols:
            used_symbols.append(hit["symbol"])
        if len(chosen) >= limit:
            break
    # If the cap left us under 3, the caller still sees what exists.
    return chosen


def load_sources(root, target=None):
    """Read product scripts once and return (cards, sources). Writes nothing."""
    sources, asmdefs = read_product_tree(root)
    rules = load_role_rules(root)
    cards = analyze_sources(
        sources, target=target, asmdef_dirs=asmdefs, role_rules=rules,
    )
    return cards, sources


def _description(card, language=None):
    return programmer_description(card, language=language)


def heat_path_violations(card, call_sites, skill_text):
    """Return human-readable violations. Empty means the skill info is clean."""
    problems = []
    if not (1 <= len(call_sites) <= 8):
        problems.append("EXAMPLES count {} is outside 1-8".format(len(call_sites)))
    empty = set(card.get("empty_enums") or [])
    for hit in call_sites:
        symbol = hit["symbol"]
        if symbol in empty:
            problems.append("empty enum {} used as an example".format(symbol))
        if _PROTOCOL.match(symbol) and not _ui_context(hit["path"], hit["text"]):
            problems.append("protocol symbol {} outside UI/Flow".format(symbol))
        if _is_decl_line(hit["text"], symbol, os.path.splitext(hit["path"])[1].lower()):
            problems.append("declaration line used for {}".format(symbol))
        if _USING_LINE.match(hit["text"]):
            problems.append("using line used for {}".format(symbol))
    # Copied call sites may mention a field. The skill must not promote an
    # OnInit-only field, an empty enum, or a protocol method into an entry.
    if re.search(r"\b(is the registry|当作登记表|as a dictionary key|当作字典键)\b", skill_text, re.I):
        problems.append("skill text presents a registry or dictionary key")
    return problems


def _skill_markdown(card, desc, symbols, language):
    """Recall body. Links only the role file this pass actually writes."""
    mid = card["id"]
    skill_name = card.get("suggested_skill") or "programmer-{}-skill".format(mid)
    engine_deps = card.get("engine_deps") or []
    symbol_list = ", ".join(symbols)
    if language == "zh":
        deps = (
            "- 依赖引擎 {}（只写一句，不抄它的示例）。\n".format(", ".join(engine_deps))
            if engine_deps else ""
        )
        if symbols:
            duties = (
                "- 只改产品脚本里已有的 {} 调用点。\n"
                "- 定义命中不是入口。\n"
            ).format(symbol_list)
            nav = "- EXAMPLES.md — 从产品脚本复制的热调用点\n"
        else:
            duties = "- 这次没有活调用点。不要编一个入口。\n"
            nav = ""
        body = (
            "改本仓库的 {mid}。\n\n"
            "## 让位\n\n"
            "{desc}\n\n"
            "## 职责\n\n"
            "{duties}"
            "{deps}"
        ).format(mid=mid, desc=desc, duties=duties, deps=deps)
        if nav:
            body += "\n## 导航\n\n" + nav
    else:
        deps = (
            "- Depends on engine {} (summary only, not its own examples).\n".format(
                ", ".join(engine_deps)
            )
            if engine_deps else ""
        )
        if symbols:
            duties = (
                "- Edit existing product-script call sites of {}.\n"
                "- A definition hit is not an entry.\n"
            ).format(symbol_list)
            nav = "- EXAMPLES.md — hot call sites copied from product scripts\n"
        else:
            duties = "- This pass found no live call site. Do not invent an entry.\n"
            nav = ""
        body = (
            "Change {mid} in this repo.\n\n"
            "## Yield\n\n"
            "{desc}\n\n"
            "## Responsibilities\n\n"
            "{duties}"
            "{deps}"
        ).format(mid=mid, desc=desc, duties=duties, deps=deps)
        if nav:
            body += "\n## Navigate\n\n" + nav
    return (
        "---\n"
        "name: {skill}\n"
        "description: {desc}\n"
        "---\n\n"
        "{body}"
    ).format(skill=skill_name, desc=desc, body=body)


def _example_blocks(call_sites, language):
    blocks = []
    for index, hit in enumerate(call_sites, 1):
        text = hit["text"] or hit["symbol"]
        if language == "zh":
            blocks.append(
                "## 示例{n}：{symbol} 调用点\n\n"
                "场景\n"
                "产品脚本在声明行以外引用 {symbol}。\n\n"
                "代码\n"
                "```\n"
                "{text}\n"
                "```\n\n"
                "项目参考\n"
                "{path}:{line} {symbol}\n"
                .format(
                    n=index, symbol=hit["symbol"], text=text,
                    path=hit["path"], line=hit["line"],
                )
            )
        else:
            blocks.append(
                "## Example {n}: {symbol} call site\n\n"
                "Scene\n"
                "Product script references {symbol} outside its declaration.\n\n"
                "Code\n"
                "```\n"
                "{text}\n"
                "```\n\n"
                "Project reference\n"
                "{path}:{line} {symbol}\n"
                .format(
                    n=index, symbol=hit["symbol"], text=text,
                    path=hit["path"], line=hit["line"],
                )
            )
    return "\n".join(blocks)


def write_programmer_skill(project_root, card, sources, call_sites=None):
    """Write one programmer skill from real call sites. One card only.

    SKILL.md is always written. EXAMPLES.md is written only for live hits.
    SKILL_MEMORY.md and ITERATION_GUIDE.md are not quota files.
    """
    if call_sites is None:
        call_sites = collect_call_sites(sources, card, limit=8)
    else:
        call_sites = list(call_sites)
    if len(call_sites) > 8:
        call_sites = call_sites[:8]
    folder = skill_dir(project_root, card["id"])
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)
    language = normalize_language(load_config(project_root).get("language"))
    desc = _description(card, language=language)
    symbols = []
    for hit in call_sites:
        if hit["symbol"] not in symbols:
            symbols.append(hit["symbol"])
    skill = _skill_markdown(card, desc, symbols, language)
    payloads = {"SKILL.md": skill}
    if call_sites:
        examples = _example_blocks(call_sites, language)
        problems = heat_path_violations(card, call_sites, examples + "\n" + skill)
        if problems:
            raise RuntimeError("heat-path: {}".format("; ".join(problems)))
        payloads["EXAMPLES.md"] = examples
    for fname, content in payloads.items():
        with open(os.path.join(folder, fname), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    errors, _warnings, skipped = validate_skill_dir(folder)
    if skipped or errors:
        raise RuntimeError("validate: {}".format(errors or "skipped"))
    return folder, call_sites


def assert_no_ledger(project_root):
    """Return ledger paths that exist anywhere under the project root."""
    found = []
    root = os.path.abspath(project_root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in (".git", "Library", "Temp", "obj")]
        for name in filenames:
            if name in LEDGER_NAMES or name == ".ua":
                found.append(os.path.join(dirpath, name))
        if ".ua" in dirnames:
            found.append(os.path.join(dirpath, ".ua"))
    return found
