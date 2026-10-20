# Italian ROM support status

**Updated:** 2026-10-19<br>
**Branch:** `feature/italian-rom-support`<br>
**Base commit:** `cef04466343377836e973257175bf1ebb99c81d1`

## Goal

Import the Italian Pokémon Red ROM through a dedicated variant and manifest,
without treating USA addresses as valid Italian mappings by default.

## Manifest inventory

The manifest contains 3,279 symbols, including 2,423 text labels. A read-only
comparison with base commit `cef0446` on 18 October finds 139 changed text
addresses. The earlier audit's 102 successful decodes covered an older manifest;
a new project-wide log census has not been performed. The ten Batch 12 mappings
below each have an explicit `result=ok`. `_TrainerSentOutText` still has no
observed successful decode. Decoder success does not replace structural evidence
for a symbol's identity.

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

## Batch 10 progress: HereYouGo through IgnoredOrders (2026-10-16)

`_HereYouGoText` was corrected from `[34, 25319]` to `[34, 25856]` and its
initial run was recovered conclusively: `result=ok`; the later `_HiddenItemBagFullText`
line from that old run had only been partial and is not treated as an error.

Three more mappings have since been structurally corrected and confirmed by
completed imports:

| Symbol | Previous | Corrected | Evidence / result |
| --- | --- | --- | --- |
| `_HisNameIsText` | `[34, 26186]` | `[34, 26771]` | Rival naming path selects wrapper `01:6A43` (`17 93 68 22 50`) to `22:6893`; the text includes `{RIVAL}` as literal charmap token, with no dynamic slot. `result=ok`. |
| `_HookedMonAttackedText` | `[34, 23603]` | `[34, 24073]` | Italian battle branch tests `wMoveMissed` and selects wrapper `16:4E40` (`17 09 5E 22 50`) to `22:5E09`; its single `$CFDF` substitution is the enemy Pokémon nickname, matching existing metadata. `result=ok`. |
| `_IceHealText` | `[34, 24212]` | `[34, 24730]` | Item text dispatch table at `04:6E83`, entry 2 points to wrapper `04:6ECE` (`17 9A 60 22 50`) and target `22:609A`; the one `$CD6D` substitution is `wNameBuffer`. `result=ok`. |

`_IgnoredOrdersText` changed from `[34, 23346]` to `[34, 23806]`. The Italian
disobedience branch selects wrapper `0F:5DCD` (`17 FE 5C 22 50`) to `22:5CFE`;
its single `$D00E` slot is `wBattleMonNick`. Import run
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-222527-dfce17d0`
finished with `_IgnoredOrdersText: result=ok`, then failed on
`_ItemUseBallText05: unsupported text command $7F` at `29:67CF`.
`TEST_A=FAIL`, exit code `1`; the cache marker is absent.

`_ItemUseBallText05` was then changed from `[41, 26575]` (`29:67CF`) to
`[41, 27108]` (`29:69E4`, ROM offset `0xA69E4`). In the Italian ball-use
routine, `03:58B4` contains `21 50 59 CD 61 3C` (`LD HL,5950; CALL PrintText`),
selecting wrapper `03:5950`. That wrapper is `17 E4 69 29 12 06 50`: `TX_FAR`
to `29:69E4`, followed by the caught-mon sound sequence. It follows the
Italian `ItemUseBallText00` through `04` wrappers in the same order; the
upstream `engine/items/item_effects.asm` uses `ItemUseBallText05` for the
successful-catch message and defines its wrapper with `sound_caught_mon` and a
prompt. Target bytes `00 81 A4 AD A8 B2 B2 A8 AC AE E7 7F 87 A0 A8 4F AF B1 A4
B2 AE 7F 50 01 DF CF 00 E7 50 50` form “Benissimo! Hai preso {RAM:wEnemyMonNick}!”
with one dynamic substitution and complete end/prompt delimiters. Existing
metadata `[[1, "{RAM:wEnemyMonNick}"]]` matches that single `$CFDF` command;
no exact symbol collision was found. This address is structurally demonstrated,
but has not yet returned `result=ok`.

One import is active in
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-231628-2c3e6e62`.
At the latest check, runner state was `RUNNING` / `ACTIVE_LOCAL`, worker PID
`11828` and LÖVE PID `18284` were present and responsive, heartbeat was current,
and no exit code or final `TEST A` result existed. Stdout remained on the
incomplete line `[ITALIAN TEXT] end symbol=_ItemUseBallText01 bank=29 address=`;
there was no explicit error yet. `rom-cache.complete` was absent. Do not launch
another import while this one remains active or indeterminate.

Batch 10 currently has **5/10 mappings confirmed with `result=ok`**:
`_HereYouGoText`, `_HisNameIsText`, `_HookedMonAttackedText`, `_IceHealText`,
and `_IgnoredOrdersText`. `_ItemUseBallText05` is the sixth correction and is
structurally demonstrated but still awaiting importer verification. Six
imports are associated with these corrections: five have conclusive outcomes
and the current sixth run remains open. No subsequent mapping error is yet
confirmed. `TEST A: PASS` has not been observed; the current run has no final
PASS or FAIL. `_TrainerSentOutText` remains unverified. Next operation: recover
the current run's conclusive outcome before starting another import.

## Batch 10 continuation: ItemUseBallText05 and 06 (2026-10-17)

The prior run `C:\gen1recomp\AItest\ROM-TestLogs\italian-20261016-231628-2c3e6e62`
reached `FINISHED` with exit code `1` and `TEST_A=FAIL`. It confirms
`_ItemUseBallText05: result=ok`; the first error was
`_ItemUseBallText06: unsupported text command $B4` at `29:6835`. The cache
marker is absent.

`_ItemUseBallText06` was changed from `[41, 26677]` (`29:6835`, file offset
`0xA6835`) to `[41, 27203]` (`29:6A43`, file offset `0xA6A43`). The Italian
catch routine at `03:58E0` loads `HL=5961` and calls `PrintText` in its new-
Pokédex-data branch. Wrapper `03:5961` is `17 43 6A 29 13 06 50`: `TX_FAR`
to `29:6A43`, followed by the Pokédex-page sound and prompt. This links the
wrapper to the new Pokédex entry message, consistent with the
`_ItemUseBallText06` caller in `src/battle/BattleState.lua`. The target starts
with `00`; its text section ends at `50` at `29:6A5B`, then command `01 DF CF`
substitutes `$CFDF` (`{RAM:wEnemyMonNick}`), followed by `00 E7 50` and final
`50` at `29:6A62`. The next text starts at `29:6A63` (`_SurfingGotOnText`).
Existing dynamic metadata for `_ItemUseBallText06` already specifies one
`{RAM:wEnemyMonNick}` substitution and is unchanged. No exact manifest symbol
collision was found. The target is structurally demonstrated; importer
verification is pending.

