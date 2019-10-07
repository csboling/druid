import asyncio
import logging
import monome
import random


logger = logging.getLogger(__name__)


class EchoApp(monome.GridApp):
    def on_grid_ready(self):
        logger.debug('grid ready.')

    def on_grid_key(self, x, y, s):
        logger.debug('grid key: {} {} {}'.format(x, y, s))
        self.grid.led_set(x, y, s)


class CrowFaders(monome.GridApp):
    FADERS_MAX_VALUE = 100

    def __init__(self, crow):
        super().__init__()
        self.crow = crow
        self.width = 4

    def on_grid_ready(self):
        logger.debug('grid ready.')
        self.grid.led_all(0)

        self.row_values = []
        row_value = 0
        for i in range(self.grid.height):
            self.row_values.append(int(round(row_value)))
            row_value += self.FADERS_MAX_VALUE / (self.grid.height - 1)

        self.values = [
            random.randint(0, self.FADERS_MAX_VALUE)
            for f in range(self.width)
        ]
        self.faders = [
            asyncio.async(self.fade_to(f, 0))
            for f in range(self.width)
        ]

    def on_grid_key(self, x, y, s):
        logger.debug('grid key: {} {} {}'.format(x, y, s))
        if s == 1 and x <= 3:
            self.faders[x].cancel()
            self.faders[x] = asyncio.async(
                self.fade_to(x, self.row_to_value(y)))
            self.crow.write(
                'output[{}].volts = {}\n'.format(
                    x + 1,
                    5.0 / y,
                )
            )

    def value_to_row(self, value):
        return sorted(
            [i for i in range(self.grid.height)],
            key=lambda i: abs(self.row_values[i] - value)
        )[0]

    def row_to_value(self, row):
        return self.row_values[self.grid.height - 1 - row]

    async def fade_to(self, x, new_value):
        while self.values[x] != new_value:
            if self.values[x] < new_value:
                self.values[x] += 1
            else:
                self.values[x] -= 1
            col = [0 if c > self.value_to_row(
                self.values[x]) else 1 for c in range(self.grid.height)]
            col.reverse()
            self.grid.led_col(x, 0, col)
            await asyncio.sleep(1/100)


class Grid:
    def __init__(self, app):
        self.app = app

        def device_added(id, type, port):
            logger.info('serialosc device attached to {}: {} ({})'.format(
                port,
                id,
                type,
            ))
            asyncio.ensure_future(
                self.app.grid.connect('127.0.0.1', port))

        self.serialosc = monome.SerialOsc()
        self.serialosc.device_added_event.add_handler(device_added)

    def poll(self):
        return self.serialosc.connect()
