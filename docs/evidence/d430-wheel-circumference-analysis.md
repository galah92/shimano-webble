# DU-E5000 D4.3.0 wheel-circumference BLE fallback

Date: 2026-09-24. This is an offline client/protocol analysis and a synthetic
transaction implementation. No command or firmware was sent to the bike.

## Result

The exact stock D4.3.0/M4.2.1 preparation state exposes a second, independent
software-only speed route: change the circumference represented to the motor.
This does **not** set the destination to US. It raises the real cutoff by making
the motor calculate a lower speed, so the bike display and accumulated distance
become proportionally low. US remains the preferred result because its 32 km/h
mode keeps those readings correct.

For an actual circumference `C`, nominal cutoff `Vn`, and desired real cutoff
`Vt`, the represented circumference is:

```text
represented_mm = round(C * Vn / Vt)
```

For example, an actual 2080 mm wheel, a 25 km/h nominal cutoff, and a 32 km/h
target gives 1625 mm. The display/distance ratio becomes `1625/2080 = 0.78125`;
when the bike is really moving at 32 km/h it will indicate about 25 km/h. This
is only a calculated expectation until a controlled ride measures the actual
assistance cutoff.

## Exact Android protocol evidence

The audited eTuning 3.0.7 XAPK and base APK fingerprints are recorded in
[`ASSETS.md`](../../ASSETS.md). In its complete JADX output:

- `C0534Q5` issues the old-generation getter `00 35 04 00`.
- `AbstractC0288In` parses the matching notification `00 35 06 lo hi` and
  stores `lo | hi << 8`.
- `C1463qn.m6524i0(int)` and `C1459qj` construct the setter
  `00 35 00 lo hi` and write it to `2AFE`.
- `AbstractC0288In` treats `00 35 02 ...` as the setter-success notification.
- the newer GATT helper `C1584u9.m6966y(int, ...)` reads the current value,
  writes only if different, waits 150 ms, re-reads, and reports success only
  when the returned integer equals the request.
- `ActivityC1037ka` constrains the UI to 1300–3000 mm.

This is stronger than a UI claim: it establishes the exact getter, setter,
endianness, success opcode, range, and immediate equality check in an exact
client. It does not prove that this bike accepts the setter after preparation.

## Independent public evidence

- Shimano's [archived product specification](https://productinfo.shimano.com/pdfs/product/archive/2024-2025_Specifications_v032_en.pdf)
  lists DU-E5000 compatible wheel size as 1300–3000 mm and lists both 25 km/h
  and 20 mph support.
- eTuning's [downgrade guide](https://etuning-app.com/downgrade.pdf) identifies
  E5000 4.3.0 as supporting wheel/region changes, distinguishes inaccurate
  wheel-based speed from accurate 32 km/h US mode, and says region/wheel values
  are retained when firmware is updated again.
- [STUnlocker](https://www.stunlocker.com/) independently gives E5000 4.3.0 as
  the last Bluetooth-compatible version for both destination and circumference.
- eMax's [current compatibility document](https://www.emax-tuning.com/eMax-possibilities.pdf)
  independently lists Bluetooth destination and circumference changes for
  DU-E50X0 4.2.1–4.3.0 and explains the incorrect speed/distance consequence.
- the historical [STUnlocker manual](https://www.readkong.com/page/user-manual-version-1-9-x-for-android-devices-5503878)
  warns that E5000 settings may reset after power-off. That older warning is
  why a same-session readback is insufficient despite eTuning's newer retention
  statement.

The commercial sources are compatibility/outcome evidence, not protocol proof;
the exact APK supplies the packet-level evidence.

## Local implementation

Build 87 adds an intentionally unwired branch to [`index.html`](../../index.html):

- exact read/write packet builders and a fail-closed reply parser;
- a calculation helper constrained to the motor's 1300–3000 mm range;
- a distinct same-device durable journal persisted before the only setter;
- no retry after rejection, timeout, disconnect, or malformed result;
- read-only resolution of an uncertain write in another BLE session; and
- a separate physical-power-cycle persistence check on the same salted motor
  identity and exact D4.3.0/M4.2.1 EU baseline.

[`tests/wheel_fallback_transaction.cjs`](../../tests/wheel_fallback_transaction.cjs)
uses generated firmware bytes and simulated reads/writes. It verifies the exact
packets, 2080→1625 calculation, one-write guard, uncertain-result resolution,
same-device binding, and persistence gate. It contains no vendor binary or bike
credential.

The branch has no UI caller and does not yet authorize D4.5.0 restoration. The
next live evidence, if separately authorized, must be staged:

1. prove the exact preparation pair and original circumference;
2. issue one setter and require immediate equality;
3. power-cycle and read again without retrying; and
4. independently prove that the getter still works on restored D4.5.0 before
   extending the restoration/final-verification state machine.

Until those gates pass, this is a strong fallback design—not a validated bike
result. Modified assistance limits may be illegal on public roads and can alter
the bicycle's approval, warranty, braking assumptions, and displayed telemetry.

## 2026-09-27 stock-D4.5.0 correction

The exact stock D4.5.0 image **retains** handlers for combined packet keys
`0x0035` (`35 00`, wheel setter) and `0x0435` (`35 04`, getter), despite the
commercial BLE compatibility tables ending wheel adjustment at D4.3.0. The
setter handler at `0x1e13c` checks the global nonzero PC-mode byte, a nonzero
16-bit packet value, and a source-state relation involving RAM `0x20002168`
offsets `+0x1e` and `+0x18`. Only then does `0x18e38` stage persistent record
`0x1f`, commit, verify, and update the live value. The getter dispatches to
`0x1e1bc`, which schedules a response. The exact-hash, no-image-output check is
[`tools/inspect_d450_wheel.py`](../../tools/inspect_d450_wheel.py).

This corrects a possible over-reading of the vendor version matrix: the native
handler did not simply disappear in D4.5.0. It does **not** establish that the
SC-E7000 forwards the setter in the needed source state, that the bike will
accept it over BLE, or that it raises real cutoff on this topology. The safe
next discriminator for this branch is only a `35 04` read on stock firmware;
no D4.5 wheel write is wired or authorized by this static finding. A wheel
workaround would also misreport speed and distance, unlike a true US region.
