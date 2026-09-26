#!/usr/bin/env python3
"""Verify two clients' DU-E5000 maximum-assist-speed implementations.

The APK and JADX output remain outside the repository. This checker pins the
optional APK to the fingerprint recorded in ASSETS.md, then verifies the exact
decompiled source shapes behind the B0/B2, B4/B6, and BC/BE conclusions. It is
read-only and never prints vendor source or package contents. An optional
eTuning 3.0.7 pass independently verifies its destination-success -> 350 ms ->
B0 chain.
"""
import argparse
import hashlib
from pathlib import Path


APK_SIZE = 115_738_926
APK_SHA256 = "b9b0ccb924f0dd1931beaada10501791b77268e4364bdb871010cd36ca606db2"
ETUNING_APK_SIZE = 7_060_465
ETUNING_APK_SHA256 = "d4d545150f025760a13bf3bcade148f278731a1d49bf59d1e9da338723c90e22"

ROOT = Path("com/shimano/etubeproject/sharedcode")
FILES = {
    "e5000": ROOT / "domain/model/unit/category/du/DUE5000Unit.java",
    "commands": ROOT / "domain/model/etubedata/UnitCommandDefine.java",
    "data_link": ROOT / "domain/model/unit/core/steps/DUUnitDataLink.java",
    "destination": ROOT / "domain/model/customize/du/DestinationType.java",
    "options": ROOT / "domain/model/customize/du/DUCustomizeOptions.java",
    "writer": ROOT / "domain/model/customize/readwriter/du/DUUnitReadWriter.java",
    "presenter": ROOT / "presentation/customizedu/CustomizeDUPresenter.java",
}

ETUNING_FILES = {
    "activity": Path(
        "eTuning/shimano/steps/p002ui/p003ea/ActivityC1041w.java"
    ),
    "runner": Path("p000/RunnableC0168F2.java"),
    "completion": Path("p000/RunnableC0597S3.java"),
    "dispatcher": Path("p000/AbstractC0288In.java"),
    "writer": Path("p000/C1463qn.java"),
    "range": Path("p000/AbstractC0310Jc.java"),
}


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def require(text, fragments, label):
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label}: expected Cyclist 5.0.2 source shape is missing")


def require_etuning(text, fragments, label):
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label}: expected eTuning 3.0.7 source shape is missing")


def inspect(sources, apk=None):
    if apk is not None:
        if apk.stat().st_size != APK_SIZE or digest(apk) != APK_SHA256:
            raise ValueError("APK fingerprint mismatch")

    loaded = {}
    for label, relative in FILES.items():
        path = sources / relative
        if not path.is_file():
            raise ValueError(f"missing JADX source: {relative}")
        loaded[label] = path.read_text(encoding="utf-8")

    require(loaded["e5000"], (
        'public static final String MODEL_NO = "DU-E5000";',
        "this.canSetMaxAssistSpeed = true;",
    ), "DU-E5000 capability")
    require(loaded["commands"], (
        "DCC_CMD_PU_MD_MAX_ASSIST_SPD_DEST_GET_C = -68;",  # BC
        "DCC_CMD_PU_MD_MAX_ASSIST_SPD_DEST_GET_R = -66;",  # BE
        "DCC_CMD_PU_MD_MAX_ASSIST_SPD_GET_C = -76;",       # B4
        "DCC_CMD_PU_MD_MAX_ASSIST_SPD_GET_E = -73;",       # B7
        "DCC_CMD_PU_MD_MAX_ASSIST_SPD_GET_R = -74;",       # B6
        "DCC_CMD_PU_MD_MAX_ASSIST_SPD_SET_C = -80;",       # B0
    ), "maximum-assist command constants")
    require(loaded["data_link"], (
        "new UnitCommandSetting(b, (byte) 22, (byte) -76, new byte[]{0})",
        "new UnitCommandSetting(b, (byte) 22, (byte) -80, bArr)",
        "byte b2 = (byte) 255;",
        "bArrM115uShortToByteArrayxj2QHRw[0], bArrM115uShortToByteArrayxj2QHRw[1], b2, b2",
        "new UnitCommandSetting(b, (byte) 22, (byte) -68, bArr)",
        "new byte[]{parameters[0], parameters[1]}",
        "new byte[]{parameters[1], parameters[2]}",
    ), "getter/setter packet construction")
    require(loaded["destination"], (
        "EU((byte) 0)",
        "US((byte) 1)",
    ), "destination mapping")
    require(loaded["options"], (
        "readDestinationType(",
        "m107getMaxAssistSpeedForDestinationXRpZGF0(slotNo, value",
        "setDefaultMaxAssistSpeed(Boxing.boxInt(iIntValue / 100))",
    ), "destination-specific default flow")
    require(loaded["writer"], (
        "return Boxing.boxInt(numBoxInt.intValue() / 100);",
        "UShort.m699constructorimpl((short) (i * 100))",
    ), "hundredths-of-km/h conversion")
    require(loaded["presenter"], (
        "makeDefaultSettings()",
        "setMaxAssistSpeed(this.duOptions.getDefaultMaxAssistSpeed())",
        "writeMaxAssistSpeedKM(iIntValue, this)",
    ), "Reset/Apply flow")

    print("Cyclist 5.0.2 DU-E5000 maximum-assist implementation verified")
    print("  capability: maximum-assist customization enabled")
    print("  protocol: B4/B6 current, BC/BE per destination, B0 setter")
    print("  units: little-endian hundredths of km/h")
    print("  workflow: destination-specific default is staged, then Apply writes it")


