local RomImporter = require("src.import.RomImporter")
local GameVersion = require("src.core.GameVersion")

local function fail(message)
  error("[TEST A FAIL] " .. tostring(message), 0)
end

local function assertEq(actual, expected, label)
  if actual ~= expected then
    fail(("%s: expected %s, got %s")
      :format(label, tostring(expected), tostring(actual)))
  end
end

local function readFile(path)
  local file, err = io.open(path, "rb")
  if not file then
    fail("cannot open ROM: " .. tostring(err))
  end

  local data = file:read("*a")
  file:close()

  if not data then
    fail("cannot read ROM: " .. path)
  end

  return data
end

print("========================================")
print("TEST A - ITALIAN ROM IMPORT")
print("========================================")

local romPath = "red-ita.gb"
local romData = readFile(romPath)

print("ROM:", romPath)
print("Size:", #romData)

assertEq(#romData, 1024 * 1024, "ROM size")

local expectedVersion = "red_ita"
local expectedSha1 = "65b97cf8f2f1cff711a6d08c6c894c8ce65ce522"

local digest = love.data.hash("sha1", romData)
if type(digest) == "userdata" and digest.getString then
  digest = digest:getString()
end

local actualSha1 = love.data.encode("string", "hex", digest)

print("SHA-1:", actualSha1)

assertEq(actualSha1, expectedSha1, "ROM SHA-1")

local detectedVersion = GameVersion.forSha1(actualSha1)

print("Detected version:", tostring(detectedVersion))

assertEq(detectedVersion, expectedVersion, "GameVersion.forSha1")

local info = GameVersion.info(detectedVersion)

if not info then
  fail("GameVersion.info returned nil")
end

print("Display name:", info.displayName)
print("Manifest:", info.manifest)
print("Cache prefix:", info.cachePrefix)

assertEq(
  info.manifest,
  "tools/rom_variants/red_ita_manifest.json",
  "Italian manifest"
)

assertEq(
  info.cachePrefix,
  "red_ita/",
  "Italian cache prefix"
)

print()
print("Creating RomImporter...")

local completedVersion = nil

local importer = RomImporter.new(function(version)
  completedVersion = version
  print("[CALLBACK] import complete:", version)
end, {
  launcher = false,
  forceImport = true,
})

if not importer then
  fail("RomImporter.new returned nil")
end

print("Starting import...")
importer:startData(romData, romPath)

if not importer.worker then
  fail("RomImporter did not create import coroutine")
end

print("Running import coroutine...")

local iterations = 0
local maxIterations = 200000

while importer.worker do
  iterations = iterations + 1

  if iterations > maxIterations then
    fail("import exceeded maximum coroutine iterations")
  end

  local ok, err = coroutine.resume(importer.worker)

  if not ok then
    fail("import coroutine error: " .. tostring(err))
  end

  if coroutine.status(importer.worker) == "dead" then
    importer.worker = nil
  end
end

print("Coroutine iterations:", iterations)
print("Work state:", tostring(importer.workState))
print("Completed version:", tostring(importer.completeVersion))
print("Callback version:", tostring(completedVersion))
print("Error:", tostring(importer.detail))

assertEq(importer.workState, "complete", "import workState")
assertEq(importer.completeVersion, expectedVersion, "completeVersion")
assertEq(completedVersion, expectedVersion, "callback version")

print()
print("========================================")
print("TEST A: PASS")
print("========================================")

love.event.quit()
