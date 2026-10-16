# Italian ROM support status

**Updated:** 2026-10-16<br>
**Branch:** `feature/italian-rom-support`<br>
**Base commit:** `cef04466343377836e973257175bf1ebb99c81d1`

## Goal

Import the Italian Pokémon Red ROM through a dedicated variant and manifest,
without treating USA addresses as valid Italian mappings by default.

## Manifest inventory

The last audit counted 3,279 symbols, including 2,423 text labels. A read-only
comparison of the current manifest with the base commit finds 100 changed text
mappings. Persistent import logs contain `result=ok` for 99 of those mappings;
`_TrainerSentOutText` is the only changed mapping without an observed successful
decode. This count describes decoder results in available logs; it does not
replace structural evidence for each symbol's identity.

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

### Batch 8: structurally mapped and import verified

Ten corrections have been made in Batch 8. Each was followed by one Italian
import; every listed corrected symbol returned `result=ok` in its import log.

| Symbol | Previous | Italian target | Structural reference |
| --- | --- | --- | --- |
| `_FuchsiaGoodRodHouseFishingGuruReceivedGoodRodText` | `[40, 18152]` | `[40, 18202]` (`28:471A`) | Good Rod success branch wrapper `15:61C2`, `TX_FAR`; existing string-buffer substitution |
| `_FuchsiaGymKogaReceivedTM06Text` | `[40, 16619]` | `[40, 16629]` (`28:40F5`) | Fuchsia Gym text ID 9 and Koga reward wrapper `1D:560D`, `TX_FAR` |
| `_FullHealText` | `[34, 24246]` | `[34, 24770]` (`22:60C2`) | Italian party-item wrapper sequence, Full Heal entry |
| `_GainedText` | `[34, 23490]` | `[34, 23958]` (`22:5D96`) | Experience routine wrapper `15:54B2`, `TX_FAR` followed by `text_asm` |
| `_GameCornerClerk1DoYouNeedSomeGameCoinsText` | `[39, 22810]` | `[39, 23147]` (`27:5A6B`) | Game Corner Clerk 1 script loads `12:4D21`; wrapper `17 6B 5A 27 50` |
| `_GameCornerClerk2Received20CoinsText` | `[39, 23631]` | `[39, 23972]` (`27:5DA4`) | Object text ID 9 → table at `12:4C89` → Clerk 2 script `12:4DD8` → reward wrapper `12:4E2A` |
| `_GameCornerFishingGuruReceived10CoinsText` | `[39, 23209]` | `[39, 23545]` (`27:5BF9`) | Object text ID 5 → table at `12:4C89` → Fishing Guru reward branch wrapper `12:4DA0` |
| `_GameCornerGentlemanReceived20CoinsText` | `[39, 23787]` | `[39, 24121]` (`27:5E39`) | Object text ID `0A` → table at `12:4C9B` → Gentleman success branch loads wrapper `12:4E8C`; `17 39 5E 27 0B 50` (`TX_FAR`, reward sound, end); stream decodes `<PLAYER> riceve{LINE}20 gettoni!` |
| `_GameCornerPosterSwitchBehindPosterText` | `[39, 23984]` | `[39, 24331]` (`27:5F0B`) | Game Corner header `12:4BB0` → sign record `12:4FB1` ID `0C` → table `12:4C9F` → script `12:4EDC` → wrapper `12:4F08`, `17 0B 5F 27 08` (`TX_FAR` then `text_asm`) |
| `_GetmText` | `[34, 23757]` | `[34, 24243]` (`22:5EB3`) | HP 10–39% branch in dispatch `16:4E90` selects wrapper `16:4EBC`; `17 B3 5E 22 08` points to `22:5EB3` then `text_asm` |

The Game Corner reward wrappers include `sound_get_item_1` after their
`TX_FAR`; the mapped text streams themselves contain no dynamic RAM
substitutions. The poster stream is `00 84 A7 A8 E7 51 94 AD 7F AF B4 AB B2
A0 AD B3 A4 7F A3 A8 A4 B3 B1 AE 4F A0 AB 7F AF AE B2 B3 A4 B1 E7 55 8F B1
A4 AC A8 A0 AC AE AB AE E7 50` and ends before the following separate stream.
`_GetmText` is `00 83 A0 A8 E7 7F 50` («Dai! »), with the next
`_EnemysWeakText` stream beginning at `22:5EBB`. The ROM order and wrappers
confirm boundaries; neither candidate has an exact manifest collision.

## Latest import result

- Ten imports were run for Batch 8, one per correction. The first six ended
  at the next explicit unsupported-command errors: Koga TM06 (`$A4`), Full
  Heal (`$A8`), Gained (`$AC`), Game Corner Clerk 1 (`$A7`), Clerk 2 received
  coins (`$B2`), then Fishing Guru received coins (`$F6`). Each triggering
  symbol was corrected only after structural verification and returned
  `result=ok` in the following import.
- The seventh import later completed and confirmed
  `_GameCornerFishingGuruWinsComeAndGoText: result=ok`, then failed at
  `_GameCornerGentlemanReceived20CoinsText` (`$A8`).
- The eighth import confirmed
  `_GameCornerGentlemanReceived20CoinsText: result=ok`, then failed at
  `_GameCornerPosterSwitchBehindPosterText` (`$7F`). Its worker eventually
  reached `FINISHED`, exit code `1`, and marker absent; the diagnostic was at
  `27:5DB0`. Log directory:
  `C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-124213-gentleman-6cec31f4`.
- The ninth import confirmed
  `_GameCornerPosterSwitchBehindPosterText: result=ok`, then failed at
  `_GetmText: unsupported text command $7F` at `22:5CCD`. It reached
  `FINISHED`, exit code `1`, marker absent. Log directory:
  `C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-125122-poster-84934cb4`.
- The tenth import confirmed `_GetmText: result=ok`, then failed at
  `_GoText: unsupported text command $AD` at `22:5CBC`. It reached `FINISHED`,
  exit code `1`, marker absent; stderr was empty. Log directory:
  `C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-130248-getm-bd83f0e1`.
- `TEST A: PASS`: **not observed**; the tenth stdout contains `TEST A FAIL`.
- First open mapping: `_GoText`, unsupported command `$AD` at `22:5CBC`.
- `rom-cache.complete`: **absent** after the tenth import.
- LÖVE exit code: **1** for each of imports eight through ten.
- Last log directory:
  `C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-130248-getm-bd83f0e1`

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

1. Structurally investigate `_GoText` before changing its mapping.
2. Verify `_TrainerSentOutText` with `result=ok` only if the importer reaches it.
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