One import was started with the corrected mapping:
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261017-115025-cd836364`.
At the latest observation it remained `RUNNING` / `ACTIVE_LOCAL`, worker PID
`5632`, LÖVE PID `18052`; the runner heartbeat was current. At 12:01 both
process CPU times had increased, but stdout had not changed since 11:50:34 by
12:06:55. Stdout had reached `_ItemUseBallText00: result=ok` and contained an
incomplete begin line for the next ball text. No exit code, final `TEST A`
result, or cache marker was available. The runner still identifies this as a
local active run, but the result is indeterminate while the diagnostic output
has stopped advancing; do not start another import until this run is resolved.

Batch 10 now has six verified corrections: `_HereYouGoText`, `_HisNameIsText`,
`_HookedMonAttackedText`, `_IceHealText`, `_IgnoredOrdersText`, and
`_ItemUseBallText05`. `_ItemUseBallText06` is the seventh correction, with
structural evidence but no observed `result=ok` yet. `TEST A: PASS` has not been
observed and `rom-cache.complete` is absent. `_TrainerSentOutText` remains
unverified. Next operation: recover the conclusive result of the active run;
do not launch a duplicate import.

## Batch 10 continuation: ItemUseBallText06 and 07 (2026-10-17)

Run `C:\gen1recomp\AItest\ROM-TestLogs\italian-20261017-115025-cd836364`
finished with exit code `1` and `TEST_A=FAIL`. It confirms
`_ItemUseBallText06: result=ok`; the first error was
`_ItemUseBallText07: unsupported text command $88` at `29:67EE`. The cache
marker is absent.

`_ItemUseBallText07` was changed from `[41, 26606]` (`29:67EE`, file offset
`0xA67EE`) to `[41, 27138]` (`29:6A02`, file offset `0xA6A02`). The Italian
catch/box branch at `03:590E` loads `HL=5957`; it tests the `EVENT_MET_BILL`
bit at `03:5911` and, when clear, loads `HL=595C` at `03:5918` before calling
the text dispatcher at `03:591B`. Wrapper `03:5957` is `17 02 6A 29 50`, a
`TX_FAR` to `29:6A02`; sibling wrapper `03:595C` is `17 23 6A 29 50`, to
`29:6A23` (`_ItemUseBallText08`). This matches the two conditional branches
in `src/battle/BattleState.lua`, which choose ItemUseBallText07/08 on the Bill
flag after depositing the caught Pokémon.

The target starts with dynamic command `01 0B DE` (`$DE0B`), followed by text
bytes `00 4F BB 7F B3 B1 A0 B2 A5 A4 B1 A8 B3 AE 7F A0 AB 55 8F 82 7F A3 A8
7F 81 88 8B 8B E7 58`; the prompt/end delimiter is at `29:6A22`. The next
target begins immediately at `29:6A23`. Existing manifest metadata specifies
one `{RAM:wBoxMonNicks}` substitution, consistent with the ROM command and
the caller's single caught-Pokémon-name argument. No exact manifest collision
was found. The target is structurally demonstrated; its importer result is
pending.

The runner started one import for this mapping at
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261017-140419-cc5e6c13`.
At the latest check it was `RUNNING` / `ACTIVE_LOCAL`, worker PID `16584`,
LÖVE PID `10012`. The last completed text diagnostic was
`_IsUnaffectedText: result=ok`; `_ItemUseBallText00` had begun but its output
line was incomplete. There was no error, exit code, final `TEST A` result, or
cache marker. Do not start another import until this run concludes.

Seven Batch 10 corrections now have importer-confirmed `result=ok`:
`_HereYouGoText`, `_HisNameIsText`, `_HookedMonAttackedText`, `_IceHealText`,
`_IgnoredOrdersText`, `_ItemUseBallText05`, and `_ItemUseBallText06`.
`_ItemUseBallText07` is the eighth correction, structurally demonstrated but
not yet importer-verified. `TEST A: PASS` has not been observed;
`rom-cache.complete` is absent. `_TrainerSentOutText` remains unverified.

The runner's configured log root remains
`C:\gen1recomp\AItest\ROM-TestLogs`; `C:\gen1recomp\AI-TestLogs` does not
exist on this workstation. The differing path spelling was in the request,
not a runner configuration change.

## Batch 10 completed: ItemUseBallText07/08 and ItemUseText002 (2026-10-17)

Run `C:\gen1recomp\AItest\ROM-TestLogs\italian-20261017-140419-cc5e6c13`
reached `FINISHED`, exit code `1`, and `TEST_A=FAIL`. It confirmed
`_ItemUseBallText07: result=ok` at `29:6A02`. The first subsequent error was
`_ItemUseBallText08: unsupported text command $A2` at the old mapping
`[41, 26640]` (`29:6810`). The cache marker was absent.

`_ItemUseBallText08` was changed to `[41, 27171]` (`29:6A23`, file offset
`0xA6A23`). In the Italian catch/box branch, `03:590E` loads wrapper `03:5957`
for the Bill case; `FA F6 D7 CB 47 20 03` tests the Bill flag, and the other
branch at `03:5918` loads wrapper `03:595C`. That wrapper contains
`17 23 6A 29 50`, a `TX_FAR` to `29:6A23`. The target begins with one
dynamic command `01 0B DE` (`$DE0B`), matching the existing
`{RAM:wBoxMonNicks}` substitution. Its text says the caught Pokémon was
transferred to an unspecified PC and ends with `58` at `29:6A42`; the next
stream begins at `29:6A43`. No exact manifest mapping collision was found.

Run `C:\gen1recomp\AItest\ROM-TestLogs\italian-20261017-144628-d3d6d9bd`
reached `FINISHED`, exit code `1`, and `TEST_A=FAIL`. It confirmed
`_ItemUseBallText08: result=ok`. Its first error was
`_ItemUseText002: unused dynamic text substitutions` at the old mapping
`[42, 16393]` (`2A:4009`). The cache marker was absent.

