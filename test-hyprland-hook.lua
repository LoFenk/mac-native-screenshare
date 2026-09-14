local path = assert(arg[1])
local root = path:match("(.+)/[^/]+$") or "."
local original_open, original_getenv, original_dofile = io.open, os.getenv, dofile
local files, calls = {}, {}
os.getenv = function(name) if name == "XDG_RUNTIME_DIR" then return "/test-runtime" end end
io.open = function(name) if files[name] then return { close = function() end } end end
local module = original_dofile(path)
local api = {}
dofile = function(name)
  calls[#calls + 1] = name
  return { install = function(value) assert(value == api) end }
end
module.keyboard(api, root)
module.display(api)
assert(#calls == 0, "Inactive hook must not alter bindings or displays")
files["/test-runtime/mac-native-screenshare/keyboard"] = true
files["/test-runtime/mac-native-screenshare/display.lua"] = true
module.keyboard(api, root)
module.display(api)
assert(calls[1] == root .. "/mac-shortcuts.lua")
assert(calls[2] == "/test-runtime/mac-native-screenshare/display.lua")
files = {}
module.keyboard(api, root)
module.display(api)
assert(#calls == 2, "Removing markers must disable both runtime hooks")
io.open, os.getenv, dofile = original_open, original_getenv, original_dofile
print("Hyprland hook tests passed: inactive guards, private keyboard module, display reload rules, and marker removal.")
