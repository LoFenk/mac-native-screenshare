local module = dofile(assert(arg[1], "Pass the path to mac-shortcuts.lua"))
local binds, removed, fail_at = {}, {}, nil
local api = {
  bind = function(keys, dispatcher, options)
    if fail_at == #binds + 1 then error("Simulated failure") end
    local binding = { keys = keys, dispatcher = dispatcher, options = options or {}, enabled = true }
    function binding:set_enabled(enabled) self.enabled = enabled end
    function binding:is_enabled() return self.enabled end
    binds[#binds + 1] = binding
    return binding
  end,
  unbind = function(keys) removed[#removed + 1] = keys end,
}
local state = module.install(api)
assert(module.install(api) == state, "Installation must be idempotent")
local action = function() error("Tests must not execute desktop actions") end
local options = { description = "Fullscreen", release = true, locked = true }
local pair = api.bind("SUPER + F", action, options)
assert(pair[1].keys == "SUPER + F" and pair[2].keys == "ALT + F")
assert(pair[1].options.device.inclusive == false)
assert(pair[2].options.device.inclusive == true)
assert(pair[1].options.device.list[1] == "hl-virtual-keyboard-wayvnc")
assert(pair[2].options.device.list[1] == "hl-virtual-keyboard-wayvnc")
assert(pair[1].options.device.list[2] == "hl-virtual-keyboard-wayvnc-1")
assert(pair[2].options.device.list[2] == "hl-virtual-keyboard-wayvnc-1")
assert(pair[1].dispatcher == action and pair[2].dispatcher == action)
assert(pair[1].options.release and pair[2].options.locked)
assert(options.device == nil, "Do not mutate the caller's options")
pair:set_enabled(false)
assert(not pair[1].enabled and not pair[2].enabled)
pair:set_enabled(true)

-- Opposite-modifier actions must not double-fire or be removed together.
local opposite = api.bind("ALT + F", action)
assert(opposite[1].keys == "ALT + F" and opposite[2].keys == "SUPER + F")
api.unbind(" super + f ")
assert(not pair[1].enabled and not pair[2].enabled)
assert(opposite[1].enabled and opposite[2].enabled)
assert(#removed == 0)

-- Preserve multiple intentional actions on a single shortcut (e.g. Alt+Tab).
local first = api.bind("ALT + TAB", action)
local second = api.bind("ALT + TAB", action)
api.unbind("ALT + TAB")
assert(not first[1].enabled and not second[2].enabled)

for _, keys in ipairs({ "CTRL + C", "SUPER + ALT + F", "SUPER + mouse:272", "SUPER + mouse_down" }) do
  local count = #binds
  api.bind(keys, action)
  assert(#binds == count + 1 and binds[#binds].keys == keys)
end
local scoped = { device = { inclusive = true, list = { "special-keyboard" } } }
api.bind("SUPER + X", action, scoped)
assert(binds[#binds].options == scoped)

local translated, changes = module.translate("SUPER + SHIFT + CTRL + code:10")
assert(translated == "ALT + SHIFT + CTRL + code:10" and changes)
translated, changes = module.translate("SUPER + ALT + code:10")
assert(not changes)
translated, changes = module.translate("CTRL + Alt_L")
assert(translated == "CTRL + Alt_L" and not changes)

-- Purely model physical versus remote execution without pressing real keys.
local function enabled_matches(keys, device)
  local count = 0
  for _, binding in ipairs(binds) do
    local scope = binding.options.device
    local matched = false
    for _, name in ipairs(scope and scope.list or {}) do
      if name == device then matched = true end
    end
    local allowed = not scope or (scope.inclusive == matched)
    if binding.enabled and binding.keys == keys and allowed then count = count + 1 end
  end
  return count
end
assert(enabled_matches("ALT + F", "physical-keyboard") == 1)
assert(enabled_matches("SUPER + F", "physical-keyboard") == 0)
assert(enabled_matches("SUPER + F", "hl-virtual-keyboard-wayvnc") == 1)
assert(enabled_matches("ALT + F", "hl-virtual-keyboard-wayvnc") == 0)
assert(enabled_matches("SUPER + F", "hl-virtual-keyboard-wayvnc-1") == 1)
assert(enabled_matches("ALT + F", "hl-virtual-keyboard-wayvnc-1") == 0)
local count = #binds
fail_at = count + 2
assert(not pcall(api.bind, "SUPER + Z", action))
assert(#binds == count + 1 and not binds[#binds].enabled)
assert(state.families["SUPER+Z"] == nil)
fail_at = nil
api.unbind("CTRL + C")
assert(removed[#removed] == "CTRL + C")
api.unbind("all")
assert(removed[#removed] == "all" and next(state.families) == nil)
assert(state.question_binding.keys == "UP")
assert(state.question_binding.options.auto_consuming)
assert(state.question_binding.options.device.inclusive)
assert(state.question_binding.options.device.list[1] == "hl-virtual-keyboard-wayvnc")

local focused, option, sent, timers = nil, false, {}, {}
local question = module.question_shortcut({
  get_active_window = function() return focused end,
  is_key_down = function(code) assert(code == 205); return option end,
  dsp = { send_key_state = function(args) return args end },
  dispatch = function(args) sent[#sent + 1] = args end,
  timer = function(callback, options)
    assert(options.timeout == 50 and options.type == "oneshot")
    timers[#timers + 1] = callback
  end,
})
assert(not question().ok)
local agent = { class = "org.omarchy.agent" }
focused = agent
assert(not question().ok, "Plain Up must pass through")
option = true
focused = { class = "other-app" }
assert(not question().ok, "Other applications must keep their input")
assert(#sent == 0 and #timers == 0)
focused = agent
assert(question().ok and #sent == 1 and #timers == 1)
assert(sent[1].mods == "ALT" and sent[1].key == "UP" and sent[1].state == "down")
assert(question().ok and #sent == 1, "Do not overlap synthetic key presses")
focused = { class = "other-app" }
option = false
timers[1]()
assert(#sent == 2 and sent[2].state == "up" and sent[2].mods == "ALT")
assert(sent[1].window == agent and sent[2].window == agent, "Release must target the original window")
focused, option = agent, true
assert(question().ok and #sent == 3, "The next shortcut must work after release")
timers[2]()
-- A normal terminal must receive the same chord as a specially labeled agent.
for _, class in ipairs({ "foot", "Alacritty", "kitty", "com.mitchellh.ghostty" }) do
  focused, option = { class = class }, true
  local count = #sent
  assert(question().ok and #sent == count + 1, class)
  timers[#timers]()
  assert(#sent == count + 2 and sent[#sent].window == focused)
end
local local_binding = module.install_local(api)
assert(module.install_local(api) == local_binding, "Local binding is idempotent")
assert(local_binding.keys == "MOD5 + UP")
assert(not local_binding.options.device.inclusive)
local local_question = module.question_shortcut({
  get_active_window = function() return focused end,
  is_key_down = function() error("Local Mod5 chord does not depend on remote Meta") end,
  dsp = { send_key_state = function(args) return args end },
  dispatch = function(args) sent[#sent + 1] = args end,
  timer = function(callback) timers[#timers + 1] = callback end,
}, true)
focused, option = { class = "foot" }, false
assert(local_question().ok)
timers[#timers]()
focused = { class = "browser" }
assert(not local_question().ok)
print("Mac shortcut tests passed: modifier pairs, scope, preserved actions/flags, no duplicate execution, isolated unbind, idempotence, pointer exclusions, partial-failure cleanup.")
print("Option-Up tests passed: remote device scope, plain Up passthrough, application scope, paired events, no overlapping presses, release after focus change.")
