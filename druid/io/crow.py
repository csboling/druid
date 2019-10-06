import asyncio
import logging
import serial
import serial.tools.list_ports
import serial.threaded

from druid.io.abstractions import AsciiHandler

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


class CrowEventHandler(AsciiHandler):
    def __init__(self, event_handlers):
        self.event_handlers = event_handlers

    def handle_line(self, line):
        if '^^' in line:
            cmds = line.split('^^')
            for cmd in cmds:
                t3 = cmd.rstrip().partition('(')
                if len(t3) != 3:
                    continue
                evt = t3[0]
                args = t3[2].rstrip(')').partition(',')

                try:
                    handler = self.event_handlers[evt]
                except KeyError:
                    continue
                else:
                    return handler(line, evt, args)


class CrowCommandHandler(CrowEventHandler):

    def __init__(self, event_handlers):
        super().__init__(event_handlers=dict(
            self.decorate_handlers(event_handlers)
        ))

    def decorate_handlers(self, handlers):
        for evt, inputs in handlers.items():
            yield (evt, self.combine_handlers(inputs))

    def combine_handlers(self, handlers):
        def handler(line, evt, args):
            logger.debug("event '{}', args {}".format(evt, args))
            if len(args) < 1:
                return False
            try:
                index = int(args[0]) - 1
            except ValueError:
                return False
            else:
                if index < 0:
                    return False
                if index < len(handlers) and handlers[index] is not None:
                    logger.info('handler found')
                    handlers[index](line, evt, args)
                    return True
        return handler


class LuaResultHandler(AsciiHandler):

    def __init__(self, output_handler):
        self.output_handler = output_handler

    def handle_line(self, line):
        if len(line) > 0:
            self.output_handler(line + '\n')
            return True
        return False


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
        self.serial = serial.Serial(
            self.comport, baudrate=115200, timeout=0.1)
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
