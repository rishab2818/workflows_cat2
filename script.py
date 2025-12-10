import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

IDENT_RE = r"[A-Za-z][A-Za-z0-9_]*"


def strip_comment(line: str) -> str:
    """Remove Ada line comment starting with --."""
    idx = line.find("--")
    if idx != -1:
        return line[:idx]
    return line


def is_package_unit(text: str) -> bool:
    """
    Heuristic:
    - Ignore leading with/use lines and comments.
    - If the first significant keyword is 'package' -> treat as package unit.
    - If we see 'procedure'/'function' first -> treat as subprogram file.
    """
    for line in text.splitlines():
        code = strip_comment(line).strip().lower()
        if not code:
            continue
        if code.startswith("with ") or code.startswith("use "):
            continue
        if code.startswith("package "):
            return True
        if code.startswith("procedure ") or code.startswith("function "):
            return False
    return False


def collect_type_names(line: str) -> Dict[str, str]:
    """
    Find type names used in a declaration line and return mapping to UPPERCASE.

    Examples:
      X : Integer := 0;           -> Integer
      subtype Index is Integer;   -> Integer
      type Vec is array (... of Integer); -> Integer
      function F (...) return Float;      -> Float
    """
    mapping: Dict[str, str] = {}
    code = strip_comment(line)

    # Type name after colon (parameters/variables), possibly with 'constant', 'in', 'out'
    mtype = re.search(
        rf":\s*(?:constant\s+)?(?:in\s+out\s+|in\s+|out\s+)?({IDENT_RE})",
        code,
        re.IGNORECASE,
    )
    if mtype:
        tname = mtype.group(1)
        mapping[tname.lower()] = tname.upper()

    # Element type of an array: "array (...) of <TYPE>"
    if re.search(r"\barray\b", code, re.IGNORECASE):
        marray = re.search(rf"\bof\s+({IDENT_RE})", code, re.IGNORECASE)
        if marray:
            tname = marray.group(1)
            mapping[tname.lower()] = tname.upper()

    # Return type in function declarations: "return <TYPE>"
    mret = re.search(rf"\breturn\s+({IDENT_RE})", code, re.IGNORECASE)
    if mret:
        tname = mret.group(1)
        mapping[tname.lower()] = tname.upper()

    return mapping


