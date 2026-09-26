#!/usr/bin/env python3
"""Verify the exact E-TUBE 3.4.5 Renesas loader command/write path.

The vendor assembly stays outside Git. This read-only checker requires the
``dnfile`` and ``dncil`` Python packages, accepts only the exact assembly
fingerprinted in ASSETS.md, and emits metadata/IL facts without dumping code or
firmware bytes. It does not inspect the resident loader inside the motor.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

try:
    import dnfile
    from dncil.cil.body.reader import read_method_body_from_bytes
    from dncil.clr.token import Token
except ImportError as error:  # pragma: no cover - environment dependency
    raise SystemExit("install dnfile and dncil in an isolated environment") from error


ASSEMBLY_SIZE = 851_456
ASSEMBLY_SHA256 = "814d8096d9f6e5552d8131ff840d3bf407b0f0b089c9a0a821cbb34f141e5ab5"

COMMANDS = {
    "Start": 0x21,
    "FirmVer": 0x22,
    "EraseCnt": 0x23,
    "WriteAddressSet": 0x24,
    "CheckSum": 0x25,
    "ClearCheckSum": 0x26,
    "Finish": 0x27,
    "Reset": 0x28,
    "SerialNumberLow": 0x29,
    "SerialNumberHigh": 0x2A,
    "BootVer": 0x41,
    "NormalResponse": 0x31,
    "ErrorResponse": 0x32,
    "FirmVerResponse": 0x33,
    "EraseCntResponse": 0x34,
    "SerialNumberLowResponse": 0x35,
    "SerialNumberHighResponse": 0x36,
    "BootVerResponse": 0x51,
}

COMMAND_METHODS = {
    "SendReceiveStartCommand": (0x21, 0x31),
    "SendRecieveFirmVerCommand": (0x22, 0x33),
    "SendRecieveEraseCntCommand": (0x23, 0x34),
    "SendRecieveWriteAddressSetCommand": (0x24, 0x31),
    "SendRecieveCheckSumCommand": (0x25, 0x31),
    "SendRecieveClearCheckSumCommand": (0x26, 0x31),
    "SendRecieveFinishCommand": (0x27, 0x31),
    "SendRecieveResetCommand": (0x28, 0x31),
    "SendRecieveSerialNumberLowCommand": (0x29, 0x35),
    "SendRecieveSerialNumberHighCommand": (0x2A, 0x36),
    "SendRecieveBootVerCommand": (0x41, 0x51),
}


def type_row(pe, namespace, name):
    matches = [row for row in pe.net.mdtables.TypeDef
               if str(row.TypeNamespace) == namespace and str(row.TypeName) == name]
    if len(matches) != 1:
        raise ValueError(f"expected one type {namespace}.{name}, found {len(matches)}")
    return matches[0]


def method_rows(type_definition, name):
    return [index.row for index in type_definition.MethodList if str(index.row.Name) == name]


def constant_value(pe, field):
    values = [row.Value.value for row in pe.net.mdtables.Constant
              if getattr(getattr(row, "Parent", None), "row", None) is field]
    if len(values) != 1:
        raise ValueError(f"expected one constant for {field.Name}")
    return int.from_bytes(values[0], "little")


def enum_values(pe, name):
    enum = type_row(pe, "", name)
    return {str(index.row.Name): constant_value(pe, index.row) for index in enum.FieldList}


def body(pe, method):
    if not method.Rva:
        raise ValueError(f"method {method.Name} has no IL body")
    return read_method_body_from_bytes(pe.get_data(method.Rva))


def explicit_integer_constants(pe, method):
    result = []
    for instruction in body(pe, method).instructions:
        if str(instruction.opcode) in ("ldc.i4", "ldc.i4.s"):
            result.append(int(instruction.operand))
    return result


def token_name(pe, operand):
    if not isinstance(operand, Token):
        return None
    tables = {0x06: pe.net.mdtables.MethodDef, 0x0A: pe.net.mdtables.MemberRef}
    table = tables.get(operand.table)
    if table is None or operand.rid < 1 or operand.rid > len(table.rows):
        return None
    return str(table.rows[operand.rid - 1].Name)


def called_names(pe, type_definition, method_name):
    names = set()
    methods = method_rows(type_definition, method_name)
    if not methods:
        raise ValueError(f"method {type_definition.TypeName}.{method_name} not found")
    for method in methods:
        for instruction in body(pe, method).instructions:
            if str(instruction.opcode) not in ("call", "callvirt", "newobj"):
                continue
            name = token_name(pe, instruction.operand)
            if name:
                names.add(name)
    return names


def require_calls(actual, required, label):
    missing = sorted(set(required) - actual)
    if missing:
        raise ValueError(f"{label} call chain is missing: {', '.join(missing)}")


def inspect(path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != ASSEMBLY_SIZE or digest != ASSEMBLY_SHA256:
        raise ValueError(f"{path.name}: not the exact recorded E-TUBE 3.4.5 etubedatalinks.dll")
    pe = dnfile.dnPE(data=data)
    if pe.net is None:
        raise ValueError("assembly has no CLR metadata")

    commands = enum_values(pe, "BootloaderCommandCodes")
    if commands != COMMANDS:
        raise ValueError("BootloaderCommandCodes enum mismatch")

    utils = type_row(pe, "Shimano.EtubeDataLinks", "RenesasMicomUtils")
    method_evidence = {}
    for name, expected in COMMAND_METHODS.items():
        methods = method_rows(utils, name)
        if len(methods) != 1:
            raise ValueError(f"expected one {name} method")
        constants = explicit_integer_constants(pe, methods[0])
        if not all(value in constants for value in expected):
            raise ValueError(f"{name} command/reply constants mismatch")
        method_evidence[name] = {
            "command": f"0x{expected[0]:02x}",
            "expected_reply": f"0x{expected[1]:02x}",
        }

    main = type_row(pe, "Shimano.EtubeDataLinks", "EtubeDataLinksMain")
    update_calls = called_names(pe, main, "UpdateRenesasFirmware")
    require_calls(update_calls, ("SendReceiveStartCommand", "SendRenesasFWData",
                                  "SendRecieveFinishCommand", "SendRecieveResetCommand"),
                  "outer update")
    write_calls = called_names(pe, main, "SendRenesasFWData")
    require_calls(write_calls, ("SendRecieveWriteAddressSetCommand",
                                 "SendRecieveClearCheckSumCommand",
                                 "SendRenesasDataPacket", "SendRecieveCheckSumCommand"),
                  "data write")
    unit = type_row(pe, "Shimano.EtubeDataLinks", "Unit")
    source_calls = called_names(pe, unit, "UpdateRenesasFirmware")
    require_calls(source_calls, ("get_BinaryData", "UpdateRenesasFirmware"), "binary source")

    reviewed_calls = update_calls | write_calls | source_calls
    direct_crypto_calls = sorted(name for name in reviewed_calls
                                 if re.search(r"(?:crypt|signature|rsa|ecdsa|sha|md5)", name, re.I))
    if direct_crypto_calls:
        raise ValueError("unexpected direct cryptographic call in reviewed raw-write path")

    command_names = set(commands)
    flash_read_members = sorted(name for name in command_names
                                if "read" in name.lower() and "serial" not in name.lower())
    if flash_read_members:
        raise ValueError("unexpected flash-read member in exact loader enum")

    return {
        "source": path.name,
        "assembly": {"size": len(data), "sha256": digest},
        "loader_commands": {name: f"0x{value:02x}" for name, value in commands.items()},
        "command_methods": method_evidence,
        "write_path": {
            "outer_calls": sorted(set(("SendReceiveStartCommand", "SendRenesasFWData",
                                        "SendRecieveFinishCommand", "SendRecieveResetCommand")) & update_calls),
            "data_calls": sorted(set(("SendRecieveWriteAddressSetCommand",
                                       "SendRecieveClearCheckSumCommand", "SendRenesasDataPacket",
                                       "SendRecieveCheckSumCommand")) & write_calls),
            "host_binary_source": "get_BinaryData",
            "direct_crypto_calls": direct_crypto_calls,
        },
        "bounded_conclusion": (
            "the exact desktop client exposes no flash-read loader command and its raw update "
            "path sends host binary data through address, data, additive-checksum, finish and reset operations; "
            "no separate signature operation appears in this reviewed call chain"
        ),
        "limitations": [
            "the command inventory is the exact E-TUBE 3.4.5 client implementation, not resident-loader code",
            "absence of a client-side command does not mathematically exclude an undocumented device opcode",
            "a resident loader can perform an internal computed or externally stored integrity check",
            "modified-image acceptance, boot, BLE recovery and bike behavior remain unproved",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assembly", type=Path)
    arguments = parser.parse_args()
    try:
        result = inspect(arguments.assembly)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
