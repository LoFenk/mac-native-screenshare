"""Authenticated frame geometry check; discard pixels and send no input/clipboard.

Usage: python check-native-frame.py address port password-file width height
"""
from pathlib import Path
import socket
import struct
import sys

from probe import read_exact, vnc_response

address, port, password_file, width, height = sys.argv[1:]
width, height = int(width), int(height)
password = Path(password_file).read_bytes().rstrip(b'\r\n')
with socket.create_connection((address, int(port)), timeout=8) as c:
    assert read_exact(c, 12) == b'RFB 003.889\n'
    c.sendall(b'RFB 003.889\n')
    assert read_exact(c, 5) == b'\x04\x02\x02\x02\x02'
    c.sendall(vnc_response(password, read_exact(c, 16)))
    assert read_exact(c, 4) == b'\0' * 4
    c.sendall(b'\xc1')
    header = read_exact(c, 24)
    assert struct.unpack('!HH', header[:4]) == (width, height)
    bpp = header[4]
    name = read_exact(c, struct.unpack('!I', header[20:24])[0])
    assert name[6 + 21 // 8] & (0x80 >> (21 % 8)), 'Clipboard capability missing'
    c.sendall(struct.pack('!BBHii', 2, 0, 2, -239, 0))
    c.sendall(struct.pack('!BBHHHH', 3, 0, 0, 0, width, height))
    c.sendall(struct.pack('!BBHIHHHH', 9, 0, 1, 0xffffffff, 0, 0, width, height))
    cursor_hidden = False
    pixels = 0
    for _ in range(8):
        update = read_exact(c, 4)
        assert update[0] == 0
        for _ in range(struct.unpack('!H', update[2:])[0]):
            x, y, w, h, encoding = struct.unpack('!HHHHi', read_exact(c, 12))
            if encoding == -239:
                assert (w, h) == (0, 0), 'Separate cursor should be hidden with overlay'
                cursor_hidden = True
            else:
                assert encoding == 0
                assert x + w <= width and y + h <= height
                read_exact(c, w * h * bpp // 8)
                pixels += w * h
        if pixels >= width * height and cursor_hidden:
            break
    assert pixels >= width * height and cursor_hidden
    c.sendall(struct.pack('!BBHIHHHH', 9, 0, 0, 0xffffffff, 0, 0, 0, 0))
    print(f'Authenticated {width}x{height} full frame and cursor overlay state verified; pixels discarded.')
