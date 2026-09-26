# E5000 boot-patch framework in E-TUBE Project 3.4.5

Date: 2026-09-24. This is a read-only audit of exact historical desktop
assemblies. It does not contain a boot-patch payload and performs no bike I/O.

## Result

E-TUBE Project 3.4.5 contains a genuine boot-patch framework and assigns a
boot-patch specification to DU-E5000. The exact model static constructor sets:

| Field | Value |
| --- | --- |
| family / unit | 34 / 0 |
| application base name | `DUE5000-D` |
| boot-patch base name | `UPDATEX` |
| substrate | 1 |
| specified bootloader version | 5.0.0, revision/batch 01 |
| constructed filename stem | `1UPDATEX-01` |

`FirmwareFileUtil.GetBootPatchFileName` concatenates substrate, base name, and
the two-digit bootloader revision. `BootLoaderFirmwareFile` identifies the file
as `FirmwareFileType.BootPatch` (3), requires bootloader 4.0.0.0, and defines
this header:

| Offset | Field |
| ---: | --- |
| 0 | `CheckSum1` |
| 1 | `CheckSum2` |
| 2 | `CodeAreaSize` |
| 4 | `DCASVersion` |
| 5 | `MiconGenerationNo` |
| 6 | `VersionMajorMinor` |
| 7 | `VersionSubMinor` |
| 8 | `VersionRevision` |

The official `Unit.UpdateBootPatch` path starts update mode 2, reads bootloader
identity/version, obtains the newest file set, validates the BootPatch entry,
and calls `SendUpdateBootPatch` only when the file version is newer than the
reported bootloader. The sender reuses `SendUpdateData(..., true)` and finishes
with `EndUpdate(true)`.

## Artifact search boundary

The E-TUBE 3.4.5 application directory contains the `UPDATEX` and `UPDATE2I`
framework strings but no corresponding file. A bounded inventory of public
client catalogs from 2.2.3 through 3.4.5 (including the debug catalog), the
archived public installers from 2.2.3 through 3.4.5, likely 5.x filename URLs,
Wayback/Common Crawl indexes, GitHub/Sourcegraph references, and the Reven
firmware corpus found no `1UPDATEX-01` or other `UPDATEX`/`UPDATE2I` payload.
Known DUE5000 firmware URLs were rechecked as positive controls during the
filename sweep.

That is bounded negative evidence, not proof that the file never existed. The
path may have been dealer/recovery-only, distributed through another catalog,
or left dormant in this client generation. Without the exact payload, it is not
an actionable bootloader dump, unlock, or recovery route.

## Reproducibility and limits

`tools/inspect_etube_boot_patch.py` verifies the exact assembly hashes, E5000
spec, filename construction, update call chain, boot-patch file type, required
version, and header layout. It requires `dnfile` and `dncil`; vendor assemblies
remain outside Git.

This framework does not establish a public BLE bootloader patch, a flash-read
primitive, modified-application acceptance, or recovery from an unbootable
motor application. It therefore does not remove the risk of the local
D4.5.0.1 experiment. The stock D4.3.0/M4.2.1 BLE preparation route remains the
lower-risk software path because it uses exact public firmware that the current
eTuning client explicitly allowlists.
