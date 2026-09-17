-- Loaded by the two guarded, owned blocks in the user's main config.
local M = {}
local runtime = os.getenv("XDG_RUNTIME_DIR")
local function present(path)
  local file = io.open(path, "r")
  if file then file:close(); return true end
  return false
end
function M.keyboard(api, root)
  -- Local accent-layout Option-Up remains useful when sharing is stopped.
  local shortcuts = dofile(root .. "/mac-shortcuts.lua")
  shortcuts.install_local(api)
  if runtime and present(runtime .. "/mac-native-screenshare/keyboard") then
    shortcuts.install(api)
  end
end
function M.display(api)
  if runtime and present(runtime .. "/mac-native-screenshare/display.lua") then
    dofile(runtime .. "/mac-native-screenshare/display.lua")
  end
end
return M
