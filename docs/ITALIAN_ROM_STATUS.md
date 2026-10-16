# Italian ROM support status

**Updated:** 2026-10-16<br>
**Branch:** `feature/italian-rom-support`<br>
**Base commit:** `cef04466343377836e973257175bf1ebb99c81d1`

## Goal

Import the Italian Pokémon Red ROM through a dedicated variant and manifest,
without treating USA addresses as valid Italian mappings by default.

## Manifest inventory

The last audit counted 3,279 symbols, including 2,423 text labels. A read-only
comparison of the current manifest with the base commit finds 103 changed text
mappings. Persistent import logs contain `result=ok` for 102 of those mappings.
`_TrainerSentOutText` is the changed mapping without an observed successful
decode. This count describes decoder results in available logs; it does not
replace structural evidence for each symbol's identity.

## Structural evidence

- `_DisabledNoMoreText`: `[34, 23355]` (`22:5B3B`), structurally mapped to the
  Italian target and reached with `result=ok`.
- `_TrainerSentOutText`: `[34, 22886]` (`22:5966`), structurally demonstrated
  through its Italian `TX_FAR` wrapper, but not reached and not confirmed with
  `result=ok`.
- `_GoText`: `[34, 24227]` (`22:5EA3`, file offset `0x89EA3`), structurally
  mapped from the Italian send-out dispatch at `16:4E90`. Its high-HP branch
  selects wrapper `16:4EAE`, whose bytes `17 A3 5E 22 08 18 13` contain
  `TX_FAR` to `22:5EA3`, then `text_asm` and the following control flow. The
  target bytes `00 95 A0 A8 E7 7F 50 50` decode as «Vai! » and end at the
  first `$50`; the next stream starts at `22:5EAB` (`_DoItText`). It has no
  dynamic RAM substitution or exact manifest collision. The importer returned
  `result=ok` in the completed first Batch 9 run.
- `_GoodText`: `[34, 24303]` (`22:5EEF`, file offset `0x89EEF`), structurally
  mapped from the Italian retreat-text dispatch at `16:4F10`. The high damage
  branch selects wrapper `16:4F33`, bytes `17 EF 5E 22 08 18 00`, which uses
  `TX_FAR` to `22:5EEF` and then `text_asm`. The target bytes
  `00 A1 A4 AD A4 E7 50 50` decode as «bene!»; the preceding stream ends at
  `22:5EEE`, and `_ComeBackText` begins at `22:5EF7`. There are no dynamic RAM
  substitutions or exact manifest collisions. The importer returned
  `result=ok` in the completed run recorded below.
- `_DoItText`: `[34, 24235]` (`22:5EAB`, file offset `0x89EAB`). The Italian
  send-out dispatch at `16:4E90` selects wrapper `16:4EB5` for the 40–69% HP
  branch. Its bytes `17 AB 5E 22 08 18 0C` point to `22:5EAB` via `TX_FAR`,
  then continue through `text_asm`. The target bytes
  `00 83 A0 A8 E7 7F 50 50` start a text stream for «Dai! », terminate before
  the next wrapper target at `22:5EB3`, and contain no dynamic RAM command.
  The importer reached this mapping with `result=ok`.