`_ItemUseText002` was changed to `[42, 16392]` (`2A:4008`, file offset
`0xA8008`). Italian item-use callsites load `HL=65E2` (for example
`03:655D: 21 E2 65 CD 61 3C`). The composite wrapper at `03:65E2` contains
`17 00 40 2A 05 17 08 40 2A 50`: first `TX_FAR 2A:4000`, a continuation
command `05`, then `TX_FAR 2A:4008`. The first target prints the player using
an item; the second begins with dynamic command `01 50 CF` (`$CF50`), prints
`!`, and ends with `57` at `2A:400D`. The previous mapping pointed to the
`50` parameter inside that command, leaving the one configured dynamic
substitution unused. Existing metadata `{RAM:wStringBuffer}` was retained;
no exact manifest mapping collision was found. The USA address `2A:4009`
was not reused as evidence for the Italian address.

Run `C:\gen1recomp\AItest\ROM-TestLogs\italian-20261017-145114-2fb5b5d4`
reached `FINISHED`, exit code `1`, and `TEST_A=FAIL`. It confirmed
`_ItemUseText002: result=ok` at `2A:4008`. The first remaining error is
`_LancesRoomLanceAfterBattleText: unsupported text command $91` at
`21:5E9E` (`src/import/RomExtractor.lua:1548`). The cache marker is absent.

Batch 10 is **10/10 corrections confirmed with `result=ok`**:
`_HereYouGoText`, `_HisNameIsText`, `_HookedMonAttackedText`,
`_IceHealText`, `_IgnoredOrdersText`, `_ItemUseBallText05`,
`_ItemUseBallText06`, `_ItemUseBallText07`, `_ItemUseBallText08`, and
`_ItemUseText002`. `TEST A: PASS` has not been observed and
`rom-cache.complete` is absent. `_TrainerSentOutText` remains structurally
demonstrated but without observed `result=ok`. Next operation: investigate
`_LancesRoomLanceAfterBattleText` structurally before changing its mapping.

## Batch 11 — 17 October 2026 (run still active)

Five mappings have an observed `result=ok`; the fifth import remains active,
so its final test result and next error are not yet established. No further
import is permitted until that run reaches a conclusive state.

| Symbol | Previous | Italian target | Structural evidence | Import result |
| --- | --- | --- | --- | --- |
| `_LancesRoomLanceAfterBattleText` | `[33, 24222]` | `[33, 24510]` (`21:5FBE`, `0x85FBE`) | Lance trainer header `16:6397` selects wrapper `16:63B8`, `17 BE 5F 21`; stream starts `00`, ends `50 50` before the next text. | `result=ok`; `FINISHED`, exit 1, next Cubone error. |
| `_LavenderCuboneHouseCuboneText` | `[38, 25144]` | `[38, 25246]` (`26:629E`, `0x9A29E`) | Cubone object has text ID `01`; first table entry at `07:59B3` selects wrapper `07:59B7`, `17 9E 62 26`; stream `00 ... E7 50`, followed by the next text. | `result=ok`; `FINISHED`, exit 1, next Nugget error. |
| `_LavenderMartCooltrainerMNuggetText` | `[38, 25059]` | `[38, 25166]` (`26:624E`, `0x9A24E`) | Cooltrainer M is object/text ID `03`; conditional wrapper `17:4938` selects `17:4956`, `17 4E 62 26 50`; PEPITA text starts `00`, ends `57` before Cubone text. | `result=ok`; `FINISHED`, exit 1, next LearnedMove1 error. |
| `_LearnedMove1Text` | `[40, 26427]` | `[40, 26598]` (`28:67E6`, `0xA27E6`) | Italian move-learning callsite `01:6F52` loads wrapper `01:7001`, `17 E6 67 28 0B 06 50`; target has `01 3B D0` then `01 50 CF`, matching the two existing substitutions, and ends `50 50` before `28:67FA`. | `result=ok`; `FINISHED`, exit 1, next LinkBattleLost error. |
| `_LinkBattleLostText` | `[34, 22386]` | `[34, 22818]` (`22:5922`, `0x89922`) | Link-battle loss wrapper `0F:488E`, `17 22 59 22 50`, points to one `$D04F` dynamic command and text ending `58` at `22:5934`; next text starts `22:5935`. Existing `wTrainerName` metadata retained. | `result=ok` observed; run still `RUNNING / ACTIVE_LOCAL`. |

Completed run directories, in order:
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261017-150941-a76728af`,
`italian-20261017-151400-0cc45a21`,
`italian-20261017-151822-54f8ffc9`, and
`italian-20261017-152020-1a9c3eda` under the same log root.
The current run is
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261017-152142-308f4208`.
At the last observation, worker PID `620` and LÖVE PID `1992` were active,
the heartbeat was updating, stdout stopped in a partial
`_LinkCableHelpText1` diagnostic, stderr was empty, no exit code or `TEST A`
result had been recorded, and `rom-cache.complete` was absent. This partial
line is not an established decoder error. `_TrainerSentOutText` remains
unverified. That run subsequently reached `FINISHED`, exit code `1`,
`TEST_A=FAIL`, with no cache marker. It confirmed the LinkBattleLost mapping;
its first next error was `_LinkCableHelpText1: unsupported text command $82`
at the old address `22:5001`.

The sixth Batch 11 mapping, `_LinkCableHelpText1`, was changed from
`[34, 20481]` to `[34, 20766]` (`22:511E`, file offset `0x8911E`).
The Italian link-help routine loads wrapper `17:5C9A`; the wrapper bytes
`17 1E 51 22 50` point to a stream beginning `00` and spelling
“CONSIGLI UTILI / Uso del Cavo Game Link.” It ends with `58` at `22:5145`,
immediately before `_LinkCableHelpText2` at `22:5146`. No dynamic
substitution or exact manifest collision was found. The address is
structurally demonstrated, but `result=ok` has **not** been observed.

