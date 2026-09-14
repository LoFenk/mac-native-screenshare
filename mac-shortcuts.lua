-- Prototype: translate Apple Screen Sharing keyboard shortcuts at registration.
-- Application input is unchanged except for Option-Up in the agent terminal.
local M = {}
-- Hyprland suffixes the device name when normal sharing and the clipboard
-- trial are connected together. Both use the same Mac shortcut translation.
local remote_keyboards = { "hl-virtual-keyboard-wayvnc", "hl-virtual-keyboard-wayvnc-1" }

local function normalize(keys)
  return keys:gsub("%s+", ""):upper()
end

function M.translate(keys)
  local parts, super, alt = {}, false, false
  for raw_part in keys:gmatch("[^+]+") do
    local part = raw_part:match("^%s*(.-)%s*$")
    local modifier = part:upper()
    if modifier == "SUPER" then
      part, super = "ALT", true
    elseif modifier == "ALT" then
      part, alt = "SUPER", true
    end
    parts[#parts + 1] = part
  end
  return table.concat(parts, " + "), super ~= alt
end

local function copy(options)
  local result = {}
  for key, value in pairs(options or {}) do result[key] = value end
  return result
end

function M.question_shortcut(api)
  local sending = false
  return function()
    local window = api.get_active_window()
    -- Apple's Option arrives as XKB <META> (205), with no active modifier.
    -- Let ordinary Up and other applications receive their original input.
    if not window or window.class ~= "org.omarchy.agent" or not api.is_key_down(205) then
      return { ok = false }
    end
    if sending then return { ok = true } end

    sending = true
    api.dispatch(api.dsp.send_key_state({ mods = "ALT", key = "UP", state = "down", window = window }))
    -- Match Omarchy's clipboard forwarding workaround for synthetic repeats.
    -- Target the same window on release even if focus changes in the meantime.
    api.timer(function()
      api.dispatch(api.dsp.send_key_state({ mods = "ALT", key = "UP", state = "up", window = window }))
      sending = false
    end, { timeout = 50, type = "oneshot" })
    return { ok = true }
  end
end

function M.install(api)
  if api.omarchy_mac_shortcuts then return api.omarchy_mac_shortcuts end
  local original_bind, original_unbind = api.bind, api.unbind
  local families = {}
  local state = { translated = 0, unchanged = 0, families = families }

  api.bind = function(keys, dispatcher, options)
    local translated, changes = M.translate(keys)
    local pointer = (options and options.mouse) or keys:lower():find("mouse", 1, true)
    local scoped = options and (options.device or options.devices)
    if not changes or pointer or scoped then
      state.unchanged = state.unchanged + 1
      return original_bind(keys, dispatcher, options)
    end

    local local_options, remote_options = copy(options), copy(options)
    local_options.device = { inclusive = false, list = remote_keyboards }
    remote_options.device = { inclusive = true, list = remote_keyboards }
    local primary = original_bind(keys, dispatcher, local_options)
    local ok, remote = pcall(original_bind, translated, dispatcher, remote_options)
    if not ok or not remote then
      primary:set_enabled(false)
      error(ok and "Remote shortcut registration failed" or remote)
    end

    local pair = { primary, remote }
    function pair:set_enabled(enabled)
      for _, binding in ipairs(self) do binding:set_enabled(enabled) end
    end
    function pair:is_enabled() return primary:is_enabled() end
    -- Hyprland 0.56.2's handle:remove() also removes other bindings with the
    -- same key/mask. Disable exactly these handles; reload reclaims them.
    function pair:remove() self:set_enabled(false) end
    pair.unbind = pair.remove
    setmetatable(pair, { __index = function(_, key) return primary[key] end })

    local key = normalize(keys)
    families[key] = families[key] or {}
    families[key][#families[key] + 1] = pair
    state.translated = state.translated + 1
    return pair
  end

  api.unbind = function(keys)
    if keys == "all" then
      for key in pairs(families) do families[key] = nil end
      return original_unbind(keys)
    end
    local key = normalize(keys)
    if not families[key] then return original_unbind(keys) end
    -- Do not unbind the opposite modifier's unrelated physical-keyboard action.
    for _, pair in ipairs(families[key]) do pair:remove() end
    families[key] = nil
  end

  state.question_binding = original_bind("UP", M.question_shortcut(api), {
    description = "Mac sharing: Option-Up for agent questions",
    auto_consuming = true,
    device = { inclusive = true, list = remote_keyboards },
  })
  api.omarchy_mac_shortcuts = state
  return state
end

return M