- `_GotMapText`: `[37, 19866]` (`25:4D9A`, file offset `0x94D9A`), structurally
  selected by the successful Town Map gift branch in the Italian Blues House
  inline routine. `BluesHouse_h` is at `06:5B34` (`0x19B34`); its header bytes
  `08 04 04 FB 5B 5C 5B 40 5B 00 D3 5B` identify text table `06:5B5C` and
  object data `06:5BD3`. The table begins `62 5B C9 5B CE 5B`; Daisy's object
  record at `06:5BDF` is `11 07 06 FF D3 01`, with text ID `01` selecting
  inline code at `06:5B62`. That code calls GiveItem (`CD 46 3E`) and, on
  success, loads `HL=5BB9` and calls PrintText (`21 B9 5B CD 61 3C`). The
  wrapper at `06:5BB9` is `17 9A 4D 25 11 50`: `TX_FAR` to `25:4D9A`, followed
  by the key-item sound command and wrapper end. The target bytes are
  `00 52 7F B1 A8 A2 A4 B5 A4 7F AB A0 4F 8C 80 8F 8F 80 7F A3 A4 AB AB A4 7F
  82 88 93 93 BE 50`; the Italian charmap decodes this as
  `{PLAYER} riceve la{LINE}MAPPA DELLE CITTÀ`. It has no command `01`; the
  former `{RAM:wStringBuffer}` substitution metadata was removed for this
  Italian literal. The previous text ends at file offset `0x94D99` with `$58`,
  so the target begins at the next byte; the next wrapper `06:5BBF` points to
  `25:4DBA`, after the target terminator at `25:4DB8`. No other manifest symbol
  shares the candidate address. Import verification remains pending because the
  new run stopped without a final runner status.

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

### Batch 9: mapping verification and import status

| Symbol | Previous | Italian target | Import result |
| --- | --- | --- | --- |
| `_GoText` | `[34, 23740]` | `[34, 24227]` (`22:5EA3`) | `result=ok` |
| `_GoodText` | `[34, 23821]` | `[34, 24303]` (`22:5EEF`) | `result=ok` |
| `_GotMapText` | `[37, 19612]` | `[37, 19866]` (`25:4D9A`) | `result=ok` |

The first Batch 9 run reached `FINISHED` with exit code `1`. It confirmed
`_GoText: result=ok`, then failed on the old `_GoodText` mapping at `22:5D0D`
with unsupported command `$B1`. `TEST A FAIL` was recorded and the cache
marker was absent. Log directory:
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-gotext-11ac160b`.

After the structurally supported `_GoodText` correction, the import in
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-goodtext-9766a43a`
eventually reached `FINISHED`. Its final status records worker PID `16012`,
LÖVE PID `13496`, exit code `1`, and `MARKER_EXISTS=False`; `exit-code.txt`
contains `1`, and stderr is empty. Stdout confirms `_GoText: result=ok` and
`_GoodText: result=ok`, followed by `_GotAwayText: result=ok`. The first next
failure is `_GotMapText: unsupported text command $B3` at `25:4C9C`, with
`[TEST A FAIL]` and a traceback from `RomExtractor.lua:1548`. `TEST A: PASS`
was not observed and `rom-cache.complete` is absent. No Love/Lovec process was
active at the final process check. The earlier `RUNNING` observation was
intermediate: the runner later appended `FINISHED` at
`2026-10-16T14:39:20.8197387+02:00`, approximately 70 minutes after its
`STARTED` timestamp. This establishes that the result was read before the
worker had completed; it does not establish why the process took that long.