The verification run
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261017-164943-36c958ed`
was `RUNNING / ACTIVE_LOCAL` at the last observation (worker PID `16404`,
LÖVE PID `18636`). Heartbeat continued, but stdout stopped in a partial
diagnostic for `_LinkCableHelpText1`; stderr was empty, exit code and `TEST A`
result were not yet available, and `rom-cache.complete` was absent. Window
enumeration found no top-level window owned by that LÖVE PID. This is an
indeterminate test outcome, not a demonstrated decoder failure. Batch 11
remains **5 verified mappings out of 10**. `_TrainerSentOutText` remains
unverified. That run subsequently reached `FINISHED`, exit code `1`,
`TEST_A=FAIL`, with the cache marker absent. It confirmed
`_LinkCableHelpText1: result=ok`; its first next error was
`_LoafingAroundText: unsupported text command $5A` at old address
`22:5AE5`.

The seventh Batch 11 mapping, `_LoafingAroundText`, was changed from
`[34, 23269]` to `[34, 23728]` (`22:5CB0`, file offset `0x89CB0`).
The Italian disobedience dispatch at `0F:5D28` loads wrapper `0F:5DB9`
for the first random outcome; wrapper bytes `17 B0 5C 22 50` point to the
loafing text. The target begins with `01 0E D0` (`$D00E`, existing
`{RAM:wBattleMonNick}` substitution), says the Pokémon is ciondolando,
ends with `58` at `22:5CC5`, and the next text begins at `22:5CC6`.
No exact manifest collision was found. This mapping is structurally
demonstrated but has **no observed `result=ok` yet**.

Its only verification run is
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261017-165845-c27947dc`.
At the latest observation it remained `RUNNING / ACTIVE_LOCAL` (worker PID
`18492`, LÖVE PID `16536`) with a current heartbeat, no exit code, empty
stderr, no recorded `TEST A` result and no `rom-cache.complete`. Stdout
remained partial during `_LinkCableHelpText1`; the last complete diagnostic
was `_LinkBattleLostText: result=ok`. No result for `_LoafingAroundText`
or next error can be inferred from that partial output. Batch 11 is now
**6 mappings verified out of 10**, with the seventh awaiting its test.
`_TrainerSentOutText` remains unverified. Next operation: recover this run's
conclusive state before starting another import.

The LoafingAround verification run later reached `FINISHED`, exit code `1`,
`TEST_A=FAIL`, with the cache marker absent. Its log confirms
`_LoafingAroundText: result=ok`; the first next error was
`_LoreleisRoomLoreleiDontRunAwayText: unsupported text command $B3` at
the old address `21:6729`. Batch 11 therefore reached **7/10 verified**.

`_LoreleisRoomLoreleiDontRunAwayText` was changed from `[33, 26409]` to
`[33, 26804]` (`21:68B4`, file offset `0x868B4`). The Italian room script
uses text ID `02` when blocking the player from leaving; the second text
pointer at `1D:62CA` leads to wrapper `1D:62F2`, whose bytes
`17 B4 68 21 50` target `21:68B4`. That stream begins `00`, says
“Una voce: Non scappare!”, and ends with `57` at `21:68CC` before the
next text. It has no dynamic substitutions. The address currently also
appears under `_LoreleiEndBattleText` in the manifest; this collision was
recorded but the other symbol was not changed. The identity of the
DontRunAway target follows from the script ID and wrapper, independently
of the collision.

Its single verification run is
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261017-190453-1afd4a25`.
At the latest observation it remained `RUNNING / ACTIVE_LOCAL` (worker
PID `10224`, LÖVE PID `18008`) with heartbeat, empty stderr, no exit
code, no `TEST A` result, and no `rom-cache.complete`. Stdout was partial
around `_LinkCableHelpText1`; `_LoreleisRoomLoreleiDontRunAwayText` had
not yet appeared with `result=ok`. The eighth mapping is structurally
demonstrated but **not import verified**. `_TrainerSentOutText` also remains
unverified. Next operation: recover this run's conclusive state before any
further mapping correction or import.

### Batch 11: Lorelei collision audit (18 October 2026)

The run `C:\gen1recomp\AItest\ROM-TestLogs\italian-20261017-190453-1afd4a25`
subsequently reached `FINISHED`, exit code `1`, `TEST_A=FAIL`, with
`rom-cache.complete` absent. Stdout records
`_LoreleisRoomLoreleiDontRunAwayText: result=ok` at `21:68B4`; batch 11
therefore has **8/10 import-verified corrections**. The first next error is
`_MewtwoBattleText: unsupported text command $A0` at `21:5C72`.

The Italian Lorelei room text table at `1D:62C8` contains `D9 62 F2 62`.
The exit-block script selects text ID `02`, reaching the wrapper at
`1D:62F2` (`17 B4 68 21 50`) and the `21:68B4` stream (`00`, “Una voce:
Non scappare!”, `57` at `21:68CC`). The trainer header at `1D:62CC`
contains pointers to distinct trainer wrappers: `1D:62E8` has
`17 33 68 21 50` for the end-battle line at `21:6833`, and `1D:62ED`
has `17 4A 68 21 50` for the after-battle line at `21:684A`. These
streams begin with `00`; the former ends with `58` immediately before
`21:684A`, and the latter with `57` immediately before `21:68B4`.

The manifest's `_LoreleisRoomLoreleiEndBattleText` is a text label used
by the Lorelei trainer header. The separate `_LoreleiEndBattleText` key
also maps to `21:68B4`, but is absent from `text.labels`, the USA
manifest, and the game's Lua callers. Its current address duplicates the
exit-block text despite its name; no independent callsite establishes
whether it was intended as an alias or what it should designate. It was
already present at this address in the published manifest and was not
modified during this audit. Because the identity of that extra key is
unresolved, no further mapping was changed or import started. Next
operation: establish the provenance and intended use of
`_LoreleiEndBattleText` before resuming at `_MewtwoBattleText`.
`_TrainerSentOutText` remains without explicit `result=ok` evidence.

### Batch 11 completed: Mewtwo and Mirror Move (18 October 2026)

The extra `_LoreleiEndBattleText` manifest symbol remains a **semantic
audit issue**, not a validated alias. The actual Italian end-battle
path is the trainer header at `1D:62CC` via wrapper `1D:62E8`
(`17 33 68 21 50`) to `21:6833` (“Come ti sei permesso!”, `00` through
`58`). `_LoreleiEndBattleText` is absent from `text.labels`, the USA
manifest, and project Lua callers; its `21:68B4` mapping instead names
the independently demonstrated exit-block text. The historical
`CONFIRMED` entry in `tools/italian_global_mapping.tsv` is not evidence
of an Italian callsite. No unique intended use for this extra key has
been established; it was not changed. It does not participate in the
subsequent Mewtwo or Mirror Move call chains.

`_MewtwoBattleText` was corrected from `[33, 23666]` to `[33, 23962]`
(`21:5D9A`, file offset `0x85D9A`). The Italian Cerulean Cave B1F
header at `11:5EE4` points to the text table at `11:5F09`. Its first
entry `1C 5F` selects the Mewtwo `text_asm` wrapper at `11:5F1C`,
which loads trainer header `11:5F0F`; the header points to `11:5F26`.
That wrapper begins `17 9A 5D 21 08`: `TX_FAR` targets `21:5D9A`, then
the wrapper plays Mewtwo's cry. The first object record at `11:5F3E`
has Mewtwo's text ID `41` (trainer flag plus text 1). The target begins
`00 8C A4 B6 E7 50 50` (“Mew!”), has no dynamic substitutions, and
ends before the next stream at `21:5DA1`; no exact manifest collision
was found. Run
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261018-134918-39e92048`
reached `FINISHED`, exit code `1`, with `_MewtwoBattleText: result=ok`.
Its first next error was `_MirrorMoveFailedText: unsupported text
command $4F` at the old `22:5B96`.

