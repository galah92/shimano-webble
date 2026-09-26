#!/usr/bin/env python3
"""Verify eTuning 3.0.7's firmware-file allowlist without storing the APK.

The input is JADX's ``C0473Oa.java`` from the exact XAPK fingerprinted in
ASSETS.md.  The checker decodes the obfuscated 32-character MD5 strings,
requires the recorded allowlists, and can match local candidate firmware
files.  It is read-only and never prints firmware contents.
"""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path


XAPK_SIZE = 7_228_364
XAPK_SHA256 = "9964a346b708eb0c42e13dc08f71073e2dd1673b158b21491d57ac4f714b4eb9"
APK_SIZE = 7_060_465
APK_SHA256 = "d4d545150f025760a13bf3bcade148f278731a1d49bf59d1e9da338723c90e22"

GENERAL_ALLOWLIST = {
    "6daee3c8de5ae0d4b77443e28c7bb758",
    "492d14c37c8ee2fd4a636ab416eea143",
    "1efaa10b5205ca6b2b42b0f95a248489",
    "f8355d7666db9fefaa236e6caa4c578b",
    "414859c49af7454a9f9d62aacf67dcd6",
    "d641cb58698fbbe82be31321569cb55a",
    "f87853420f4d6778f0a2d3ec1567fdeb",
    "9edbfdb6c72fae6b1fe1aa59841101fb",
    "10018ba991b00a757c9f29ad368ed774",
    "861fd985b3964283c6b316cd3fe04bd3",
    "916987ac8f1d6a4783da1eb72a3d2465",
    "67b2e6987ea441d642c567116b271284",
    "aa35536758eea011ca5779952295811d",
    "8124a6ef8b3bed1719c45aeafc475de4",
    "60c9f5dc92c869c1467d20d40783a583",
    "f0f94a29a328bae502ce8d1ea66f9abe",
    "4df386b7ace4f9d3ad130063ba28c552",
    "fd1abd9c85cd5b6bf1b2ff51c5d1a4d0",
}
SPECIAL_ALLOWLIST = {
    "414859c49af7454a9f9d62aacf67dcd6",
    "d641cb58698fbbe82be31321569cb55a",
    "f87853420f4d6778f0a2d3ec1567fdeb",
    "9edbfdb6c72fae6b1fe1aa59841101fb",
}
E5000_PAIR = {
    "DUE5000-D.5.3.0.dat": "6daee3c8de5ae0d4b77443e28c7bb758",
    "DUE5000-M.5.2.1.dat": "492d14c37c8ee2fd4a636ab416eea143",
}


def extract_block(source, marker):
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index]
    raise ValueError(f"unterminated block after {marker}")


def rotate_right(value, distance):
    value &= 0xFFFFFFFF
    distance &= 31
    return ((value >> distance) | (value << (32 - distance))) & 0xFFFFFFFF


def safe_integer(expression):
    expression = expression.replace("(f1923d ^ f1923d)", "0")
    rotation = re.compile(r"Integer\.rotateRight\((-?\d+),\s*(\d+)\)")
    while rotation.search(expression):
        expression = rotation.sub(lambda match: str(rotate_right(
            int(match.group(1)), int(match.group(2)))), expression)
    tree = ast.parse(expression, mode="eval")

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -evaluate(node.operand)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.BitXor)):
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            return left ^ right
        raise ValueError(f"unsupported Java integer expression: {expression}")

    return evaluate(tree) & 0xFFFF


def char_expressions(statement):
    values = []
    cursor = 0
    while True:
        marker = statement.find("(char)", cursor)
        if marker < 0:
            return values
        opening = statement.find("(", marker + len("(char)"))
        if opening < 0:
            raise ValueError("char expression has no opening parenthesis")
        depth = 0
        for index in range(opening, len(statement)):
            if statement[index] == "(":
                depth += 1
            elif statement[index] == ")":
                depth -= 1
                if depth == 0:
                    values.append(statement[opening + 1:index])
                    cursor = index + 1
                    break
        else:
            raise ValueError("unterminated char expression")