def collect_declarations(
    lines: List[str], make_var_upper: bool
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Scan a list of lines for declarations and return:
        (identifier_mapping, type_name_mapping)

    - make_var_upper=True  => variables/constants/types -> UPPERCASE
    - make_var_upper=False => variables (non-constant) -> lowercase,
                              constants/types -> UPPERCASE
    """
    identifiers: Dict[str, str] = {}
    type_names: Dict[str, str] = {}

    for raw in lines:
        code = strip_comment(raw).rstrip()
        stripped = code.strip()
        if not stripped:
            continue

        # TYPE / SUBTYPE declarations: declared name always uppercase
        m = re.match(rf"^\s*(type|subtype)\s+({IDENT_RE})\b", code, re.IGNORECASE)
        if m:
            name = m.group(2)
            identifiers[name.lower()] = name.upper()
            # Also capture any type names used on the RHS
            type_map = collect_type_names(code)
            type_names.update(type_map)
            continue

        # Object declarations:
        #   A, B : constant Integer := 10;
        #   C    : Integer := 0;
        m = re.match(r"^\s*([A-Za-z0-9_,\s]+):(.*)$", code)
        if m:
            id_part = m.group(1)
            rest = m.group(2)
            is_const = bool(re.search(r"\bconstant\b", rest, re.IGNORECASE))

            for ident in id_part.split(","):
                name = ident.strip()
                if not name:
                    continue
                if not re.match(rf"^{IDENT_RE}$", name):
                    continue

                if is_const:
                    new_name = name.upper()
                else:
                    if make_var_upper:
                        new_name = name.upper()
                    else:
                        new_name = name.lower()

                identifiers[name.lower()] = new_name

            # And capture any type names used here
            type_map = collect_type_names(code)
            type_names.update(type_map)

    return identifiers, type_names


def collect_package_mapping(text: str) -> Dict[str, str]:
    """
    For package spec/body files:
    - Treat *all* variables/constants/types as 'global' => UPPERCASE.
    - All type names used in declarations (built-in or user-defined) -> UPPERCASE.
    """
    lines = text.splitlines()
    id_map, type_map = collect_declarations(lines, make_var_upper=True)
    mapping: Dict[str, str] = {}
    mapping.update(id_map)
    mapping.update(type_map)
    return mapping


def find_first_subprogram(text: str):
    """
    Find the first procedure/function in the text, skipping commented parts.

    Returns (kind, index) where kind is 'procedure' or 'function',
    or (None, None) if not found.
    """
    offset = 0
    for line in text.splitlines(True):  # keep line endings
        code = strip_comment(line)
        m = re.search(r"\b(procedure|function)\b", code, re.IGNORECASE)
        if m:
            return m.group(1).lower(), offset + m.start()
        offset += len(line)
    return None, None


def find_keyword_after(text: str, keyword: str, start: int):
    """Find the position of a keyword after 'start', or None."""
    if start is None:
        return None
    m = re.search(rf"\b{keyword}\b", text[start:], re.IGNORECASE)
    if not m:
        return None
    return start + m.start()


def collect_subprogram_mapping(text: str) -> Dict[str, str]:
    """
    Collect mapping of identifiers and type names for a standalone
    procedure/function file.

    Rules:
    - Declarations before the first subprogram: globals -> UPPERCASE.
    - Parameters and local variables: lowercase (non-constants).
    - All constants and type declarations: UPPERCASE.
    - All type names used in declarations and return types: UPPERCASE.
    - Loop index in 'for I in ...' : lowercase.
    - Undeclared identifiers on LHS of ':=' are treated as external globals -> UPPERCASE.
    """
    kind, proc_start = find_first_subprogram(text)
    if kind is None:
        # No procedure/function found; treat as package unit
        return collect_package_mapping(text)

    # Declarations before the subprogram: globals
    before_lines = text[:proc_start].splitlines()
    global_id_map, global_type_map = collect_declarations(before_lines, make_var_upper=True)

    is_pos = find_keyword_after(text, "is", proc_start)
    begin_pos = find_keyword_after(text, "begin", is_pos if is_pos is not None else proc_start)

    # If we can't find declarative part, just use globals
    if is_pos is None or begin_pos is None:
        mapping: Dict[str, str] = {}
        mapping.update(global_id_map)
        mapping.update(global_type_map)
        return mapping

    header = text[proc_start:is_pos]
    declarative_lines = text[is_pos:begin_pos].splitlines()

    mapping: Dict[str, str] = {}
    mapping.update(global_id_map)
    mapping.update(global_type_map)

    # Parameters: names -> lowercase, types -> UPPERCASE
    paren_match = re.search(r"\((.*)\)", header, re.DOTALL)
    if paren_match:
        params_str = paren_match.group(1)
        for group in params_str.split(";"):
            group_code = strip_comment(group)
            # names before colon
            m = re.match(rf"\s*([A-Za-z0-9_,\s]+):", group_code)
            if m:
                id_part = m.group(1)
                for ident in id_part.split(","):
                    name = ident.strip()
                    if not name:
                        continue
                    if not re.match(rf"^{IDENT_RE}$", name):
                        continue
                    mapping[name.lower()] = name.lower()
            # type names in parameter spec
            type_map = collect_type_names(group_code)
            mapping.update(type_map)

    # Return type for functions
    m_return = re.search(rf"\breturn\s+({IDENT_RE})", header, re.IGNORECASE)
    if m_return:
        ret_type = m_return.group(1)
        mapping[ret_type.lower()] = ret_type.upper()

    # Declarations between 'is' and 'begin'
    local_id_map, local_type_map = collect_declarations(
        declarative_lines, make_var_upper=False
    )
    mapping.update(local_id_map)
    mapping.update(local_type_map)

    # Loop variables: 'for I in SOMETHING loop' => I is local -> lowercase
    no_comment_text = "\n".join(strip_comment(l) for l in text.splitlines())
    for mloop in re.finditer(rf"\bfor\s+({IDENT_RE})\s+in\b", no_comment_text, re.IGNORECASE):
        loop_var = mloop.group(1)
        canon = loop_var.lower()
        # If it's not already a constant/type/global, treat as local var
        if canon not in mapping or mapping[canon].isupper():
            mapping[canon] = loop_var.lower()

    # External globals: identifiers on the left side of ':=' that are not
    # declared locally (no param/local/constant/type) are assumed to be
    # global variables and should be UPPERCASE.
    assignment_re = re.compile(rf"^\s*({IDENT_RE})\s*:=", re.IGNORECASE)
    for raw in text.splitlines():
        code = strip_comment(raw)
        m = assignment_re.match(code)
        if not m:
            continue
        name = m.group(1)
        canon = name.lower()
        if canon not in mapping:
            mapping[canon] = name.upper()

    return mapping


def apply_mapping(text: str, mapping: Dict[str, str]) -> str:
    """
    Apply identifier case mapping to the whole Ada source text.

    mapping: canonical_name (lowercase) -> new_name (desired spelling).
    """
    if not mapping:
        return text

    result = text
    # sort by length descending so longer identifiers match first
    for canon_name, new_name in sorted(mapping.items(), key=lambda kv: -len(kv[0])):
        pattern = re.compile(rf"\b{re.escape(canon_name)}\b", re.IGNORECASE)
        result = pattern.sub(new_name, result)

    return result


def process_file(path: Path, out_dir: Path):
    """Read, normalize and write a single .ada file."""
    original = path.read_text(encoding="utf-8")

    if is_package_unit(original):
        mapping = collect_package_mapping(original)
    else:
        mapping = collect_subprogram_mapping(original)

    new_text = apply_mapping(original, mapping)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / path.name
    out_path.write_text(new_text, encoding="utf-8")
    print(f"Processed {path} -> {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Normalize Ada identifier casing (globals/types/constants UPPER, locals lower)."
    )
    parser.add_argument(
        "source_dir",
        help="Directory containing .ada files to process",
    )
    parser.add_argument(
        "--out-dir",
        help="Output directory for corrected files (default: <source_dir>/_normalized)",
        default=None,
    )
    args = parser.parse_args()

    src = Path(args.source_dir)
    if not src.is_dir():
        raise SystemExit(f"{src} is not a directory")

    out_dir = Path(args.out_dir) if args.out_dir else src / "_normalized"

    for entry in src.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".ada":
            process_file(entry, out_dir)


if __name__ == "__main__":
    main()
