#!/usr/bin/env python3
"""Synthetic tests for the eTuning firmware-policy evidence checker."""
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "inspect_etuning_firmware_policy", ROOT / "tools" / "inspect_etuning_firmware_policy.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def encoded(value):
    return ", ".join(f"(char) ({ord(character)} + (f1923d ^ f1923d))"
                     for character in value)


def source_fixture(general=None):
    general = MODULE.GENERAL_ALLOWLIST if general is None else general
    special_lines = "\n".join(
        f"hashSet.add(new String(new char[]{{{encoded(value)}}}));"
        for value in sorted(MODULE.SPECIAL_ALLOWLIST))
    general_lines = "\n".join(
        f"hashSet.add(new String(new char[]{{{encoded(value)}}}));"
        for value in sorted(general)
    )
    return f"""
public final class C0473Oa {{
  static {{
    HashSet hashSet = new HashSet();
    {special_lines}
    f1922c = hashSet;
  }}
  public static HashSet m2079l() {{
    HashSet hashSet = new HashSet();
    {general_lines}
    return hashSet;
  }}
  MessageDigest.getInstance(); ZipInputStream input;
  boolean a = f1921b.contains(m2065A(file));
  void keep() {{ linkedHashMap.put(); }}
}}
"""


class FirmwarePolicyTest(unittest.TestCase):
    def test_integer_decoder_matches_java_signed_rotate_right(self):
        self.assertEqual(MODULE.safe_integer(
            "(Integer.rotateRight(-1761607532, 24) ^ 38049) + (f1923d ^ f1923d)"),
            ord("6"))

    def test_exact_allowlists_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "C0473Oa.java"
            source.write_text(source_fixture(), encoding="utf-8")
            result = MODULE.inspect(source)
            self.assertEqual(set(result["general_allowlist"]), MODULE.GENERAL_ALLOWLIST)
            self.assertEqual(set(result["special_allowlist"]), MODULE.SPECIAL_ALLOWLIST)
            self.assertEqual(result["e5000_preparation_pair"], MODULE.E5000_PAIR)

            source.write_text(source_fixture(MODULE.GENERAL_ALLOWLIST - {
                "6daee3c8de5ae0d4b77443e28c7bb758"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "general firmware MD5 allowlist mismatch"):
                MODULE.inspect(source)


if __name__ == "__main__":
    unittest.main()
