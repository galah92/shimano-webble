#!/usr/bin/env python3
"""Verify E-TUBE 3.4.5's dormant E5000 boot-patch path.

This read-only checker requires ``dnfile`` and ``dncil`` and the three exact
managed assemblies fingerprinted in ASSETS.md.  It verifies the model spec,
filename construction, update call chain, and boot-patch header.  It neither
finds nor installs a boot patch and does not inspect the motor bootloader.
"""
import argparse
import hashlib
import json
from pathlib import Path

try:
    import dnfile
    from dncil.cil.body.reader import read_method_body_from_bytes
    from dncil.clr.token import Token
except ImportError as error:  # pragma: no cover - environment dependency
    raise SystemExit("install dnfile and dncil in an isolated environment") from error


ASSEMBLIES = {
    "etubedatalinks.dll": (851_456, "814d8096d9f6e5552d8131ff840d3bf407b0f0b089c9a0a821cbb34f141e5ab5"),
    "etubecommons.dll": (215_040, "90d57684bd06caa6071d143357a61432c5f8225b72694271f5da18ce7bb7131c"),
    "etubedata.dll": (2_128_384, "e67f2a12a678628521095dfef9cc27d5588abda8988606206b03ad43382e1dbe"),
}
HEADER_FIELDS = {
    "CheckSum1": 0,
    "CheckSum2": 1,
    "CodeAreaSize": 2,
    "DCASVersion": 4,
    "MiconGenerationNo": 5,
    "VersionMajorMinor": 6,
    "VersionSubMinor": 7,
    "VersionRevision": 8,
}


def exact_bytes(path, expected_name):
    data = path.read_bytes()
    size, expected_hash = ASSEMBLIES[expected_name]
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != size or digest != expected_hash:
        raise ValueError(f"{path.name}: not the exact recorded E-TUBE 3.4.5 {expected_name}")
    return data, {"name": path.name, "size": size, "sha256": digest}


def type_row(pe, namespace, name):
    rows = [row for row in pe.net.mdtables.TypeDef
            if str(row.TypeNamespace) == namespace and str(row.TypeName) == name]
    if len(rows) != 1:
        raise ValueError(f"expected one type {namespace}.{name}, found {len(rows)}")
    return rows[0]


def method_row(type_definition, name):
    rows = [index.row for index in type_definition.MethodList if str(index.row.Name) == name]
    if len(rows) != 1:
        raise ValueError(f"expected one {type_definition.TypeName}.{name}, found {len(rows)}")
    return rows[0]


def body(pe, method):
    if not method.Rva:
        raise ValueError(f"method {method.Name} has no body")
    return read_method_body_from_bytes(pe.get_data(method.Rva))


def token_name(pe, operand):
    if not isinstance(operand, Token):
        return None
    tables = {
        0x04: pe.net.mdtables.Field,
        0x06: pe.net.mdtables.MethodDef,
        0x0A: pe.net.mdtables.MemberRef,
    }
    table = tables.get(operand.table)
    if table is None or operand.rid < 1 or operand.rid > len(table.rows):
        return None
    return str(table.rows[operand.rid - 1].Name)


def instructions(pe, type_definition, method_name):
    return list(body(pe, method_row(type_definition, method_name)).instructions)


def called_names(pe, type_definition, method_name):
    return {name for instruction in instructions(pe, type_definition, method_name)
            if str(instruction.opcode) in ("call", "callvirt", "newobj")
            if (name := token_name(pe, instruction.operand))}


def operand_names(pe, type_definition, method_name):
    return {name for instruction in instructions(pe, type_definition, method_name)
            if (name := token_name(pe, instruction.operand))}


def strings(pe, type_definition, method_name):
    values = []
    for instruction in instructions(pe, type_definition, method_name):
        if str(instruction.opcode) != "ldstr" or not isinstance(instruction.operand, Token):
            continue
        value = pe.net.user_strings.get(instruction.operand.rid)
        if value is not None:
            values.append(str(value))
    return values


def integers(pe, type_definition, method_name):
    values = []
    aliases = {
        "ldc.i4.m1": -1, "ldc.i4.0": 0, "ldc.i4.1": 1, "ldc.i4.2": 2,
        "ldc.i4.3": 3, "ldc.i4.4": 4, "ldc.i4.5": 5, "ldc.i4.6": 6,
        "ldc.i4.7": 7, "ldc.i4.8": 8,
    }
    for instruction in instructions(pe, type_definition, method_name):
        opcode = str(instruction.opcode)
        if opcode in aliases:
            values.append(aliases[opcode])
        elif opcode in ("ldc.i4", "ldc.i4.s"):
            values.append(int(instruction.operand))
    return values


def require_calls(actual, required, label):
    missing = sorted(set(required) - actual)
    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")


def constant_value(pe, field):
    values = [row.Value.value for row in pe.net.mdtables.Constant
              if getattr(getattr(row, "Parent", None), "row", None) is field]
    if len(values) != 1:
        raise ValueError(f"expected one constant for {field.Name}")
    return int.from_bytes(values[0], "little")