def decode_hashes(block):
    decoded = []
    builders = {}
    statement_pattern = re.compile(r"[^;]+;", re.S)
    for match in statement_pattern.finditer(block):
        statement = match.group(0).strip()
        builder = re.search(r"StringBuilder\s+(\w+)\s*=\s*new StringBuilder", statement)
        if builder:
            builders[builder.group(1)] = []
            continue
        append = re.search(r"(\w+)\.append\(\(char\)", statement)
        if append and append.group(1) in builders:
            expressions = char_expressions(statement)
            if len(expressions) != 1:
                raise ValueError("unexpected StringBuilder append shape")
            builders[append.group(1)].append(chr(safe_integer(expressions[0])))
            continue
        add_builder = re.search(r"hashSet\.add\((\w+)\.toString\(\)\)", statement)
        if add_builder:
            name = add_builder.group(1)
            if name not in builders:
                raise ValueError(f"unknown StringBuilder {name}")
            decoded.append("".join(builders.pop(name)))
            continue
        if "hashSet.add(new String(new char[]" in statement:
            decoded.append("".join(chr(safe_integer(value))
                                   for value in char_expressions(statement)))
    invalid = sorted(value for value in decoded if not re.fullmatch(r"[0-9a-f]{32}", value))
    if invalid:
        raise ValueError(f"decoded non-MD5 allowlist values: {invalid}")
    return set(decoded)


def digest(path, algorithm="sha256"):
    hasher = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def inspect(source_path, candidates=(), xapk=None, apk=None):
    source = source_path.read_text(encoding="utf-8")
    general = decode_hashes(extract_block(source, "public static HashSet m2079l()"))
    static = extract_block(source, "static {")
    special_body = static[static.index("HashSet hashSet = new HashSet();"):]
    special = decode_hashes(special_body)
    if general != GENERAL_ALLOWLIST:
        raise ValueError("general firmware MD5 allowlist mismatch")
    if special != SPECIAL_ALLOWLIST:
        raise ValueError("special firmware MD5 allowlist mismatch")
    required_fragments = (
        "MessageDigest.getInstance", "ZipInputStream", "f1921b.contains",
        "m2065A(file)", "linkedHashMap.put",
    )
    missing = [fragment for fragment in required_fragments if fragment not in source]
    if missing:
        raise ValueError(f"firmware import/check path is missing: {', '.join(missing)}")

    packages = {}
    for label, path, size, expected in (
        ("xapk", xapk, XAPK_SIZE, XAPK_SHA256),
        ("base_apk", apk, APK_SIZE, APK_SHA256),
    ):
        if path is None:
            continue
        actual = digest(path)
        if path.stat().st_size != size or actual != expected:
            raise ValueError(f"{path.name}: not the exact recorded eTuning 3.0.7 {label}")
        packages[label] = {"name": path.name, "size": size, "sha256": actual}

    files = []
    for path in candidates:
        md5 = digest(path, "md5")
        files.append({
            "name": path.name,
            "size": path.stat().st_size,
            "md5": md5,
            "allowed": md5 in general,
            "recorded_e5000_role": next((name for name, value in E5000_PAIR.items()
                                          if value == md5), None),
        })
    return {
        "source": source_path.name,
        "packages": packages,
        "general_allowlist": sorted(general),
        "special_allowlist": sorted(special),
        "e5000_preparation_pair": E5000_PAIR,
        "candidate_files": files,
        "bounded_conclusion": (
            "the exact eTuning 3.0.7 client accepts the two recorded stock public "
            "E5000 D4.3.0/M4.2.1 files by exact MD5; no modified E5000 image is "
            "needed to satisfy this client-side firmware import allowlist"
        ),
        "limitations": [
            "client-side acceptance does not prove a wireless transfer completes on this bike",
            "it does not explain the D4.3 direct-A8 gate paradox or prove the destination write",
            "it does not prove persistence or a higher measured assistance cutoff",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="JADX C0473Oa.java from eTuning 3.0.7")
    parser.add_argument("--xapk", type=Path, help="optional exact XAPK fingerprint check")
    parser.add_argument("--apk", type=Path, help="optional exact base APK fingerprint check")
    parser.add_argument("--firmware", type=Path, action="append", default=[],
                        help="optional local firmware file to match by MD5; repeatable")
    arguments = parser.parse_args()
    try:
        result = inspect(arguments.source, arguments.firmware, arguments.xapk, arguments.apk)
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
