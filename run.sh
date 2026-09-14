#!/bin/bash

# Temporary compatibility test, not a production Omarchy service.
set -euo pipefail
umask 077
ulimit -c 0

if (( $# < 4 || $# > 5 )); then
  echo "Usage: bash run.sh <interface> <host-ipv4> <network-uuid> <output> [encrypted|legacy]" >&2
  exit 2
fi

interface="$1"
address="$2"
connection="$3"
output="$4"
mode="${5:-encrypted}"
if [[ $mode != "encrypted" && $mode != "legacy" ]]; then
  echo "Unknown authentication mode; refusing to start." >&2
  exit 2
fi
lab_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
wayvnc_command=(wayvnc)
case "${OMARCHY_NATIVE_CLIPBOARD:-0}" in
  0) ;;
  1)
    if [[ $mode != "legacy" || ! -r $lab_dir/native-clipboard/lib/libneatvnc.so.1 || ! -x $lab_dir/native-clipboard/bin/wayvnc ]]; then
      echo "Native clipboard requires the tested private builds and approved legacy mode." >&2
      exit 2
    fi
    wayvnc_command=(env "LD_LIBRARY_PATH=$lab_dir/native-clipboard/lib" NVNC_APPLE_CLIPBOARD=1 "$lab_dir/native-clipboard/bin/wayvnc" -r)
    ;;
  *) echo "Invalid native clipboard setting." >&2; exit 2 ;;
esac
: "${XDG_RUNTIME_DIR:?Run in the graphical user session}"
: "${WAYLAND_DISPLAY:?Run in the graphical user session}"
[[ -d $XDG_RUNTIME_DIR && -O $XDG_RUNTIME_DIR ]] || exit 1

runtime="$(mktemp -d "$XDG_RUNTIME_DIR/omarchy-screen-sharing.XXXXXXXX")"
server_pid=""
publisher_pid=""
cleanup() {
  trap - EXIT INT TERM
  for child in "$publisher_pid" "$server_pid"; do
    if [[ -n $child ]]; then
      kill "$child" 2>/dev/null || true
      wait "$child" 2>/dev/null || true
    fi
  done
  # These are exclusively files generated in this invocation's private directory.
  rm -f -- "$runtime/config" "$runtime/login.txt" "$runtime/tls-key.pem" "$runtime/tls-cert.pem" "$runtime/rsa-key.pem"
  if [[ -S $runtime/control ]]; then
    rm -- "$runtime/control"
  fi
  rmdir -- "$runtime" || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Keep secrets in private runtime files, never in argv or the journal.
if [[ $mode == "legacy" ]]; then
  if [[ -n ${CREDENTIALS_DIRECTORY:-} && -f $CREDENTIALS_DIRECTORY/password ]]; then
    password="$(< "$CREDENTIALS_DIRECTORY/password")"
    if [[ ! $password =~ ^[a-zA-Z0-9+/]{1,8}$ ]]; then
      echo "The test password must contain one to eight ASCII letters, digits, + or /." >&2
      exit 2
    fi
  else
    # Six random bytes give eight Base64 characters; legacy VNC uses only eight.
    password="$(openssl rand -base64 6)"
  fi
  printf 'Password: %s\nNo username is needed for legacy VNC authentication.\n' "$password" > "$runtime/login.txt"
  printf '%s\n' \
    "address=$address" "port=5900" "enable_auth=true" "enable_pam=false" \
    "password=$password" "relax_encryption=true" "allow_broken_crypto=true" > "$runtime/config"
  echo "Approved legacy test: password authentication is required; desktop transport is NOT encrypted."
else
  password="$(openssl rand -base64 24)"
  printf 'Username: omarchy\nPassword: %s\n' "$password" > "$runtime/login.txt"
  openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:secp384r1 -sha384 -days 1 -nodes \
    -keyout "$runtime/tls-key.pem" -out "$runtime/tls-cert.pem" \
    -subj /CN=omarchy-screen.local -addext "subjectAltName=DNS:omarchy-screen.local,IP:$address" 2>/dev/null
  openssl genrsa -traditional -out "$runtime/rsa-key.pem" 2048 2>/dev/null
  printf '%s\n' \
    "address=$address" "port=5900" "enable_auth=true" "enable_pam=false" \
    "username=omarchy" "password=$password" "relax_encryption=false" "allow_broken_crypto=false" \
    "private_key_file=$runtime/tls-key.pem" "certificate_file=$runtime/tls-cert.pem" \
    "rsa_private_key_file=$runtime/rsa-key.pem" > "$runtime/config"
fi
unset password

python "$lab_dir/publish.py" --check "$interface" "$address" "$connection"
"${wayvnc_command[@]}" -C "$runtime/config" -S "$runtime/control" -o "$output" -R -n Omarchy -L info &
server_pid=$!

ready=false
for (( attempt = 0; attempt < 50; attempt++ )); do
  kill -0 "$server_pid" 2>/dev/null || break
  if wayvncctl -S "$runtime/control" version >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 0.1
done
if [[ $ready != "true" ]]; then
  echo "WayVNC did not become ready; nothing will be advertised." >&2
  exit 1
fi

python "$lab_dir/probe.py" "$address" "$mode" < "$runtime/login.txt"
echo "Prototype mode=$mode is listening. Credentials are in $runtime/login.txt"
python "$lab_dir/publish.py" "$interface" "$address" "$connection" &
publisher_pid=$!
wait -n "$server_pid" "$publisher_pid"
