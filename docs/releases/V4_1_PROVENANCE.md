# v4.1 provenance and import audit

- Source conversation: `6a8811cd-4d64-83ea-817e-0c292598cf6b` (`SMC`)
- Imported archive: `moomoo_indicators_optimized_v4_1.zip`
- Archive timestamp observed in ChatGPT Library: 2026-08-28 13:11 (Asia/Shanghai)

## Verified code hashes

| Repository file | SHA-256 |
|---|---|
| `indicators/smc/SMC_STR.py` | `fb093ac3bf0fc5902c4856070085cc98749fc0c2353f633f7991d601d594048b` |
| `indicators/smc/SMC_OB.py` | `9edfdc78b8b05f826d64021c026d48f550b86f550e7b80a766e033161cdb8ab5` |
| `indicators/smc/SMC_IMB.py` | `1646482e2926cb58f5abeb27f14d770e8027f01d50650a4262bfba5a4964dcf5` |
| `indicators/ote/OTE_CP.py` | `502d96a4b3c0fc2e324ce813049a52dcb1b75687dd1fcd6aef62063492637fee` |

These four hashes match the archive's `SHA256SUMS.txt` exactly.

## Documentation checksum discrepancy

The archive's `README_CN.md`, `VALIDATION_REPORT.md`, and `CHANGELOG.md` did not match their recorded hashes, indicating they were modified after the checksum list was generated. Those files were not imported verbatim. Repository release notes were reconstructed from the conversation record and verified code behavior instead.

## Independent repository validation

After import, the repository reran syntax/plot checks, a deterministic 1,400-bar simulated moomoo Sequence runtime, 500-case current-extreme tests, 500-case OTE confirmed-pivot tests, 300 randomized OB histories, 1,500 active-slot rankings, 400 LuxAlgo structure histories, 500 ChartPrime anchor histories, 5,000 OTE geometry cases, same-bar OB mitigation, and EQH/EQL label-level checks.
