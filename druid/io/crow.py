import asyncio
from functools import reduce
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
                 handlers=None):
        super().__init__()
        self.on_connect = on_connect or (lambda transport: None)
        self.on_disconnect = on_disconnect or (lambda exc: None)
        self.handlers = handlers or []

    def connection_made(self, transport):
        super().connection_made(transport)
        logger.info('connected')
        self.on_connect(transport)

    def connection_lost(self, exc):
        self.on_disconnect(exc)
        logger.error('connection lost:', exc)
        # super().connection_lost(exc)

    def handle_packet(self, packet):
        logger.debug('rx: {}'.format(packet))
        for handler in self.handlers:
            if handler(packet):
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
                args = t3[2].rstrip(')').split(',')

                logger.debug("event '{}', args {}".format(evt, args))
                curr = self.event_handlers
                for cmp in evt.split('.'):
                    try:
                        curr = curr[cmp]
                    except KeyError:
                        break
                    else:
                        if hasattr(curr, '__call__'):
                            return curr(line, evt, args)


class CrowCommandHandler(CrowEventHandler):

    def __init__(self, event_handlers):
        super().__init__(event_handlers=dict(
            self.decorate_handlers(event_handlers)
        ))

    def decorate_handlers(self, handlers):
        for evt, inputs in handlers.items():
            yield from self.combine_handlers(evt, inputs)

    def combine_handlers(self, evt, handlers):
        if evt == 'stream' or evt == 'change':
            yield from self.combine_io_handlers(evt, handlers)
        if evt[:2] == 'ii':
            yield (evt, handlers)

    def combine_io_handlers(self, evt, handlers):
        def handler(line, evt, args):
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
        yield (evt, handler)


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

    def __init__(self, writer, comport=None, **protocol_args):
        self.protocol_args = protocol_args
        self.writer = writer
        self.comport = comport

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

    # def __enter__(self):
    #     self.connect()
    #     return self

    # def __exit__(self, type, value, traceback):
    #     if value is not None:
    #         logger.error('crow connection failed', value)
    #     self.writer.detach(self.protocol)
    #     if self.protocol is not None:
    #         self.protocol.__exit__(type, value, traceback)
    #     self.serial = None

    def connect(self):
        if self.comport is None:
            self.comport = self.find_comport()
        self.serial = serial.Serial(
            self.comport, baudrate=115200, timeout=0.1)
        self.protocol = serial.threaded.ReaderThread(
            self.serial,
            lambda: CrowProtocol(**self.protocol_args),
        ).__enter__()
        self.writer.attach(self.protocol)

    async def listen(self):
        while True:
            try:
                self.connect()
            except (serial.SerialException, CrowConnectionException):
                await asyncio.sleep(1.0)
