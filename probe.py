"""Test RFB security without requesting desktop content or sending input."""

import ctypes
import ctypes.util
import socket
import struct
import sys


def read_exact(connection, length):
    value = b""
    while len(value) < length:
        chunk = connection.recv(length - len(value))
        if not chunk:
            raise EOFError("Server closed the connection")
        value += chunk
    return value


def probe(address):
    with socket.create_connection((address, 5900), timeout=3) as connection:
        banner = read_exact(connection, 12)
        if not banner.startswith(b"RFB 003."):
            raise RuntimeError(f"Unexpected protocol: {banner!r}")
        connection.sendall(b"RFB 003.008\n")
        count = read_exact(connection, 1)[0]
        if not count:
            raise RuntimeError("Server offered no security types")
        methods = list(read_exact(connection, count))
        # VeNCrypt (19), RA2 (5), and RA2_256 (129) support encrypted sessions.
        if not set(methods).issubset({19, 5, 129}):
            raise RuntimeError(f"Unexpected security types in encrypted-only mode: {methods}")
        connection.sendall(b"\x01")  # Deliberately request unoffered None auth.
        try:
            result = struct.unpack("!I", read_exact(connection, 4))[0]
        except EOFError:
            result = 1
        if result != 1:
            raise RuntimeError("Server did not reject unoffered None authentication")
        print(f"RFB negotiation checked: {banner.strip().decode()}, security types {methods}; None authentication rejected.")


def vnc_response(password, challenge):
    if len(challenge) != 16:
        raise ValueError("A VNC challenge must contain 16 bytes")
    library = ctypes.util.find_library("nettle")
    if not library:
        raise RuntimeError("The installed Nettle library is required for this test")
    nettle = ctypes.CDLL(library)

    class DESContext(ctypes.Structure):
        _fields_ = [("key", ctypes.c_uint32 * 32)]

    byte_pointer = ctypes.POINTER(ctypes.c_uint8)
    nettle.nettle_des_set_key.argtypes = [ctypes.POINTER(DESContext), byte_pointer]
    nettle.nettle_des_set_key.restype = ctypes.c_int
    nettle.nettle_des_encrypt.argtypes = [ctypes.POINTER(DESContext), ctypes.c_size_t, byte_pointer, byte_pointer]
    nettle.nettle_des_encrypt.restype = None
    # VNC reverses each password byte's bits before using it as a DES key.
    key = bytes(int(f"{value:08b}"[::-1], 2) for value in password[:8].ljust(8, b"\0"))
    key_buffer = (ctypes.c_uint8 * 8).from_buffer_copy(key)
    source = (ctypes.c_uint8 * 16).from_buffer_copy(challenge)
    result = (ctypes.c_uint8 * 16)()
    context = DESContext()
    nettle.nettle_des_set_key(ctypes.byref(context), key_buffer)
    nettle.nettle_des_encrypt(ctypes.byref(context), 16, result, source)
    return bytes(result)


def legacy_attempt(address, password, expect_success, unix=False):
    if unix:
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(3)
        try:
            connection.connect(address)
        except BaseException:
            connection.close()
            raise
    else:
        connection = socket.create_connection((address, 5900), timeout=3)
    with connection:
        if not read_exact(connection, 12).startswith(b"RFB 003."):
            raise RuntimeError("Unexpected RFB banner")
        connection.sendall(b"RFB 003.003\n")
        method = struct.unpack("!I", read_exact(connection, 4))[0]
        if method != 2:
            raise RuntimeError(f"Expected password authentication for RFB 3.3, received type {method}")
        challenge = read_exact(connection, 16)
        connection.sendall(vnc_response(password, challenge))
        result = struct.unpack("!I", read_exact(connection, 4))[0]
        if expect_success and result != 0:
            raise RuntimeError("The correct temporary password was rejected")
        if not expect_success and result != 1:
            raise RuntimeError("The incorrect password was not explicitly rejected")
        # Close before ClientInit: no framebuffer, clipboard, or input requested.


def legacy_probe(address, password, unix=False):
    if not 1 <= len(password) <= 8:
        raise ValueError("The legacy test requires one to eight password bytes")
    wrong = bytes([password[0] ^ 1]) + password[1:]
    if unix:
        legacy_attempt(address, wrong, False, unix=True)
        legacy_attempt(address, password, True, unix=True)
    else:
        legacy_attempt(address, wrong, False)
        legacy_attempt(address, password, True)
    print("RFB 3.3 DES authentication checked: incorrect password rejected; correct password accepted. No desktop content requested.")


if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "encrypted"
    if mode == "legacy":
        password_line = next((line for line in sys.stdin.buffer if line.startswith(b"Password: ")), b"")
        legacy_probe(sys.argv[1], password_line.removeprefix(b"Password: ").rstrip(b"\r\n"))
    elif mode == "encrypted":
        probe(sys.argv[1])
    else:
        raise ValueError("Unknown authentication probe mode")
