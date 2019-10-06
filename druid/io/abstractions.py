from abc import ABCMeta, abstractmethod


class SerialPacketParser(metaclass=ABCMeta):
    @abstractmethod
    def __call__(self, packet: bytes) -> bool:
        pass


class AsciiParser(SerialPacketParser):
    def __call__(self, packet):
        return self.parse_line(packet.decode('ascii'))


class LineHandler(metaclass=ABCMeta):
    @abstractmethod
    def __call__(self, evt: str, line: str, args: [str]):
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