`_MirrorMoveFailedText` was corrected from `[34, 23446]` to
`[34, 23908]` (`22:5D64`, file offset `0x89D64`). In the Italian
battle routine, `0F:6318` checks Mirror Move (`FE 77`); its failure
branch loads wrapper `0F:6327` (`21 27 63` at `0F:631F`) and calls
`PrintText`. The wrapper is `17 64 5D 22 50`, targeting `22:5D64`.
The stream starts `00`, reads “La SPECULMOSSA è fallita!”, ends with
`58` at `22:5D7E`, and the next stream starts `00` at `22:5D7F`.
There are no dynamic commands or exact manifest collisions. Run
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261018-135202-50439bc0`
reached `FINISHED`, exit code `1`, and records
`_MirrorMoveFailedText: result=ok`.

Batch 11 is **10/10 import verified**. The last run reports
`TEST_A=FAIL`, `rom-cache.complete` absent, and the first next error
`_MonCannotLearnMachineMoveText: unused dynamic text substitutions`
at `29:6A6E`. No mapping for that symbol was changed in this batch.
`_TrainerSentOutText` still lacks explicit `result=ok` evidence.
Next operation: separately trace the Italian dynamic commands and
manifest substitutions for `_MonCannotLearnMachineMoveText` before
changing it.

### Batch 12 completed: dynamic text and adjacent battle/house texts (18 October 2026)

All ten rows below were changed one at a time in the Italian manifest. Each
change passed JSON parsing and `git diff --check`, then returned `result=ok` in
one completed Italian import. Dynamic metadata was retained in every row;
the initial `unused dynamic text substitutions` errors came from wrong text
addresses, not excess substitutions at the demonstrated targets.

| Symbol | Previous | Italian target | Structural and dynamic evidence |
| --- | --- | --- | --- |
| `_MonCannotLearnMachineMoveText` | `[41, 27246]` | `[41, 27796]` (`29:6C94`, `0xA6C94`) | TM/HM refusal branch `03:651B` selects wrapper `03:6558` (`17 94 6C 29 50`); commands `01 6D CD` and twice `01 50 CF` use the Pokémon name and move name twice; ends `$58` at `29:6CCB`. |
| `_MonWasReleasedText` | `[34, 25192]` | `[34, 25737]` (`22:6489`, `0x8A489`) | Bill's PC release callsite `08:56AF` selects wrapper `08:581D` (`17 89 64 22 50`); two `01 50 CF` name substitutions; ends `$58` at `22:64AB`. |
| `_MonWasStoredText` | `[34, 24921]` | `[34, 25452]` (`22:636C`, `0x8A36C`) | Bill's PC deposit callsite `08:5614` selects wrapper `08:57F5` (`17 6C 63 22 50`); `01 50 CF` is the Pokémon name and `01 3D CD` the destination Box number; ends `$58` at `22:638C`. |
| `_MoneyForWinningText` | `[34, 22237]` | `[34, 22671]` (`22:588F`, `0x8988F`) | Trainer victory routine at `0F:46D7` prints wrapper `0F:46E4` (`17 8F 58 22 50`) before adding prize money; `02 7E D0 C3 00` reads the numeric winnings, matching existing metadata; ends `$58` at `22:58A0`. |
| `_MonsStatsFellText` | `[37, 18355]` | `[37, 18547]` (`25:4873`, `0x94873`) | Stat-down routine prints wrapper `0F:766A` (`17 73 48 25 08`) after preparing the stat name; `01 50 CF` uses `wStringBuffer`; stream ends `$50` at `25:4884` before the following text at `25:4885`. |
| `_MoveIsDisabledText` | `[34, 23081]` | `[34, 23539]` (`22:5BF3`, `0x89BF3`) | Disabled-move routine at `0F:5A8B` selects wrapper `0F:5AAB` (`17 F3 5B 22 50`); one `01 6D CD` uses `wNameBuffer`; ends `$58` before the next stream. |
| `_MoveWasDisabledText` | `[37, 18590]` | `[37, 18784]` (`25:4960`, `0x94960`) | Disable effect at `0F:7B0E` prints wrapper `0F:7B18` (`17 60 49 25 50`); one `01 6D CD` uses `wNameBuffer`; ends `$58` at `25:4976`. |
| `_MrFujisHouseMrFujiReceivedPokeFluteText` | `[38, 24571]` | `[38, 24690]` (`26:6072`, `0x9A072`) | House header `07:589D` selects table `07:58AD`; Mr. Fuji's object record `07:598F` has text ID 5, table entry `07:58B5` points to conditional script `07:5919`; gift-success branch prints wrapper `07:5952` (`17 72 60 26 11`), followed by sound and explanation. `01 50 CF` uses `wStringBuffer` for the item name; ends with `$50 $50` at `26:6085–6086`. |
| `_MrFujisHouseNidorinoText` | `[38, 24453]` | `[38, 24560]` (`26:5FF0`, `0x99FF0`) | Object record `07:5989` has text ID 4; table entry `07:58B3` points to wrapper `07:590C` (`17 F0 5F 26 08`), then the cry routine. Literal Nidorino text ends `$50 $50` at `26:6001–6002`; no dynamic commands. |
| `_MrFujisHousePsyduckText` | `[38, 24434]` | `[38, 24542]` (`26:5FDE`, `0x99FDE`) | Object record `07:5983` has text ID 3; table entry `07:58B1` points to wrapper `07:58FF` (`17 DE 5F 26 08`), then the cry routine. Literal Psyduck text ends `$50 $50` at `26:5FEE–5FEF`; no dynamic commands. |

The House text targets have separate starts and adjacent terminators; none of
the ten new target addresses has an exact manifest collision. Ten imports were
started for these ten corrections. The last run is
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261018-170352-bd78e52f`:
`FINISHED`, exit code `1`, `_MrFujisHousePsyduckText: result=ok`,
`TEST_A=FAIL`, and `rom-cache.complete` absent. Its first next error is
`_MrPsychicsHouseMrPsychicReceivedTM29Text: unsupported text command $AD`
at the old `28:652A`. No mapping for that symbol was changed. Some earlier
Batch 12 runs held an error window open after printing a partial stdout line;
the exact test PID and the window content were captured before using the
runner's controlled window-close function, after which `FINISHED` and the
exit code were recorded. The runner was not modified.

