from abc import ABCMeta, abstractmethod


class SerialPacketHandler(metaclass=ABCMeta):
    @abstractmethod
    def __call__(self, packet: bytes) -> bool:
        pass


class AsciiHandler(SerialPacketHandler):
    def __call__(self, packet):
        return self.handle_line(packet.decode('ascii'))

    @abstractmethod
    def handle_line(self, line: str) -> bool:
        pass


class LineHandler(metaclass=ABCMeta):
    @abstractmethod
    def __call__(self, line: str):
        pass


class SerialWriter:
    def attach(self, protocol):
        self.protocol = protocol

    def detach(self, protocol):
        self.protocol = None

    def write(self, s):
        self.protocol.transport.write(s)


class UTF8Writer(SerialWriter):
    def write(self, s):
        super().write(bytes(s, 'utf-8'))
