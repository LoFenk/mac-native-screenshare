import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = load("probe")
publisher = load("publish")


class Connection:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def sendall(self, data):
        pass

    def recv(self, count):
        value, self.data = self.data[:1], self.data[1:]
        return value


class PrototypeTests(unittest.TestCase):
    def handshake(self, methods, result):
        data = b"RFB 003.008\n" + bytes([len(methods)]) + bytes(methods) + result
        with patch.object(probe.socket, "create_connection", return_value=Connection(data)):
            probe.probe("192.0.2.1")

    def test_encrypted_methods_and_auth_rejection(self):
        self.handshake([19, 129, 5], b"\x00\x00\x00\x01")

    def test_no_auth_must_not_be_offered(self):
        with self.assertRaises(RuntimeError):
            self.handshake([1, 19], b"")

    def test_unencrypted_methods_must_not_be_offered(self):
        with self.assertRaises(RuntimeError):
            self.handshake([2, 30], b"")

    def test_no_auth_must_not_succeed(self):
        with self.assertRaises(RuntimeError):
            self.handshake([19], b"\x00\x00\x00\x00")

    def test_des_known_answer(self):
        key = bytes.fromhex("133457799BBCDFF1")
        password = bytes(int(f"{value:08b}"[::-1], 2) for value in key)
        challenge = bytes.fromhex("0123456789ABCDEF") * 2
        self.assertEqual(probe.vnc_response(password, challenge), bytes.fromhex("85E813540F0AB405") * 2)

    def test_legacy_success_and_failure(self):
        for result, expected in [(0, True), (1, False)]:
            data = b"RFB 003.008\n" + b"\0\0\0\x02" + bytes(16) + result.to_bytes(4, "big")
            with patch.object(probe.socket, "create_connection", return_value=Connection(data)):
                probe.legacy_attempt("192.0.2.1", b"testpass", expected)

    def test_legacy_cannot_accept_no_auth(self):
        data = b"RFB 003.008\n" + b"\0\0\0\x01"
        with patch.object(probe.socket, "create_connection", return_value=Connection(data)):
            with self.assertRaises(RuntimeError):
                probe.legacy_attempt("192.0.2.1", b"testpass", True)

    def test_legacy_rejects_empty_and_truncated_password(self):
        for password in (b"", b"toolongpassword"):
            with self.assertRaises(ValueError):
                probe.legacy_probe("192.0.2.1", password)

    def test_legacy_accepts_seven_character_password(self):
        with patch.object(probe, "legacy_attempt") as attempt:
            probe.legacy_probe("192.0.2.1", b"test123")
            self.assertEqual(attempt.call_args_list[1].args, ("192.0.2.1", b"test123", True))

    def test_legacy_checks_wrong_and_right_password(self):
        with patch.object(probe, "legacy_attempt") as attempt:
            probe.legacy_probe("192.0.2.1", b"testpass")
            self.assertEqual(attempt.call_count, 2)
            self.assertNotEqual(attempt.call_args_list[0].args[1], b"testpass")
            self.assertEqual(attempt.call_args_list[1].args, ("192.0.2.1", b"testpass", True))

    def test_approved_profile_and_address(self):
        with patch.object(publisher.subprocess, "check_output", return_value="approved\n192.0.2.1/24\n"):
            publisher.check_network("test0", "192.0.2.1", "approved")

    def test_same_subnet_other_profile_rejected(self):
        with patch.object(publisher.subprocess, "check_output", return_value="other\n192.0.2.1/24\n"):
            with self.assertRaises(RuntimeError):
                publisher.check_network("test0", "192.0.2.1", "approved")

    def test_changed_address_rejected(self):
        with patch.object(publisher.subprocess, "check_output", return_value="approved\n192.0.2.2/24\n"):
            with self.assertRaises(RuntimeError):
                publisher.check_network("test0", "192.0.2.1", "approved")


if __name__ == "__main__":
    unittest.main()
