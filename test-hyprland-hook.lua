local path = assert(arg[1])
local root = path:match("(.+)/[^/]+$") or "."
local original_open, original_getenv, original_dofile = io.open, os.getenv, dofile
local files, calls, local_installs, remote_installs = {}, {}, 0, 0
os.getenv = function(name) if name == "XDG_RUNTIME_DIR" then return "/test-runtime" end end
io.open = function(name) if files[name] then return { close = function() end } end end
local module = original_dofile(path)
local api = {}
dofile = function(name)
  calls[#calls + 1] = name
  return {
    install_local = function(value) assert(value == api); local_installs = local_installs + 1 end,
    install = function(value) assert(value == api); remote_installs = remote_installs + 1 end,
  }
end
module.keyboard(api, root)
module.display(api)
assert(local_installs == 1 and remote_installs == 0, "Local Option-Up works with sharing stopped")
files["/test-runtime/mac-native-screenshare/keyboard"] = true
files["/test-runtime/mac-native-screenshare/display.lua"] = true
module.keyboard(api, root)
module.display(api)
assert(calls[1] == root .. "/mac-shortcuts.lua")
assert(calls[3] == "/test-runtime/mac-native-screenshare/display.lua")
assert(local_installs == 2 and remote_installs == 1)
files = {}
module.keyboard(api, root)
module.display(api)
assert(#calls == 4 and local_installs == 3 and remote_installs == 1, "Removing markers disables remote changes but keeps local Option-Up")
io.open, os.getenv, dofile = original_open, original_getenv, original_dofile
print("Hyprland hook tests passed: inactive guards, private keyboard module, display reload rules, and marker removal.")
