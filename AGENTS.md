# Project instructions

## Project and Italian ROM goal

gen1recomp is a LÖVE application that imports supported Pokémon ROMs and
extracts data used by the application. `GameVersion` identifies a ROM and
selects its manifest; `RomImporter` coordinates import work and `RomExtractor`
reads ROM structures, pointers, assets, and text. The Italian support work
adds a dedicated Pokémon Red variant and manifest while preserving the USA
variant's mappings.

## Protect local data

- Never publish ROMs, save files, caches, extracted user data, credentials, or
  private keys.
- Preserve all local changes, including unrelated edits. Inspect status and
  diffs before touching a file.
- Do not delete, overwrite, move, or restore local data without explicit
  authorization.
- Do not run `git reset`, `git clean`, force push, or other destructive Git
  operations without explicit authorization.

## Italian text mappings

- Derive mappings from the Italian ROM's structures: map/event/script
  references, text IDs, pointer tables, wrappers, and `TX_FAR` targets as
  applicable. Verify the raw bytes at every link.
- Confirm the target's identity, not just that its address decodes as plausible
  text. Check bank, CPU address, file offset, stream start, command, terminator,
  boundaries, and collisions.
- Distinguish a structurally demonstrated address from a symbol that has
  actually returned `result=ok` in the importer log.
- Trace dynamic substitutions in ROM order. Verify each command, RAM alias,
  caller semantics, number, order, and type separately; do not infer equivalence
  from a shared command byte.
- Stop without changing a mapping if its target or identity is ambiguous.

## Import tests

- Follow `docs/ITALIAN_ROM_STATUS.md` and use the documented Italian test runner.
- Do not run concurrent or duplicate imports. Keep each run's persistent stdout,
  stderr, exit code, status, and cache-marker result.
- Stop at the first new or ambiguous error. A symbol's `result=ok` confirms its
  decoding only; it does not mean the whole import passed. Record `TEST A: PASS`
  and `rom-cache.complete` independently.
- Do not automatically delete caches or diagnostic logs.

## Git and multi-workstation work

- Never use global staging such as `git add .` or `git add -A`; stage explicit
  paths or reviewed hunks.
- Do not commit or synchronize (fetch, pull, or push) without explicit
  authorization.
- Use GitHub to share reviewed, versioned history. Do not use a writable
  working tree concurrently from multiple computers; each workstation should
  have its own checkout and integrate through Git after review.
- Treat NAS copies as unverified until their path, Git status, and ownership are
  established. Do not assume Codex conversation history contains project files.

## Session handoff

- Read `docs/ITALIAN_ROM_STATUS.md` before resuming Italian ROM work.
- At the end of relevant work, update the status with structural evidence,
  verified symbols, unresolved issues, test outcome, marker, and log directory.
- Separate established facts, test observations, and hypotheses. State the next
  concrete operation; do not imply a mapping is verified when it was not
  reached by the importer.