Batch 12 is **10/10 import verified**. `_TrainerSentOutText` still lacks
explicit `result=ok`. `_LoreleiEndBattleText` remains the unresolved semantic
audit issue described above; neither mapping was changed in this batch. Next
operation: trace the Italian Mr. Psychic gift-success script and wrapper for
the TM29 receipt text, then verify any demonstrated correction in a new batch.

### Runner screenshot isolation verified (19 October 2026)

`PrintWindow` now runs only in the disposable child
`tools/capture_import_window.ps1`. The supervisor in
`tools/run_italian_import.ps1` waits at most 5 seconds for that child and records
`SCREENSHOT_TIMEOUT` if it does not finish. It terminates only the child it
created, using its process object; it never applies this timeout or termination
to LÖVE. Helper cleanup waits are also bounded. Screenshot filenames are unique
and opened with `CreateNew`; stdout, stderr and original import results remain
untouched. The helper does not send window input or close windows.

Before capture and again before `WM_CLOSE`, the runner requires a recorded error
and matching machine, PID, start time, executable path and session. It rechecks
the selected visible handle and window class after the capture attempt, and the
native close function checks handle ownership immediately before posting
`WM_CLOSE`. Screenshot failure does not prevent that controlled close. Existing
single-import mutex and file lock protections are unchanged. The helper must
accompany the runner when moving to another workstation; preflight checks its
presence.

Validation commands:

```powershell
pwsh -NoProfile -File .\tools\run_italian_import.ps1 -Action SelfTest
pwsh -NoProfile -File .\tests\test_import_window_capture.ps1
pwsh -NoProfile -File .\tools\run_italian_import.ps1 -Action Preflight
```

PowerShell syntax checks, `git diff --check`, existing SelfTest (including
cross-process exclusion), and preflight passed. The GUI test created only its
own disposable windows. A real `PrintWindow` capture produced a valid PNG. A
first attempt to provoke a native hang by suspending the fixture's message
pump still produced a screenshot; it was not treated as proof of a timeout.
The deterministic test therefore substitutes a deliberately non-returning
capture child at the same supervisor boundary. It recorded
`SCREENSHOT_TIMEOUT`, returned in **5.11 seconds**, confirmed the helper had
exited while both fixture processes remained alive, refused a foreign PID's
window and a close without recorded LÖVE/error identity, and preserved hashes
of fixture stdout, stderr and exit code. Both fixture windows then closed
normally. This proves the supervisor timeout path; it does not claim that a
native `PrintWindow` hang was reproduced. Test artifacts are preserved under
`C:\gen1recomp\AItest\ROM-TestLogs\runner-selftests\capture-1fb7ccf18ce144f8adff63269bca75bd`.

Exactly one ordinary Italian import was then run without manifest changes:
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261019-134933-5431b356`.
It reached `FINISHED`, exit code `1`, `TEST_A=FAIL`, `ERROR_PHASE=ROM_EXTRACTION`,
with `rom-cache.complete` absent. The screenshot helper (PID `21156`) exited
with code `0`; the runner recorded `SCREENSHOT_RESULT=CAPTURED` and
`ERROR_WINDOW_WM_CLOSE_POSTED=True` for LÖVE PID `17588`, handle `10225908`.
LÖVE and worker PID `12408` exited without manual window interaction. The first
error remains `_MrPsychicsHouseMrPsychicReceivedTM29Text: unsupported text
command $AD` at `28:652A`. Batch 12 stays complete at 10/10; batch 13 has not
started. `_TrainerSentOutText` and the Lorelei semantic audit remain unresolved.

Remaining limits: absent/ambiguous windows or unverified process identity still
prevent automatic close. A window that ignores `WM_CLOSE` is left running with
heartbeat and the import lock held; no import timeout or forced LÖVE termination
was added. Computer Use screenshots are not required by this runner.

### Batch 13 in progress (19 October 2026)

The runner, screenshot helper and GUI self-test changes above are preserved.
Only the Italian manifest and this status document are being edited.

| Symbol | Previous | Italian target | Evidence and result |
| --- | --- | --- | --- |
| `_MrPsychicsHouseMrPsychicReceivedTM29Text` | `[40, 25898]` | `[40, 26097]` (`28:65F1`, `0xA25F1`) | Header `07:5E31` selects table `07:5E40` and object data `07:5E8B`; NPC record `07:5E97` has text ID 1, selecting script `07:5E42`. GiveItem (`00:3E46`) receives item `$E5`, quantity 1; its success branch loads wrapper `07:5E7B`, `17 F1 65 28 0B 50`. Target uses one `01 50 CF` with existing `wStringBuffer` item-name metadata; ends `$50 $50` at `28:6604–6605`, before explanation at `6606`; no exact collision. `result=ok` in `italian-20261019-140202-db7962bd`, `FINISHED`, exit 1. |
| `_MrPsychicsHouseMrPsychicTM29ExplanationText` | `[40, 25918]` | `[40, 26118]` (`28:6606`, `0xA2606`) | Same NPC script checks `$D7C2` bit 0; the already-received branch at `07:5E6D` loads wrapper `07:5E81`, `17 06 66 28 50`. Literal explanation ends `$57` at `28:6644`, before no-room text at `6645`; no dynamics or exact collision. `result=ok` in `italian-20261019-140254-09d4bf50`, `FINISHED`, exit 1. |

The second run held its error window open while stdout stopped mid-line. A
bounded helper capture identified the actual error on the exact SDL window
(LÖVE PID `12096`, handle `1050454`). The screenshot and a separate visual
evidence entry were preserved before posting `WM_CLOSE` via the runner's native
ownership-checking function. The original stdout was not edited. After normal
exit, complete stdout confirmed `_MtMoonPokecenterMagikarpSalesmanIGotADealText:
unsupported text command $B3` at `22:6976`, `TEST_A=FAIL`, marker absent.

Third mapping verified: `_MtMoonPokecenterMagikarpSalesmanIGotADealText`
`[34, 26998]` -> `[34, 27638]` (`22:6BF6`, `0x8ABF6`). Header `12:52C5`
points to table `12:52D7` and object data `12:5378`. The salesman record at
`12:5396` has text ID 4; table entry `12:52DD` is `EE 52`. Script `12:52EE`
checks the purchase event and loads wrapper `12:535E` for the initial offer,
before the yes/no choice and money check. Wrapper `17 F6 6B 22 50` leads to
literal offer text ending `$57` at `22:6C67`, immediately before the refusal
text at `6C68`. No dynamic commands or exact collision. Verification run:
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261019-144331-957ef8b2`.
The run finished with exit 1, `result=ok`, `TEST_A=FAIL`, marker absent;
the next error was `_Museum1FScientist1ThankYouText`, `$B1` at `25:6572`.

