-- The per-version import metadata (symbol table + ROM hash) that drives
-- RomExtractor.  Split out of RomImporter so the extraction worker thread can
-- decode it itself: shipping the decoded table across a love.thread channel
-- would deep-copy every symbol for nothing.

local GameVersion = require("src.core.GameVersion")

local RomManifest = {}

function RomManifest.decode(version)
  local info = GameVersion.info(version)
  local raw, readError = love.filesystem.read(info.manifest)
  if not raw then
    error("ROM import metadata is missing: " .. tostring(readError))
  end
  local Json = require("src.link.Json")
  local manifest, decodeError = Json.decode(raw)
  if not manifest then
    error("ROM import metadata is invalid: " .. tostring(decodeError))
  end
  print("MANIFEST DEBUG: version=" .. tostring(version))
  print("MANIFEST DEBUG: labels=" .. tostring(#(manifest.text.labels or {})))
  for i, label in ipairs(manifest.text.labels or {}) do
    if tostring(label):find("AlreadyKnown", 1, true) then
      print("MANIFEST DEBUG: FOUND AlreadyKnown at index=" .. tostring(i) ..
        " label=" .. tostring(label))
    end
  end
  print("MANIFEST DEBUG: romSha1=" .. tostring(manifest.romSha1))

  assert(GameVersion.acceptsSha1(version, manifest.romSha1),
    "ROM import metadata version mismatch")
  return manifest
end

return RomManifest
