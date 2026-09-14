# Asset inventory and retrieval

All files needed to understand the current conclusion and run synthetic tests
are in this repository. The old external analysis folder is **not** a build,
test, or handoff dependency. Large/proprietary binaries and private captures
are intentionally excluded from public Git; no file currently requires Git
LFS. The links below are historical acquisition sources, not a recommendation
to install firmware. Check availability and hash any fresh download before
using it. The hashes describe bytes examined during this investigation.

| Asset | Source / access | Size | SHA-256 | Purpose |
| --- | --- | ---: | --- | --- |
| E-TUBE Professional 5.3.4 ZIP | [archive download](https://assets.bettershifting.com/archive/E-tube_Proj_V_5_3_4.zip), [archive index](https://bettershifting.com/e-tube-project-archive/) | 309,035,074 | `004883e032a6f343e5c11d9b8b45b7f7c77e47ca5dd7259f488f913f6aaede4f` | Desktop IL and original-version D/M image source; mirror authenticity is not a vendor signature |
| E-TUBE Professional 4.0.2 ZIP | [archive index](https://bettershifting.com/e-tube-project-archive/) | 180,864,996 | `903a343e2fde116b36846045267c9953d64535a9ed49a9adde864f18c9b56960` | Historical D4.3.0/M4.2.1 comparison; not a validated path for this bike |
| eTuning E5000 historical preparation ZIP | [download](https://etuning-app.com/wp-content/uploads/2024/11/5000_430.zip), [guide](https://etuning-app.com/downgrade.pdf) | 146,098 | `4dee4d75ee83c22e951114cbf57332709c15be637ec2a8171bd82f9345adb137` | Historical preparation comparison, not installed |
| D4.5.0 original DAT from 5.3.4 | Extract from exact archive above | 138,132 | `363a43fc6997d384e0d723fa241b034146365e7c48f1fc8cfda027a948c5a6a7` | Native baseline image; never sent to bike |
| M4.4.8 original DAT from 5.3.4 | Extract from exact archive above | 119,824 | `9ea350e988345a9d9fb41c1363562ca190f1a8d5e1cc8a38c6373f69b877f033` | Native baseline image; never sent to bike |
| D4.5.0 unwrapped analysis image | Derive from the original D DAT using the eTuning asset wrapper; see `RESEARCH.md` | 138,072 | `44806bd54aedff95a88bb73fafe0f0581297f2f67b2ea35545cea012899d90bb` | D handler analysis; selected excerpts committed in `docs/evidence/` |
| eTuning 1.0.32 and 3.0.7 XAPKs | User-supplied APKCombo packages; exact filenames/sizes/hashes in [`docs/evidence/source-artifact-hashes.json`](docs/evidence/source-artifact-hashes.json) | 2,215,339 / 7,228,364 | See manifest | Client policy and direct `A8` call; original package not needed for current conclusion |
| `ShimanoBleProbe.zip` | User-supplied; exact fingerprint in the same manifest | 6,940 | See manifest | Earlier read-only probe source |
| Android bugreport ZIP / `btsnoop_hci.log` | Private user-supplied capture; bugreport fingerprint in the same manifest | 39,638,877 / 115,513 | Bugreport: manifest; snoop: `144a3bece6e0f8a6546cc641311ce619d21751dc7a31a4a8278078970e21c45b` | Session-auth and transport observations; contains identifiers and authentication material, so excluded |
| SC-E7000 4.1.0 display image | [recorded catalog URL](https://api.shimano.com/etube/public/data/upload/published/SCE7000.4.1.0.dat) | 126,508 according to catalog | Not available locally; catalog MD5 `4974d4f471b126be9f9657510e6bef55` | Missing bridge-mapping evidence; URL returned HTTP 403 on 2026-09-12 |

The official [SC-E7000 user manual](https://si.shimano.com/en/pdfs/um/79H0B/UM-79H0B-000-ENG.pdf)
is the source for the display's Adjust, Shift timing, and RD protection reset
menu meanings. The [eTUBE API firmware catalog](https://github.com/reven-project/etubeapi/blob/master/fw-scraped.yml)
corroborates historical hashes but is not an authenticity guarantee.

The curated textual evidence is deliberately small. `d450-*.c` are selected
Ghidra decompilation outputs for the D4.5.0 image, and `etube-*.il` are selected
managed IL excerpts. Their function names/addresses are analyzer labels, and
the candidate sequence in `d450-destination-analysis.md` is historical and
explicitly superseded by its final correction. No binary package, whole
decompilation, or secret-bearing raw trace must be present to reproduce the
handoff's *current negative conclusion*. Further bridge reconstruction may
require acquiring new private evidence.