The next run, after structurally correcting `_GotMapText` and removing its
obsolete dynamic substitution metadata, completed in
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-gotmap-150820-ebce737b`.
The earlier `RUNNING` snapshot was taken while the import was still executing.
The final status now records `FINISHED`, LÖVE exit code `1`, worker PID
`48804`, LÖVE PID `23576`, and `MARKER_EXISTS=False`; `exit-code.txt` contains
`1`, and stderr is empty. Stdout confirms
`_GotMapText: result=ok`. The first subsequent failure is
`_GotMonText: unsupported text command $86` at `29:4180`, followed by
`[TEST A FAIL]` and the extractor traceback. `TEST A: PASS` was not observed
and `rom-cache.complete` is absent. The stdout file ends with a newline and
contains the complete failure traceback. Neither recorded PID nor any LÖVE
process was active at the final process check. This establishes that this run
completed; it does not establish why it took approximately seven minutes.

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

1. Structurally diagnose `_GreatlyRoseText`, the first open mapping after the
   verified `_GreatlyFellText` correction.
2. Verify `_TrainerSentOutText` with `result=ok` only if the importer reaches it.
3. Keep decoder success, structural identity, full `TEST A: PASS`, and cache
   completion as separate status fields. Current last run: exit code `1`,
   `_GreatlyRoseText` failure, `TEST A FAIL`, marker absent.
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

### Batch 9 continuation: bicycle texts and GreatlyFell

Four further mappings were structurally corrected and returned `result=ok`:

| Symbol | Previous | Italian target | Import result |
| --- | --- | --- | --- |
| `_GotMonText` | `[41, 16768]` | `[41, 16829]` (`29:41BD`) | `result=ok` |
| `_GotOffBicycleText1` | `[42, 16420]` | `[42, 16419]` (`2A:4023`) | `result=ok` |
| `_GotOnBicycleText1` | `[42, 16399]` | `[42, 16398]` (`2A:400E`) | `result=ok` |
| `_GotOnBicycleText2` | `[42, 16414]` | `[42, 16413]` (`2A:401D`) | `result=ok` |

The Italian bike-on and bike-off code selects wrapper `03:65EC` or
`03:65F6` and routes it to `PrintText`. Those wrappers contain `TX_FAR`
targets for the respective text fragments. `_GotOnBicycleText2` begins with
`01 50 CF`; its existing `{RAM:wStringBuffer}` substitution was retained.
The three other target addresses begin at their `00` stream prefixes. The
corresponding imports reached all four symbols with `result=ok`.

`_GreatlyFellText` was changed from `[37, 18366]` to `[37, 18565]`
(`25:4885`, file offset `0x94885`) based on the Italian stat-change dispatch:
the routine at `0F:766F` defaults to wrapper `0F:768C` (`_FellText`), and
selects `0F:7687` for the greatly-fell branch. That wrapper contains
`0A 17 85 48 25 17 88 48 25 50`: pause, `TX_FAR` to `25:4885`, then
`TX_FAR` to `25:4888` (`_FellText`), then end. The candidate begins `00 50`
(empty text followed by the wrapper's next command); its adjacent target
`25:4888` begins `00 E7 58`. No exact mapping collision was found. This is
structural evidence for the candidate, but **no importer `result=ok` has been
observed**.

The import for this correction completed. Its persistent log directory is
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-greatlyfell-2022459b`.
The final status is `FINISHED` at `2026-10-16T16:30:27.6042426+02:00`, exit
code `1`. Stdout confirms `_GreatlyFellText: result=ok`; the first next error
is `_GreatlyRoseText: unsupported text command $AC` at `25:47A0`. The log
contains `[TEST A FAIL]`; `TEST A: PASS` was not observed and
`rom-cache.complete` is absent. The recorded worker and LÖVE PIDs are now
absent. The earlier `RUNNING` status was an intermediate observation, not the
final result.

Batch 9 has eight corrected mappings confirmed with `result=ok` so far:
`_GoText`, `_GoodText`, `_GotMapText`, `_GotMonText`,
`_GotOffBicycleText1`, `_GotOnBicycleText1`, `_GotOnBicycleText2`, and
`_GreatlyFellText`. The current first open mapping is `_GreatlyRoseText`.
`_TrainerSentOutText` remains unverified. `TEST A: PASS` is not established,
and `rom-cache.complete` is absent.

## Persistent Italian import runner

`tools/run_italian_import.ps1` provides `Start`, `Status`, `Wait`, and
`SelfTest` actions. It creates a unique run directory under
`C:\gen1recomp\AItest\ROM-TestLogs`, records worker and LÖVE PIDs/timestamps,
streams stdout and stderr to separate files, and records the exit code,
`TEST A` result, and cache marker independently. A named-per-run status log
remains the source of truth; `RUNNING` is never converted to success merely
because a process is not visible.

