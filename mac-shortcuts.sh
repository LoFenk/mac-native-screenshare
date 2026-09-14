#!/bin/bash
set -euo pipefail
umask 077

: "${XDG_RUNTIME_DIR:?Run in the graphical user session}"
[[ $XDG_RUNTIME_DIR == "/run/user/$(id -u)" ]] || exit 1
directory="$XDG_RUNTIME_DIR/omarchy-screen-sharing-keyboard"
[[ -d $directory && -O $directory ]] || exit 1

case "${1:-}" in
  start)
    systemctl --user is-active --quiet omarchy-screen-sharing-prototype.service
    # Generated runtime state, private and removed by the service on stop.
    printf '%s\n' enabled > "$directory/enabled"
    ;;
  stop)
    rm -f -- "$directory/enabled"
    ;;
  *) exit 2 ;;
esac

hyprctl reload
errors="$(hyprctl configerrors)"
if [[ -n ${errors//[[:space:]]/} ]]; then
  printf '%s\n' "$errors" >&2
  exit 1
fi

if [[ $1 == start ]]; then
  result="$(hyprctl eval 'assert(hl.omarchy_mac_shortcuts and hl.omarchy_mac_shortcuts.translated > 0)')"
  [[ $result == ok ]] || { printf '%s\n' "$result" >&2; exit 1; }
fi