def inspect(links_path, commons_path, data_path):
    links_data, links_meta = exact_bytes(links_path, "etubedatalinks.dll")
    commons_data, commons_meta = exact_bytes(commons_path, "etubecommons.dll")
    data_bytes, data_meta = exact_bytes(data_path, "etubedata.dll")
    links = dnfile.dnPE(data=links_data)
    commons = dnfile.dnPE(data=commons_data)
    if links.net is None or commons.net is None:
        raise ValueError("assembly has no CLR metadata")

    model = type_row(links, "Shimano.EtubeDataLinks", "DuE5000Unit")
    model_calls = called_names(links, model, ".cctor")
    model_names = operand_names(links, model, ".cctor")
    model_strings = strings(links, model, ".cctor")
    require_calls(model_calls, ("set_BootPatchSpec", "set_BaseFileName",
                                "set_BootloaderVersion", "set_SubstrateNo"),
                  "E5000 model boot-patch spec")
    if not {"DUE5000-D", "DUE5000-M"}.issubset(model_strings):
        raise ValueError("E5000 model firmware names mismatch")
    if "BootLoaderDcasXBaseName" not in model_names:
        raise ValueError("E5000 spec does not use BootLoaderDcasXBaseName")
    model_ints = integers(links, model, ".cctor")
    if 34 not in model_ints or model_ints.count(5) < 1:
        raise ValueError("E5000 family or boot-patch version constants mismatch")

    utility = type_row(links, "Shimano.EtubeDataLinks", "FirmwareFileUtil")
    filename_calls = called_names(links, utility, "GetBootPatchFileName")
    require_calls(filename_calls, ("get_SubstrateNo", "get_BaseFileName",
                                    "get_BootloaderVersion", "Format", "Concat"),
                  "boot-patch filename builder")
    if "-{0:X2}" not in strings(links, utility, "GetBootPatchFileName"):
        raise ValueError("boot-patch revision suffix format mismatch")
    check_calls = called_names(links, utility, "BootPatchCheckFirmwareFiles")
    require_calls(check_calls, ("get_BootPatchSpec", "get_MiconGenerationNo",
                                "get_FilePath", "Exists", "set_ValidFiles"),
                  "boot-patch file validator")

    unit = type_row(links, "Shimano.EtubeDataLinks", "Unit")
    update_calls = called_names(links, unit, "UpdateBootPatch")
    require_calls(update_calls, ("StartUpdate", "GetBootLoaderVersion",
                                  "GetNewestUpdateFileSet", "BootPatchCheckFirmwareFiles",
                                  "CompareTo", "get_BinaryData", "SendUpdateBootPatch"),
                  "boot-patch updater")
    send_calls = called_names(links, unit, "SendUpdateBootPatch")
    require_calls(send_calls, ("SendUpdateData", "EndUpdate", "ResetTarget"),
                  "boot-patch sender")

    boot_file = type_row(commons, "Shimano.EtubeCommons", "BootLoaderFirmwareFile")
    if integers(commons, boot_file, "get_FileType") != [3]:
        raise ValueError("boot-patch file type mismatch")
    if integers(commons, boot_file, ".cctor")[:4] != [4, 0, 0, 0]:
        raise ValueError("required bootloader version mismatch")
    header_names = strings(commons, boot_file, "GetEmbedInfos")
    header_ints = integers(commons, boot_file, "GetEmbedInfos")
    for name, offset in HEADER_FIELDS.items():
        if name not in header_names or offset not in header_ints:
            raise ValueError(f"boot-patch header field mismatch: {name}")
    file_type = type_row(commons, "Shimano.EtubeCommons", "FirmwareFileType")
    enum = {str(index.row.Name): constant_value(commons, index.row)
            for index in file_type.FieldList if str(index.row.Name) != "value__"}
    if enum.get("BootPatch") != 3:
        raise ValueError("FirmwareFileType.BootPatch mismatch")

    for value in ("UPDATEX", "UPDATE2I"):
        if value.encode("utf-16le") not in data_bytes:
            raise ValueError(f"etubedata.dll is missing {value}")

    return {
        "assemblies": {
            "etubedatalinks": links_meta,
            "etubecommons": commons_meta,
            "etubedata": data_meta,
        },
        "e5000_boot_patch_spec": {
            "family": 34,
            "unit": 0,
            "substrate": 1,
            "base_name": "UPDATEX",
            "revision": 1,
            "filename_stem": "1UPDATEX-01",
            "specified_bootloader_version": "5.0.0 revision 01",
        },
        "boot_patch_file": {
            "file_type": 3,
            "required_bootloader_version": "4.0.0.0",
            "header_offsets": HEADER_FIELDS,
        },
        "update_path": [
            "StartUpdate", "GetBootLoaderVersion", "GetNewestUpdateFileSet",
            "BootPatchCheckFirmwareFiles", "version CompareTo", "get_BinaryData",
            "SendUpdateData(..., true)", "EndUpdate(true)",
        ],
        "bounded_conclusion": (
            "E-TUBE 3.4.5 has a genuine E5000 boot-patch framework, but this "
            "inspection supplies no boot-patch payload and establishes no public BLE bypass"
        ),
        "limitations": [
            "the resident motor bootloader is not inspected",
            "the exact 1UPDATEX-01 payload and its version are not present in these inputs",
            "public-catalog and installer absence must be established by a separate inventory",
            "no update or bike command is performed",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("etubedatalinks", type=Path)
    parser.add_argument("etubecommons", type=Path)
    parser.add_argument("etubedata", type=Path)
    arguments = parser.parse_args()
    try:
        result = inspect(arguments.etubedatalinks, arguments.etubecommons, arguments.etubedata)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