The existing error screenshot
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-gotonbicycle2-155150-a84397a7\love-window.png`
shows LÖVE's blue `Error` screen with the already-logged `[TEST A FAIL]` and
decoder traceback. The old runner only waited for process exit. This confirms
that the application can present the failure in its GUI while stdout already
contains the diagnostic; it does not prove that every long run has the same
window behavior.

The new runner watches for explicit failure evidence. It enumerates windows
owned by the exact recorded `lovec.exe` PID, captures the uniquely identified
visible test window before attempting `WM_CLOSE`, and then waits for normal
process exit. It never closes a window on elapsed time alone and never force
terminates LÖVE. If no unique owned window is available, it leaves the process
running and exposes the condition in status. An exclusive lock file prevents
concurrent runs started by this runner.

Static checks passed: PowerShell parser reports no syntax errors; `SelfTest`
reported syntax and Win32 window enumeration PASS; the `Status` action read the
completed GreatlyFell run as `FINISHED`, exit code `1`, with
`_GreatlyFellText: result=ok` and `_GreatlyRoseText` as the next error.

One controlled run through the new runner completed in
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-164428-5ed68bfe`.
It recorded `FINISHED`, exit code `1`, `TEST_A=FAIL`,
`_GreatlyFellText: result=ok`, then `_GreatlyRoseText: unsupported text
command $AC`; the marker is absent. The worker emitted regular heartbeats
while output stayed temporarily at `_GameSavedText`, then completed and
continued to the explicit decoder error. This confirms that a stalled-looking
stdout snapshot is not enough to declare failure and that the detached worker
persists the final result. This run did not record a matching error window,
screenshot, or `WM_CLOSE` request, so automatic GUI closure is not yet
end-to-end verified. The runner now explicitly starts LÖVE with normal window
visibility; only a failure marker plus a uniquely identified window owned by
that run's PID permits capture and graceful `WM_CLOSE`.

Use one stable invocation for subsequent runs and status checks:

```powershell
pwsh -NoProfile -File .\tools\run_italian_import.ps1 -Action Start
pwsh -NoProfile -File .\tools\run_italian_import.ps1 -Action Status -RunId <RUN_ID>
pwsh -NoProfile -File .\tools\run_italian_import.ps1 -Action Wait -RunId <RUN_ID>
```

`Start` creates the run ID and persistent logs; `Status` is read-only;
`Wait` waits for a recorded final state or reports stale activity as
indeterminate without terminating LÖVE. If the error text is observed only
after process exit, the runner records `TEST_ERROR_EVIDENCE_AFTER_PROCESS_EXIT`
and does not attempt to capture or close a nonexistent window. The first
invocation may require a Codex command approval. A persistent approval scoped to this PowerShell
executable and this script path can avoid repeated approval prompts; do not
broaden it to arbitrary PowerShell commands. The background PowerShell worker
is hidden so it survives the short `Start` command, while `lovec.exe` is
explicitly normal/visible. No scheduler or repository configuration change is
used.

## Home workstation: GreatlyRose mapping, import not started (2026-10-16)

The checkout started clean on `feature/italian-rom-support`, HEAD
`cd826f4cf58d4071be6f045ab5b634181516fef4`. The runner, harness and both
local ROMs are available. No synchronization was performed.

`_GreatlyRoseText` was changed from `[37, 18336]` (`25:47A0`) to
`[37, 18541]` (`25:486D`, file offset `0x9486D`). Identity was checked
against the stat-increase dispatch in upstream `engine/battle/effects.asm`
(`UpdateStatDone`, `MonsStatsRoseText`, `GreatlyRoseText`, `RoseText`) and
the corresponding raw Italian and USA ROM instructions:

- Italian `0F:751D` (file `0x3F51D`): `21 31 75 CD 61 3C` loads
  the composite text at `0F:7531` and calls PrintText.
- `0F:7531` (file `0x3F531`): `17 59 48 25 08` prints the stat-increase
  prefix and enters text assembly.
