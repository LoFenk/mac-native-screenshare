"""Private real-Wayland regression for switching an active single-output viewer.

Needs the configured physical output and staged OMARCHY-SHARE-TEST output. Uses only a loopback
listener, does not send keyboard/pointer/clipboard, discards desktop pixels.
Pass the WayVNC binary and optional number of switches (default 12).
"""
import os
from pathlib import Path
import resource
import socket
import struct
import subprocess
import sys
import tempfile
import time
from probe import read_exact, vnc_response

lab = Path(__file__).resolve().parent
runtime = Path(os.environ.get('MAC_NATIVE_SCREENSHARE_RUNTIME_DIR', lab))
password_file = Path(os.environ['OMARCHY_SHARE_TEST_PASSWORD_FILE'])
password = password_file.read_bytes().strip()
physical = os.environ['OMARCHY_SHARE_PHYSICAL_OUTPUT']
physical_size = tuple(map(int, os.environ['OMARCHY_SHARE_PHYSICAL_SIZE'].split('x')))
virtual_size = tuple(map(int, os.environ['OMARCHY_SHARE_VIRTUAL_SIZE'].split('x')))
assert len(physical_size) == len(virtual_size) == 2
os.umask(0o077)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def frame(c, expected, current, bpp):
    pixels = 0
    for _ in range(60):
        header = read_exact(c, 4)
        assert header[0] == 0, 'Unexpected message type'
        for _ in range(struct.unpack('!H', header[2:])[0]):
            x, y, w, h, encoding = struct.unpack('!HHHHi', read_exact(c, 12))
            if encoding == -223:
                current = (w, h)
                pixels = 0
            elif encoding == -239:
                read_exact(c, w*h*bpp//8 + ((w+7)//8)*h)
            else:
                assert encoding == 0
                read_exact(c, w*h*bpp//8)
                if current == expected:
                    assert x+w <= expected[0] and y+h <= expected[1]
                    pixels += w*h
        if pixels >= expected[0]*expected[1]:
            return current
    raise AssertionError('Full frame at expected size not received')


with tempfile.TemporaryDirectory(prefix='output-switch-check-', dir=os.environ['XDG_RUNTIME_DIR']) as tmp:
    config = Path(tmp) / 'config'
    config.write_bytes(b'address=127.0.0.1\nport=5902\nenable_auth=true\nenable_pam=false\nrelax_encryption=true\nallow_broken_crypto=true\npassword=' + password + b'\n')
    env = dict(os.environ, LD_LIBRARY_PATH=str(runtime/'lib'), NVNC_APPLE_CLIPBOARD='1')
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen([sys.argv[1], '-r', '-C', str(config), '-S', tmp+'/control', '-o', physical, '-R', '-L', 'info'], env=env, stdout=log, stderr=log)
        try:
            for _ in range(40):
                assert process.poll() is None
                if Path(tmp+'/control').exists():
                    break
                time.sleep(.1)
            with socket.create_connection(('127.0.0.1', 5902), timeout=5) as c:
                assert read_exact(c,12) == b'RFB 003.889\n'
                c.sendall(b'RFB 003.889\n')
                assert read_exact(c,5) == b'\x04\x02\x02\x02\x02'
                c.sendall(vnc_response(password,read_exact(c,16)))
                assert read_exact(c,4) == b'\0'*4
                c.sendall(b'\xc1')
                header = read_exact(c,24)
                current = struct.unpack('!HH',header[:4]); bpp=header[4]
                read_exact(c,struct.unpack('!I',header[20:24])[0])
                c.sendall(struct.pack('!BBHiii',2,0,3,-223,-239,0))
                c.sendall(struct.pack('!BBHIHHHH',9,0,1,0xffffffff,0,0,*current))
                current=frame(c,physical_size,current,bpp)
                count = int(sys.argv[2]) if len(sys.argv)>2 else 12
                for index in range(count):
                    output, expected = ('OMARCHY-SHARE-TEST',virtual_size) if index%2==0 else (physical,physical_size)
                    subprocess.run([str(runtime/'bin/wayvncctl'),'-S',tmp+'/control','output-set',output],check=True,stdout=subprocess.DEVNULL,timeout=3)
                    c.sendall(struct.pack('!BBHHHH',3,0,0,0,*expected))
                    current=frame(c,expected,current,bpp)
                    assert process.poll() is None
                print(f'{count} live output switches passed with full frames at both resolutions.',flush=True)
        except Exception:
            log.seek(0)
            print(log.read().decode(errors='replace')[-2500:])
            raise
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=5)