def inspect_etuning(sources, apk=None):
    if apk is not None:
        if (apk.stat().st_size != ETUNING_APK_SIZE
                or digest(apk) != ETUNING_APK_SHA256):
            raise ValueError("eTuning base APK fingerprint mismatch")

    loaded = {}
    for label, relative in ETUNING_FILES.items():
        path = sources / relative
        if not path.is_file():
            raise ValueError(f"missing eTuning JADX source: {relative}")
        loaded[label] = path.read_text(encoding="utf-8")

    require_etuning(loaded["activity"], (
        "public static void m5512A()",
        "new RunnableC0597S3(17)",
        "public final void m5514C(String str, boolean z)",
        "if (z) {",
        "m5522K();",
        "new byte[]{0, 22, -88, 1, (byte) AbstractC0288In.f1341m.f2911s0}",
        "int iM1671e = AbstractC0310Jc.m1671e(c0696v3);",
        "new RunnableC0168F2(this, c1463qn, iM1671e, c0696v3)",
    ), "destination-success continuation")
    require_etuning(loaded["dispatcher"], (
        "case -86:",  # AA, the A8 success reply
        "if (bArr[0] == 0 && bArr[1] == 22)",
        "ActivityC1041w.m5512A();",
    ), "A8 success dispatch")
    require_etuning(loaded["completion"], (
        "ActivityC1041w activityC1041w = ActivityC1041w.f6106J;",
        "activityC1041w.m5514C(null, true);",
    ), "successful region callback")
    require_etuning(loaded["runner"], (
        "public RunnableC0168F2(ActivityC1041w activityC1041w, C1463qn c1463qn, int i, C0696V3 c0696v3)",
        "Thread.sleep(350L);",
        "((C1463qn) this.f743d).m6515Z(i2, AbstractC0310Jc.m1669c(c0696v4));",
    ), "delayed maximum-speed continuation")
    require_etuning(loaded["writer"], (
        "public final void m6515Z(int i, boolean z)",
        "int iM1667a = AbstractC0310Jc.m1667a(i, AbstractC0288In.f1341m) * 100;",
        "m6500K(sb2.toString(), new byte[]{0, 22, -80, b, b2, -1, -1});",
    ), "old-generation B0 writer")
    require_etuning(loaded["range"], (
        "public static int m1671e(C0696V3 c0696v3)",
        "if (i == 1) {",
        "return 32;",
        "return i == 5 ? 45 : 25;",
    ), "destination maximum table")

    print("eTuning 3.0.7 old-generation maximum-assist continuation verified")
    print("  destination: direct A8 with the selected destination")
    print("  continuation: successful destination result starts a 350 ms delay")
    print("  protocol: B0 setter with little-endian hundredths of km/h")
    print("  US target: 32 km/h")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", type=Path,
                        help="JADX sources directory for the exact Cyclist 5.0.2 APK")
    parser.add_argument("--apk", type=Path,
                        help="optional original APK; exact size and SHA-256 are required")
    parser.add_argument("--etuning-sources", type=Path,
                        help="optional JADX sources directory for exact eTuning 3.0.7")
    parser.add_argument("--etuning-apk", type=Path,
                        help="optional exact eTuning 3.0.7 base APK")
    args = parser.parse_args()
    inspect(args.sources, args.apk)
    if args.etuning_apk is not None and args.etuning_sources is None:
        parser.error("--etuning-apk requires --etuning-sources")
    if args.etuning_sources is not None:
        inspect_etuning(args.etuning_sources, args.etuning_apk)


if __name__ == "__main__":
    main()