- `0F:7536`: `21 4B 75 F0 F3 A7 FA D8 CF 28 03 FA D2 CF FE 12 D0
  21 50 75 C9` selects the greatly-rose wrapper or the ordinary rose wrapper
  according to the current move effect, matching upstream control flow.
- `0F:754B` (file `0x3F54B`): `0A 17 6D 48 25 17 70 48 25 50`
  pauses, references `25:486D`, falls through to `25:4870`, and ends.
  The USA equivalent at `0F:7542` instead references `25:47A0` and
  `25:47AB`; the Italian target was followed through its own pointers.
- Italian `25:486D`: `00 50 50`, an empty text fragment with text and
  command-stream terminators. The next independently referenced stream starts
  at `25:4870` with `00 E7 58`. No dynamic substitutions or exact manifest
  collisions apply. The old Italian address starts at the glyph `AC` inside
  the stream beginning `25:479E`.

JSON validation, `git diff --check`, and runner `SelfTest` passed. A single
`Start` invocation was attempted through the normal approval mechanism, but
the runner refused **before launching LÖVE or creating a new run directory**:

`Refusing to start while a prior import may still be active`

The blocking records under `C:\gen1recomp\AItest\ROM-TestLogs` are:

- `italian-20261014-160149-bef47034`: `STATE=RUNNING`, worker PID 4644,
  LÖVE PID 22060, no exit-code file, truncated stdout.
- `italian-20261014-162048-f83f1b55`: `STATE=RUNNING`, worker PID 16416,
  LÖVE PID 14384, no exit-code file, truncated stdout.

Both process checks return `NOT_VISIBLE_OR_ABSENT`; this does not prove
completion. Historical status/log files were left unchanged. No alternative
runner or bypass was used. The current runner deliberately rejects these
unresolved records at line 227, even when their PIDs are not visible.

There were **zero new imports**. `_GreatlyRoseText` is structurally proven
but has no observed `result=ok`; batch 9 remains at eight verified corrections.
There is no new next-symbol error, exit code or PASS. The current cache marker
`test-italian-run/cache-temp/LOVE/test-italian-run/red_ita/rom-cache.complete`
is absent. `_TrainerSentOutText` remains unverified.

## Home harness asset repair and GreatlyRose run (2026-10-16)

Run `italian-20261016-194713-9afaff16` ended `FINISHED`, exit code `1`,
before extraction. Its stdout recorded `RomImporter.lua:1746: Could not open
file assets/logo/logo.png`; stderr was empty and `TEST A` was not reported.
LÖVE's source is the `test-italian-run` directory passed as the command-line
argument. The canonical asset existed at `assets/logo/logo.png` in the project,
while `test-italian-run/assets` was absent. The ignored local harness now has a
single junction `test-italian-run/assets` targeting the project's `assets`
directory. Both `assets/logo/logo.png` and `assets/logo/bcg.png`, loaded in
`RomImporter.new`, are reachable through that junction. No asset was copied or
replaced.

The runner now checks the harness entry point and both assets before Start or
Preflight. It recognizes `Error: ...` from LÖVE in addition to decoder and
test failures. It reports a startup error before any text diagnostic as
`ERROR_PHASE=LOVE_INITIALIZATION`, while keeping `TEST_A=NOT_REPORTED`
distinct from an observed test pass or failure. The previous run can be read
with these classifications without altering its original logs. SelfTest
passed for general LÖVE error detection, normal output, process identity,
cross-process exclusion, syntax, and harness assets; Preflight and
`git diff --check` passed.

