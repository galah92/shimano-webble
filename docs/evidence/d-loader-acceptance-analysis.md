# D loader command and modified-image acceptance analysis

This note records a bounded static audit of the exact E-TUBE Project 3.4.5
managed loader implementation and the recovered eTuning Android updater. It
does not contain a vendor binary or a private capture, and no command was sent
to the bike.

## Complete desktop command inventory

The exact `etubedatalinks.dll` recorded in `ASSETS.md` contains the nested
`RenesasMicomCommandDefine.BootloaderCommandCodes` enum and one corresponding
helper per request:

| Request | Value | Expected reply |
| --- | ---: | ---: |
| start | `21` | `31` |
| firmware version | `22` | `33` |
| erase count | `23` | `34` |
| set write address | `24` | `31` |
| validate partial byte-sum | `25` | `31` |
| clear partial byte-sum | `26` | `31` |
| finish with whole-image byte-sum | `27` | `31` |
| reset | `28` | `31` |
| serial low | `29` | `35` |
| serial high | `2A` | `36` |
| bootloader version | `41` | `51` |

The enum also names error reply `32`. There is no flash-read, range-read, dump,
signature, key, or authentication command in the exact client inventory.
`tools/inspect_etube_d_loader.py` verifies the assembly fingerprint, enum
values, request/reply constants, and bounded IL call chain. It requires
`dnfile` and `dncil` in an isolated Python environment.

This is stronger than a string search but remains client-bounded: an
undocumented opcode could exist in the resident loader without being used or
named by E-TUBE.

## Exact host write path

The managed call chain is:

```text
Unit.UpdateRenesasFirmware
  -> RenesasFirmwareFile.get_BinaryData
  -> EtubeDataLinksMain.UpdateRenesasFirmware
       -> SendReceiveStartCommand
       -> SendRenesasFWData
            -> SendRecieveWriteAddressSetCommand
            -> SendRecieveClearCheckSumCommand
            -> SendRenesasDataPacket
            -> SendRecieveCheckSumCommand
       -> SendRecieveFinishCommand
       -> SendRecieveResetCommand
```

`SendRenesasFWData` pads only the final block, maintains an additive byte-sum,
and supplies that sum to the checksum helper. The outer worker supplies the
whole-image sum to finish. The reviewed raw-write chain has no separate
signature or cryptographic-verification call. The DAT wrapper parsing and its
host-side integrity checks happen before `get_BinaryData`; the resident loader
receives the resulting raw application bytes.

The eTuning 2.0.7, 2.0.8, and 3.0.7 clients independently expose the same
write-only shape. Across those exact decompilations, loader requests are setup
`06`-`09`, bank `0A`, start `21`, address `24`, finish `27`, reset `28`,
identity/version queries `29`, `2A`, `2E`, `2F`, `30`, plus block data. No
memory-read request is constructed. The older desktop and newer mobile reply
layouts differ, but neither client supplies a backup primitive.

## What this changes

The result increases confidence in the five-byte D4.5.0.1 branch:

- the official client sends host-selected raw application bytes;
- the visible device integrity contract is block byte-sums plus one final
  whole-image byte-sum;
- no client-side public-key signature or second raw-image authenticator is in
  the reviewed path; and
- the exact raw D4.5 image has no identified appended signature trailer or
  application-startup self-check.

It does **not** prove acceptance. The resident motor loader is below the raw
application image and remains unavailable. It could compute an implicit hash,
consult external metadata, enforce a version policy, or reject modified bytes
without a separate host command. Because the client inventory has no flash
read, BLE cannot first back up that resident loader or the current application.

## Resulting experiment boundary

Build 85 therefore keeps the public/current-firmware A0/A8 sequence unchanged
and wires only an offline coordinator for the exact derived pair:

1. require stock D4.5.0/M4.4.8 at EU, a fresh application identity, and the
   previously verified D-loader fingerprint;
2. derive D4.5.0.1 in memory from the exact stock D image and pair it with
   unchanged M4.4.8;
3. persist a same-device recovery journal before update entry;
4. transfer complete M then D workers, with complete-pair replay available on
   interruption;
5. reset and require a different BLE session to report D4.5.0.1/M4.4.8 before
   one destination transaction;
6. require immediate US readback and a separate physical-power-cycle
   persistence readback; and
7. accept stock restoration only from the same journaled motor and verified
   patched-US lineage, then prove D4.5.0/M4.4.8 plus US again.

The coordinator has no UI caller and does not authorize a bike write. Synthetic
tests prove exact derivation, unchanged M bytes, paired ordering, complete-pair
replay, version-marker gating, one US write, persistence lineage, and stock
restoration lineage. The dominant unresolved risk is still loss of BLE
recoverability if the resident loader accepts the transfer but the patched
application does not boot.
