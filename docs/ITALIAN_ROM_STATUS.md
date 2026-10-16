# Italian ROM support status

**Updated:** 2026-10-16<br>
**Branch:** `feature/italian-rom-support`<br>
**Base commit:** `cef04466343377836e973257175bf1ebb99c81d1`

## Goal

Import the Italian Pokémon Red ROM through a dedicated variant and manifest,
without treating USA addresses as valid Italian mappings by default.

## Manifest inventory

The last audit counted 3,279 symbols, including 2,423 text labels. Relative to
the base commit, 89 text mappings have changed. The latest import log records
`result=ok` for 88 of those changed text mappings. This count describes decoder
results in that run; it does not replace the structural evidence for each
symbol's identity.

## Structural evidence

- `_DisabledNoMoreText`: `[34, 23355]` (`22:5B3B`), structurally mapped to the
  Italian target and reached with `result=ok`.
- `_TrainerSentOutText`: `[34, 22886]` (`22:5966`), structurally demonstrated
  through its Italian `TX_FAR` wrapper, but not reached and not confirmed with
  `result=ok`.
- `_DoItText`: `[34, 24235]` (`22:5EAB`, file offset `0x89EAB`). The Italian
  send-out dispatch at `16:4E90` selects wrapper `16:4EB5` for the 40–69% HP
  branch. Its bytes `17 AB 5E 22 08 18 0C` point to `22:5EAB` via `TX_FAR`,
  then continue through `text_asm`. The target bytes
  `00 83 A0 A8 E7 7F 50 50` start a text stream for «Dai! », terminate before
  the next wrapper target at `22:5EB3`, and contain no dynamic RAM command.
  The importer reached this mapping with `result=ok`.

### Batch 7: structurally mapped and import verified

Each row was checked against Italian ROM references, target boundaries and
manifest collisions, then observed as `result=ok` in its own import run.

| Symbol | Previous | Italian target | Structural reference |
| --- | --- | --- | --- |
| `_EnemyMonFaintedText` | `[34, 22215]` | `[34, 22648]` (`22:5878`) | Battle wrapper `0F:463E`, `TX_FAR` |
| `_EnemyRanText` | `[34, 22135]` | `[34, 22550]` (`22:5816`) | Enemy escape wrapper `0F:422E`, `TX_FAR` |
| `_EnemysWeakText` | `[34, 23766]` | `[34, 24251]` (`22:5EBB`) | Low HP dispatch wrapper `16:4EC3`, `TX_FAR` |
| `_EnoughText` | `[34, 23805]` | `[34, 24288]` (`22:5EE0`) | Retreat dispatch wrapper `16:4F25`, `TX_FAR` |
| `_EvolvedText` | `[37, 18114]` | `[37, 18312]` (`25:4788`) | Evolution wrapper `0E:6F78`, `TX_FAR` |
| `_ExpPointsText` | `[34, 23534]` | `[34, 24000]` (`22:5DC0`) | Experience dispatch wrapper `15:54D8`, `TX_FAR` |
| `_FightingDojoKarateMasterStayAndTrainWithUsText` | `[40, 22898]` | `[40, 23059]` (`28:5A13`) | Dojo defeated branch wrapper `17:4E9D`, `TX_FAR` |
| `_FoundHiddenCoins2Text` | `[34, 21795]` | `[34, 22165]` (`22:5695`) | Full Coin Case wrapper `1D:68C4`, `TX_FAR` |
| `_FoundHiddenCoinsText` | `[34, 21771]` | `[34, 22139]` (`22:567B`) | Normal coin retrieval wrapper `1D:68BE`, `TX_FAR` |
| `_FoundHiddenItemText` | `[34, 21712]` | `[34, 22075]` (`22:563B`) | Hidden item pickup wrapper `1D:67D2`, `TX_FAR` |

The hidden coin texts have similar contents but distinct wrapper references.
The existing dynamic metadata for the coin amount and hidden item name remained
unchanged. `_TrainerSentOutText` still has no observed `result=ok`.

## Latest import result

- First open error: `_FuchsiaGoodRodHouseFishingGuruReceivedGoodRodText:
  unsupported text command $80` at `28:46E8`
  (`src/import/RomExtractor.lua:1548`).
- `_FoundHiddenItemText` returned `result=ok` at `22:563B` in the tenth import
  of this batch. `_TrainerSentOutText` was not reached and remains unverified
  by import.
- `TEST A: PASS`: **not observed**.
- `rom-cache.complete`: **absent**.
- LÖVE exit code: `1`.
- Log directory:
  `C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-hiddenitem-104730-8cea1df2`

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

1. Diagnose `_FuchsiaGoodRodHouseFishingGuruReceivedGoodRodText` from Italian
   ROM and caller evidence before changing its mapping; do not assume `$80`
   is a parser defect.
2. Verify `_TrainerSentOutText` with `result=ok` only after the importer reaches
   it.
3. Keep decoder success, structural identity, full `TEST A: PASS`, and cache
   completion as separate status fields.
4. The NAS copy has not been identified; do not treat it as synchronized.

## Multi-workstation synchronization

Each workstation should use its own checkout and exchange reviewed Git history
through GitHub. Do not share or concurrently write a working tree over NAS.
The user reports that Windows, GitHub, and NAS have been synchronized. This
session did not inspect the NAS path, branch, HEAD, or local changes; verify
those details before using that copy.

## Updating this document

At the end of each relevant session, update the date, structural findings,
symbols with observed `result=ok`, first unresolved error, full-test result,
cache-marker state, exit code, and persistent log path. Mark unvisited symbols
as unverified. Preserve the distinction between proof from ROM structure,
observations from logs, and remaining hypotheses.