Exactly one new import was launched in
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-201457-90056cca`.
At the last observation it remained `RUNNING`, worker PID 16836 and LÖVE PID
11084 both verified active in session 1, with regular worker heartbeats and
empty stdout/stderr. Exit code and `TEST A` were unavailable; the cache marker
was absent. An `Untitled` LÖVE window was listed, but its screenshot capture
timed out and accessibility returned no text. No window was closed. This run
must be observed to a definitive state before any other import is started.

`_GreatlyRoseText` remains structurally established at `[37, 18541]` but
**not yet confirmed** with `result=ok`. Batch 9 remains at eight verified
mappings. No error after `_GreatlyRoseText` has been established.

Next action: resolve the runner's handling of historical runs from the other
workstation with explicit machine/process provenance, preserving original logs
and never converting an interrupted run to FINISHED. This requires a separate
runner change/review before retrying the GreatlyRose import; no such change was
made in this operation.

## Home runner migration and GreatlyRose verification attempt

The runner now records a hash of the Windows machine identity, computer name,
worker and LÖVE PID, start time, executable path, and Windows session. Process
identity checks reject PID reuse. A machine-wide named mutex and the existing
exclusive log lock protect a live local import. The preflight also refuses an
uncertain local record or a currently visible LÖVE/worker process.

The two legacy `RUNNING` records of 14 October have no originating machine
identity. Based on the confirmed office-to-home transfer, separate
`classification-*.json` notes bind each to its exact original `status.txt`
SHA-256 and classify it `HISTORICAL_UNRESOLVED_REMOTE`. Original status files,
stdout and stderr were not changed, and neither run was declared `FINISHED`.
Two other legacy records contain a final bare `FINISHED` line, which the
runner now reads correctly. New runs always record their machine identity.

Runner `SelfTest` passed for syntax, window enumeration, exact current-process
identity, PID reuse, local uncertainty, remote classification, and exclusion
across two harmless PowerShell processes. `Preflight` passed after registering
the transferred records. During the new import, a second preflight correctly
refused worker PID 13556 and LÖVE PID 1260; no duplicate import started.

The **single** GreatlyRose verification run is
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-194713-9afaff16`.
At the last observation, `STATE=RUNNING`, the worker and LÖVE identities were
`ACTIVE_LOCAL`, stdout and stderr were empty, and no exit code or `TEST A`
result existed. The cache marker was absent. Computer-use listed an `Untitled`
LÖVE window, but two attempts to capture it timed out; its content could not
be established. No window or process was closed. The harness on this PC has
`test-italian-run/main.lua` but no local `tests/` directory; whether that
caused the current behavior is **unconfirmed**.

`_GreatlyRoseText` remains structurally proven at `[37, 18541]` and is still
**not verified** with `result=ok`. Batch 9 remains at eight verified mappings.
The first known mapping error remains `_GreatlyRoseText`; no later error is
established. The following section supersedes this historical observation.

## Result of the harness asset repair run

`italian-20261016-201457-90056cca` reached `FINISHED` at
`2026-10-16T20:21:53+02:00`, exit code `1`, `[TEST A FAIL]`, and no
`rom-cache.complete`. `RomImporter.new` succeeded after the `assets` junction
was repaired. The first actual failure occurred when the import coroutine
tried to read `tools/rom_variants/red_ita_manifest.json` through LÖVE's source
filesystem, which is `test-italian-run`. The canonical manifest exists in the
repository, but the harness has no `tools` link. Stdout reports:

`RomManifest.lua:14: ROM import metadata is missing: Could not open file tools/rom_variants/red_ita_manifest.json. Does not exist.`

Stderr was empty. The error window was verified as belonging to this run's
`lovec.exe` PID 11084, session 1, handle 262608. A screenshot was saved as
`love-foreground-window.png` in the run directory before a normal `WM_CLOSE`
was posted to that specific handle. LÖVE and the worker then exited and the
runner recorded the final state.

`_GreatlyRoseText` was not reached, so its mapping `[37, 18541]` remains
structurally demonstrated without `result=ok`. Batch 9 remains at eight
verified corrections. There is no next text mapping error yet. The runner's
`ERROR_PHASE=LOVE_INITIALIZATION` is too broad for this case: the importer was
created and the failure occurred at the start of extraction. The status line
`TEST_ERROR_EVIDENCE=E` is also truncated, although `FIRST_ERROR` and stdout
preserve the complete message. Do not infer a mapping or parser fault from
these runner fields.

