# Italian ROM support status

**Updated:** 2026-10-15<br>
**Branch:** `feature/italian-rom-support`<br>
**Base commit:** `cef04466343377836e973257175bf1ebb99c81d1`

## Goal

Import the Italian Pokémon Red ROM through a dedicated variant and manifest,
without treating USA addresses as valid Italian mappings by default.

## Manifest inventory

The last audit counted 3,279 symbols, including 2,423 text labels. Relative to
the base commit, 78 text mappings have changed. The latest import log records
`result=ok` for 77 of those changed text mappings. This count describes decoder
results in that run; it does not replace the structural evidence for each
symbol's identity.

## Structural evidence

- `_DisabledNoMoreText`: `[34, 23355]` (`22:5B3B`), structurally mapped to the
  Italian target and reached with `result=ok`.
- `_TrainerSentOutText`: `[34, 22886]` (`22:5966`), structurally demonstrated
  through its Italian `TX_FAR` wrapper, but not reached and not confirmed with
  `result=ok`.

## Latest import result

- First open error: `_DoItText: unsupported text command $AE` at `22:5CC3`.
- `_DisabledNoMoreText` returned `result=ok` immediately before this error.
- `TEST A: PASS`: **not observed**.
- `rom-cache.complete`: **absent**.
- LÖVE exit code: `1`.
- Log directory:
  `C:\gen1recomp\AItest\ROM-TestLogs\italian-20261015-disable-phaseA-11046fb2`

## Import procedure

Use the established PowerShell runner and one import at a time. Set:

```powershell
$env:POKEPORT_NO_THREAD = '1'
$env:POKEPORT_ITALIAN_IMPORT_DIAGNOSTICS = '1'
$env:POKEPORT_IDENTITY = 'test-italian-run'
$env:APPDATA = Join-Path (Get-Location) 'test-italian-run\cache-temp'
```

Run `C:\Program Files\LOVE\lovec.exe` with `test-italian-run`. Keep each
execution's logs in a new directory under
`C:\gen1recomp\AItest\ROM-TestLogs`; record stdout, stderr, process exit code,
test status, and the cache marker. Preserve old logs and cache data.

## Open work and risks

1. Determine `_DoItText`'s correct Italian interpretation or mapping from
   structural ROM and caller evidence; do not assume `$AE` is a parser defect.
2. Verify `_TrainerSentOutText` with `result=ok` only after the importer reaches
   it.
3. Keep decoder success, structural identity, full `TEST A: PASS`, and cache
   completion as separate status fields.
4. The NAS copy has not been identified; do not treat it as synchronized.

## Multi-workstation synchronization

Each workstation should use its own checkout and exchange reviewed Git history
through GitHub. Do not share or concurrently write a working tree over NAS.
The QNAP repository path and its Git state are not yet known. Before using that
copy, identify its location and inspect its branch, HEAD, and local changes.

## Updating this document

At the end of each relevant session, update the date, structural findings,
symbols with observed `result=ok`, first unresolved error, full-test result,
cache-marker state, exit code, and persistent log path. Mark unvisited symbols
as unverified. Preserve the distinction between proof from ROM structure,
observations from logs, and remaining hypotheses.