Fourth mapping: `_Museum1FScientist1ThankYouText` `[37, 25970]` ->
`[37, 26754]` (`25:6882`, `0x96882`). Header `17:40EB` contains table
`17:412B` and object pointer `17:42C1`. First NPC (text ID 1) selects
`17:4135`. Its ticket-purchase path checks money `$00 $00 $50`, then loads
`HL=$4224` and prints before setting `$D759` bit 0 and subtracting the price.
Wrapper `17:4224` is `17 82 68 25 50`. Literal payment acknowledgement
starts `$00`, ends `$57` at `25:689A`; previous text ends `$58` at `6881`,
next starts `$00` at `689B`. No dynamics or collision. `result=ok` in
`italian-20261019-144638-c1d7028f`, FINISHED, exit 1, TEST_A FAIL, marker absent.
The subsequent Old Amber error was buffered mid-line; bounded capture saved
`love-error-b2a258dbb90d4c7bbd24940b4d368726.png`, showing `$A2`. PID/start/path/
session and SDL handle `1247062` were rechecked before native `WM_CLOSE` for
LÖVE PID `12912`. Final stdout confirmed the error without editing stdout.

Fifth mapping verified: `_Museum1FScientist2ReceivedOldAmberText`
`[37, 26512]` -> `[37, 27318]` (`25:6AB6`, `0x96AB6`). Same header, third
NPC/text ID 3 selects script `17:4256`. It tests `$D759` bit 1, calls GiveItem
with `BC=$011F` (one Old Amber), branches on carry, sets the event and hides
the object on success, then loads wrapper `17:4293`: `17 B6 6A 25 0B 50`.
The target contains PLAYER plus a literal item name, no RAM substitutions;
ends `$50 $50` at `25:6ACF–6AD0`, before follow-up at `6AD1`. Previous text
ends `$58` at `6AB5`; no exact collision. Run:
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261019-144843-8d2cd143`.
This run reached FINISHED, exit 1, `result=ok`, TEST_A FAIL, marker absent.
Its buffered stdout was recovered after bounded capture of the verified SDL
window and native WM_CLOSE (PID `16304`, handle `1508822`); screenshot
`love-error-368dc2951eae4fdabb2fa77a314124e8.png` and original logs remain.
Next error: `_Museum1FScientist3Text`, `$A3` at `25:67E8`.

Sixth mapping verified: `_Museum1FScientist3Text`
`[37, 26600]` -> `[37, 27413]` (`25:6B15`, `0x96B15`). Object record
`17:42EB` is `20 08 15 FF FF 04`; ID 4 selects table entry `17:4131`,
`A3 42`. Script `17:42A3` is `08 21 AD 42 CD 61 3C C3 D7 24`, loading
wrapper `17:42AD`, `17 15 6B 25 50`. Literal description of the two fossils
starts `$00`, ends `$57` at `25:6B55`; previous terminator at `6B14`, next
stream `$00` at `6B56`. No RAM commands or collision. Run:
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261019-145035-fd2b975d`.
Result: FINISHED, exit 1, `result=ok`, TEST_A FAIL, marker absent. Buffered
stdout was recovered after capture `love-error-36dcb4fedb7f45f78f20a3bba34cf07d.png`
and verified native WM_CLOSE (PID `20380`, SDL handle `1967246`). Next error:
`_Museum2FGrampsText`, `$A0` at `25:6869`.

Seventh mapping verified: `_Museum2FGrampsText`
`[37, 26729]` -> `[37, 27554]` (`25:6BA2`, `0x96BA2`). Header `17:430B`
is `0A 04 07 48 40 1A 43 17 43 00 4B 43`; table `17:431A`, objects
`17:434B`. Second object at `17:435F` is `25 09 04 FF D0 02` (x0,y5,
text ID 2), matching the upstream Gramps object. Entry `17:431C` is `2D 43`;
wrapper `17:432D` is `17 A2 6B 25 50`. Literal moon-landing recollection
starts `$00`, ends `$57` at `25:6BFC`; boundaries `6BA1=$57`, `6BFD=$00`.
No dynamics or exact collision. Run:
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261019-145219-d3be3c07`.
Result: FINISHED, exit 1, `result=ok`, TEST_A FAIL, marker absent. Screenshot
`love-error-516ee9214bac480aa3ca71e13886ca74.png` preserved the next error before
verified WM_CLOSE (PID `17688`, SDL handle `1442660`); final stdout confirmed
`_Museum2FMoonStoneSignText: unsupported text command $80` at `25:694B`.

Eighth mapping verified: `_Museum2FMoonStoneSignText`
`[37, 26955]` -> `[37, 27811]` (`25:6CA3`, `0x96CA3`). Same Museum2F
header/table; object data declares two BG records. Second record `17:4355`
is `05 02 07` (x2,y5, text ID 7), matching the upstream Moon Stone sign.
Table entry `17:4326` is `46 43`; wrapper `17:4346` is `17 A3 6C 25 50`.
Literal meteorite sign starts `$00`, ends `$57` at `25:6CD1`, bounded by
`6CA2=$57` and `6CD2=$00`. No dynamics or collision. Run:
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261019-145359-2fe0a192`.
This run reached `FINISHED`, exit code 1, `TEST_A=FAIL`, marker absent.
The original stdout records `_Museum2FMoonStoneSignText: result=ok` at
`25:6CA3`. Its next error was
`_NameRatersHouseNameRaterATrulyImpeccableNameText: unsupported text command
$A3` at `26:646B`. The test-owned SDL window (LÖVE PID `13440`, handle
`1247160`) was captured as `love-error-155f3b70ee65429d87e5d399a6f548b5.png`
and closed via verified `WM_CLOSE` before the worker recorded its exit.