Next operation: restore the missing `tools` access from the LÖVE harness using
the same local junction approach, verify any further required source paths,
and inspect the runner's error-phase and first-evidence formatting before a
new controlled import. No new import was started during this result recovery.

## Complete home harness and GreatlyRose result (2026-10-16)

The ignored local harness had `assets` linked, but no `tools` entry. Since
`RomManifest.decode` uses `love.filesystem.read(info.manifest)`, LÖVE could not
read `tools/rom_variants/red_ita_manifest.json` from its `test-italian-run`
source. A junction `test-italian-run/tools` now points to the canonical project
`tools` directory. The canonical manifest was not copied. The test previously
loaded `src` and `tests` modules via `require`, read the ROM through `io.open`
from the project working directory, and initialized `RomImporter`; no other
source junction was demonstrated necessary for this import path.

The runner Preflight and Start now verify the harness entry point, the exact
`assets` and `tools` junction targets, the two startup images, the manifest as
seen through the LÖVE source, the test ROM and required Lua modules in the
project, as well as the absence of a concurrent import. Error phases now
distinguish `LOVE_INITIALIZATION`, `IMPORTER_INITIALIZATION`,
`MANIFEST_LOADING`, and `ROM_EXTRACTION`. The full first error is stored in
the status file; the former single-character `TEST_ERROR_EVIDENCE=E` issue was
fixed. SelfTest, Preflight, JSON validation and `git diff --check` passed
before LÖVE started.

Exactly one new run was started:
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-202515-76a3cf70`.
It reached `FINISHED` at `2026-10-16T20:25:27+02:00`, exit code `1`,
`TEST_A=FAIL`, `ERROR_PHASE=ROM_EXTRACTION`; `rom-cache.complete` is absent.
The persistent stdout records `_GreatlyRoseText` at `25:486D` with
`result=ok`. The first subsequent error is `_GrewLevelText: unsupported text
command $B4` at diagnostic position `22:5C01` (`RomExtractor.lua:1548`).
The runner captured the LÖVE error window in `love-error-20261016-202526-553.png`,
sent `WM_CLOSE` only to its verified PID 13768 / handle 1181214, and recorded
the final process exit. No additional import was started.

Batch 9 now has **nine** mappings verified with `result=ok`. `_TrainerSentOutText`
remains structurally mapped but without an observed `result=ok`; `TEST A: PASS`
and the cache marker are still absent. The next work is structural diagnosis
of `_GrewLevelText`; do not infer its target from the byte alone.

## Batch 9 complete: GrewLevelText (2026-10-16)

The Italian experience routine at `15:53F7` loads wrapper `15:54DD` before
`PrintText`. The wrapper bytes `17 D2 5D 22 0B 50` select `TX_FAR` target
`22:5DD2` (ROM offset `0x89DD2`), followed by the level-up sound command and
text end. The Italian target begins `01 6D CD 00`, includes `09 2C D1 13`,
and ends `00 E7 50 50`. These use the existing ordered name and level
substitutions; no dynamic metadata changed. No other manifest symbol uses
the target address. `_GrewLevelText` changed from `[34, 23553]` to
`[34, 24018]`.

Exactly one import was run in
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-205124-ef699357`.
It reached `FINISHED`, exit code `1`; stdout records
`_GrewLevelText: result=ok`. Batch 9 has **10/10 verified corrections**. The next observed
failure is `_HereYouGoText: unsupported text command $A8` at diagnostic
position `22:62E7` (`RomExtractor.lua:1548`). `TEST A` is `FAIL`, and
`rom-cache.complete` is absent. `_TrainerSentOutText` remains structurally
mapped but without observed `result=ok`. Next operation: structurally trace
`_HereYouGoText` before changing its mapping.
