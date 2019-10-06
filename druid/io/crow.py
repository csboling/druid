import asyncio
import logging
import serial
import serial.tools.list_ports
import serial.threaded

from druid.io.abstractions import AsciiParser

logger = logging.getLogger(__name__)


class CrowProtocol(serial.threaded.Packetizer):
    TERMINATOR = b'\n\r'

    def __init__(self,
                 on_connect=None, on_disconnect=None,
                 parsers=None):
        super().__init__()
        self.on_connect = on_connect or (lambda transport: None)
        self.on_disconnect = on_disconnect or (lambda exc: None)
        self.parsers = parsers or []

    def connection_made(self, transport):
        super().connection_made(transport)
        logger.info('connected')
        self.on_connect(transport)

    def connection_lost(self, exc):
        self.on_disconnect(exc)
        logger.error('connection lost:', exc)
        super().connection_lost(exc)

    def handle_packet(self, packet):
        logger.debug('rx: {}'.format(packet))
        for parser in self.parsers:
            if parser(packet):
                break


class CrowResponseParser(AsciiParser):
    def __init__(self,
                 in1_handler=None, in2_handler=None,
                 output_handler=None):
        self.in1_handler = in1_handler or (lambda evt, line: None)
        self.in2_handler = in2_handler or (lambda evt, line: None)
        self.output_handler = output_handler or (lambda evt, line: None)


class CrowCommandParser(CrowResponseParser):

    def parse_line(self, line):
        if '^^' in line:
            cmds = line.split('^^')
            for cmd in cmds:
                t3 = cmd.rstrip().partition('(')
                evt = t3[0]
                args = t3[2].rstrip(')').partition(',')

                if evt == "stream" or evt == "change":
                    handler = self.in1_handler
                    if args[0] == "2":
                        handler = self.in2_handler
                    handler(evt, line, args)
                    return True


class LuaParser(CrowResponseParser):

    def parse_line(self, line):
        if len(line) > 0:
            self.output_handler(None, line + '\n', None)


class CrowConnectionException(Exception):
    pass


class CrowConnection:

    def __init__(self, parsers, writer, comport=None):
        self.parsers = parsers
        self.writer = writer
        self.comport = comport or self.find_comport()

    @classmethod
    def find_comport(cls):
        for item in serial.tools.list_ports.comports():
            logger.info('comport {} - device {}'.format(item[0], item[2]))
            if 'USB VID:PID=0483:5740' in item[2]:
                port = item[0]
                logger.info('using {}'.format(port))
                return port
        logger.error('crow not found')
        raise CrowConnectionException('crow not found')

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        if value is not None:
            logger.error('crow connection failed', value)
        self.writer.detach(self.protocol)
        # self.protocol.__exit__(type, value, traceback)
        self.serial = None

    def connect(self):
        self.serial = serial.Serial(self.comport, baudrate=115200, timeout=0.1)
        self.protocol = serial.threaded.ReaderThread(
            self.serial,
            lambda: CrowProtocol(parsers=self.parsers),
        ).__enter__()
        self.writer.attach(self.protocol)

    async def listen(self):
        while True:
            try:
                self.connect()
            except serial.SerialException:
                await asyncio.sleep(1.0)
