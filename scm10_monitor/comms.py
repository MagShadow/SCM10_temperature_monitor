import socket
from dataclasses import dataclass
from typing import Optional

import serial
from serial.tools import list_ports


@dataclass
class SerialConfig:
    port: str
    baud: int
    timeout_s: float


@dataclass
class EthernetConfig:
    ip: str
    port: int
    timeout_s: float


class InstrumentConnection:
    def open(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def is_open(self) -> bool:
        raise NotImplementedError

    def query(self, command: str, terminator: str) -> str:
        raise NotImplementedError


class SerialConnection(InstrumentConnection):
    def __init__(self, config: SerialConfig):
        self.config = config
        self._serial: Optional[serial.Serial] = None

    def open(self) -> None:
        if self._serial and self._serial.is_open:
            return
        self._serial = serial.Serial(
            port=self.config.port,
            baudrate=self.config.baud,
            timeout=self.config.timeout_s,
        )

    def close(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.close()

    def is_open(self) -> bool:
        return bool(self._serial and self._serial.is_open)

    def query(self, command: str, terminator: str) -> str:
        if not self._serial:
            raise RuntimeError("Serial connection not open")
        payload = f"{command}{terminator}".encode("ascii", errors="ignore")
        self._serial.reset_input_buffer()
        self._serial.write(payload)
        if terminator:
            data = self._serial.read_until(terminator.encode("ascii", errors="ignore"))
        else:
            data = self._serial.readline()
        return data.decode("ascii", errors="ignore").strip()


class EthernetConnection(InstrumentConnection):
    def __init__(self, config: EthernetConfig):
        self.config = config
        self._sock: Optional[socket.socket] = None

    def open(self) -> None:
        if self._sock:
            return
        self._sock = socket.create_connection(
            (self.config.ip, self.config.port),
            timeout=self.config.timeout_s,
        )
        self._sock.settimeout(self.config.timeout_s)

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self._sock.close()
            finally:
                self._sock = None

    def is_open(self) -> bool:
        return self._sock is not None

    def query(self, command: str, terminator: str) -> str:
        if not self._sock:
            raise RuntimeError("Ethernet connection not open")
        payload = f"{command}{terminator}".encode("ascii", errors="ignore")
        self._sock.sendall(payload)
        return _recv_until(self._sock, terminator)


def _recv_until(sock: socket.socket, terminator: str) -> str:
    if not terminator:
        terminator = "\n"
    term_bytes = terminator.encode("ascii", errors="ignore")
    data = bytearray()
    while True:
        chunk = sock.recv(1024)
        if not chunk:
            break
        data.extend(chunk)
        if term_bytes in data:
            break
    return data.decode("ascii", errors="ignore").strip()


def available_serial_ports() -> list[str]:
    return [port.device for port in list_ports.comports()]