Ninth mapping structurally demonstrated, **not import-verified**:
`_NameRatersHouseNameRaterATrulyImpeccableNameText` `[38, 25707]` ->
`[38, 25757]` (`26:649D`, `0x9A49D`). Header `07:5A07` selects text table
`07:5A55` and object data `07:5AD7`; the NPC's text ID 1 selects script
`07:5A57`. After the party menu, the script loads the selected Pokémon name,
checks original trainer identity via `07:5A21`, and on mismatch loads wrapper
`07:5AD2`, `17 9D 64 26 50`. The Italian target has two `01 6D CD`
commands reading `$CD6D`; the two existing `{RAM:wNameBuffer}` metadata
entries remain unchanged. The text ends with `$57` at `26:64CA`, bounded by
the preceding `$57` at `649C` and the following stream at `64CB`; no exact
collision was found.

The one verification run is
`C:\gen1recomp\AItest\ROM-TestLogs\italian-20261019-145557-a2ed50f1`.
Its original `status.txt` still says `RUNNING`, with worker PID `12500`,
LÖVE PID `21072` and last heartbeat on 19 October at 15:38:59 CEST.
The last stdout bytes are an incomplete line during
`_Museum1FScientist2TakeThisToAPokemonLabText`; stderr is empty. No
`exit-code.txt`, `FINISHED`, `TEST A` outcome, or
`_NameRatersHouseNameRaterATrulyImpeccableNameText: result=ok` exists.
On 20 October, both recorded PIDs were absent from `Get-Process`; no relevant
Application log event was found in the run interval. The runner classified
the unchanged local record `LOCAL_OR_UNKNOWN_UNRESOLVED` and observed
`RECORDED_RUNNING_PROCESSES_NOT_VISIBLE_TO_THIS_QUERY`. Its supported
`RegisterTransferred` action applies only to legacy records lacking machine
identity. The local record had no supported reconciliation action at the time
of that audit. `rom-cache.complete` remains absent.

Current batch 13 total: **8/10 verified**. `_TrainerSentOutText` remains
unverified; the `_LoreleiEndBattleText` semantic issue remains open. The next
operation is to verify the ninth mapping with a single import after confirming
the run gate and preflight again.

### Local interrupted-run recovery (20 October 2026)

`tools/run_italian_import.ps1` now supports `-Action ReconcileLocal -RunId`.
It checks the run ID and current machine identity, complete recorded PID/start
time/executable/session fields for both worker and LÖVE, current process
identity, the full local process list, and the exclusive import lock. It
requires neither recorded process to be active or uncertain, and rejects
another import or an inaccessible process list. It writes a separate,
atomically created `reconciliation-<run-id>-<machine-id>.json` containing
`OriginalState=RUNNING`, `OperationalState=INACTIVE`, and
`DiagnosticOutcome=INTERRUPTED_UNVERIFIED`, together with hashes of the three
original logs. The original status, stdout, stderr and absent exit code are
unchanged. A repeated reconciliation validates the same note and is
idempotent. A stale or altered note cannot release the import gate.

The `Start`, `Preflight`, worker and reconciliation actions now share the
named mutex and exclusive lock file. After the launcher releases the gate,
the worker checks all other run records again under that gate before starting
LÖVE. The worker excludes only its own run after verifying its recorded
identity; a concurrent start or uncertain record blocks the launch.

PowerShell syntax, runner `SelfTest`, and the new fixture tests passed. The
fixture tests covered interrupted and active runs, reused PID, incomplete
identity, another lock holder, repeated and concurrent reconciliation,
verified exclusion of the worker's own run, and unchanged original log hashes.
No LÖVE import was launched by these tests.

The 19 October run `italian-20261019-145557-a2ed50f1` was reconciled through
the new action. Its separate note is under
`C:\gen1recomp\AItest\ROM-TestLogs\reconciliation-italian-20261019-145557-a2ed50f1-D22CF422726A8432C3F3BDE043D7025B6E6A3F679697E6D86EFB316B75A66CEC.json`.
Both recorded processes were absent; the note's original-log hashes matched
the unchanged files. `Status` now reports `HISTORICAL_INTERRUPTED_LOCAL` while
showing the original `RUNNING`, empty exit code and no TEST A result.
`Preflight` returned `PASS` on this computer without starting LÖVE. The
ninth Name Rater mapping remains structurally demonstrated but has no
`result=ok`; batch 13 remains **8/10 verified**, marker absent. Before the
next import, repeat `Preflight`; do not treat this reconciliation as an
import result.

### Batch 13 completion (20 October 2026)

The ninth mapping, `_NameRatersHouseNameRaterATrulyImpeccableNameText`
`[38, 25707]` -> `[38, 25757]`, returned `result=ok` at `26:649D` in
`italian-20261020-130358-97bc1581`. That run finished with exit code 1 and
`TEST A FAIL`; the next error was
`_NameRatersHouseNameRaterGiveItANiceNameText: unsupported text command $A8`
at the old address `26:637F`. The cache marker remained absent.

The tenth mapping, `_NameRatersHouseNameRaterGiveItANiceNameText`
`[38, 25471]` -> `[38, 25565]` (`26:63DD`, file offset `0x9A3DD`), follows
the same Name Rater NPC with text ID 1 and script `07:5A57`. The renameable
Pokémon branch at `07:5A8F` loads wrapper `07:5ABE`, whose bytes are
`17 DD 63 26 50` (`TX_FAR 26:63DD`). The old address `26:637F` contains
glyph `$A8` within the earlier Name Rater text. The Italian target begins
`01 6D CD 00`, contains one dynamic read of `$CD6D`, and decodes as
`{RAM:wNameBuffer}? / Non è male! / Ti suggerisco un altro soprannome? /
Sei d'accordo?`. The existing single `{RAM:wNameBuffer}` substitution matches
that command and the caller's selected Pokémon name. The stream ends with
`$57` at `26:6420`, preceded by the prior stream's `$58` at `26:63DC` and
followed by another stream at `26:6421`. There is no exact manifest collision.

After JSON validation, `git diff --check` and runner preflight passed, the
single verification run `italian-20261020-133215-9b2a793c` finished with
exit code 1. Its original stdout records
`_NameRatersHouseNameRaterGiveItANiceNameText: result=ok` at `26:63DD`, then
`_NoCyclingAllowedHereText: unsupported text command $55` at `29:6B34`.
`TEST A FAIL` was recorded and `rom-cache.complete` is absent.

**Batch 13: 10/10 mapping corrections verified with `result=ok`.** The next
mapping to investigate is `_NoCyclingAllowedHereText`; no correction has been
made to it. `_TrainerSentOutText` still lacks explicit `result=ok` evidence,
and the `_LoreleiEndBattleText` semantic mismatch remains open. Preserve the
local runner and helper/test changes during the next checkpoint.
