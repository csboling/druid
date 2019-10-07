import asyncio
import logging

from prompt_toolkit.eventloop.defaults import use_asyncio_event_loop
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import (
    VSplit, HSplit,
    Window, WindowAlign,
)
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout.controls import FormattedTextControl

import serial

from druid.io.crow import (
    CrowConnection,
    CrowCommandHandler,
    LuaResultHandler,
)
from druid.io.grid import Grid, HelloApp
from druid.io.screen import (
    TextAreaLineDisplayer,
    TextAreaLineHandler,
    TextAreaLineWriter,
)

# monkey patch to fix https://github.com/monome/druid/issues/8
Char.display_mappings['\t'] = '  '


logger = logging.getLogger(__name__)


DRUID_INTRO = '//// druid. q to quit. h for help\n\n'
DRUID_HELP = '''
 h            this menu
 r            runs 'sketch.lua'
 u            uploads 'sketch.lua'
 r <filename> run <filename>
 u <filename> upload <filename>
 p            print current userscript
 q            quit

'''


class DruidWriter(TextAreaLineWriter):

    def write(self, s):
        try:
            super().write(s)
        except serial.SerialException as exc:
            logger.error("could not write '{}': {}".format(s, exc))
            pass

    def parse(self, cmd):
        if cmd == "q":
            raise ValueError("bye.")
        elif cmd == 'p':
            self.write('^^p')
        elif cmd == 'h':
            self.show(DRUID_HELP)
        else:
            self.write(cmd + '\r\n')


class DruidUI:

    def __init__(self):
        self.capture1 = TextArea(
            style='class:capture-field',
            height=2,
        )
        self.capture2 = TextArea(
            style='class:capture-field',
            height=2,
        )
        self.output_field = TextArea(
            style='class:output-field',
            text=DRUID_INTRO,
        )
        self.output = TextAreaLineDisplayer(self.output_field)
        self.ii_capture = TextArea(
            style='class:capture-field',
            height=2,
        )

        self.input_field = TextArea(
            height=1,
            prompt='> ',
            style='class:input-field',
            multiline=False,
            wrap_lines=False
        )

        captures = VSplit([self.capture1, self.capture2, self.ii_capture])
        container = HSplit([
            captures,
            self.output_field,
            Window(
                height=1,
                char='/',
                style='class:line',
                content=FormattedTextControl(text='druid////'),
                align=WindowAlign.RIGHT,
            ),
            self.input_field,
        ])

        self.keybindings = KeyBindings()

        @self.keybindings.add('c-c', eager=True)
        @self.keybindings.add('c-q', eager=True)
        def _(event):
            event.app.exit()

        self.style = Style([
            ('capture-field', '#747369'),
            ('output-field', '#d3d0c8'),
            ('input-field', '#f2f0ec'),
            ('line',        '#747369'),
        ])
        self.layout = Layout(container, focused_element=self.input_field)

        in1_handler = TextAreaLineHandler(
            self.capture1,
            lambda line, evt, args: '\ninput[{}] = {}\n'.format(
                args[0],
                args[1],
            ),
        )
        in2_handler = TextAreaLineHandler(
            self.capture2,
            lambda line, evt, args: 'input[{}] = {}\n'.format(
                args[0],
                args[1],
            ),
        )
        ii_handler = TextAreaLineHandler(
            self.ii_capture,
            lambda line, evt, args: '{}({})\n'.format(evt, ', '.join(args)),
        )
        output_handler = TextAreaLineHandler(
            self.output_field,
            lambda line: '{}'.format(line),
        )

        self.crow = CrowConnection(
            on_connect=lambda transport: self.show(
                '\n <connected ({})>'.format(transport.serial.port),
            ),
            on_disconnect=lambda exc: self.show('\n <disconnected>'),
            handlers=[
                CrowCommandHandler(event_handlers={
                    'stream': [
                        in1_handler,
                        in2_handler,
                    ],
                    'change': [
                        in1_handler,
                        in2_handler,
                    ],
                    'ii': ii_handler,
                }),
                LuaResultHandler(output_handler),
            ],
            writer=DruidWriter(
                input_field=self.input_field,
                output_field=self.output_field,
            ),
        )
        self.app = HelloApp()
        self.grid = Grid()

    def command(self, parser):
        parser.set_defaults(func=lambda args: self.run_forever(args))

    async def run(self):
        self.application = Application(
            layout=self.layout,
            key_bindings=self.keybindings,
            style=self.style,
            mouse_support=True,
            full_screen=True,
        )
        await self.application.run_async()

    def run_forever(self, args):
        loop = asyncio.get_event_loop()

        use_asyncio_event_loop()
        with patch_stdout():
            tasks = [
                self.crow.listen(),
                self.grid.poll(),
            ]
            background_task = asyncio.gather(*tasks, return_exceptions=True)
            loop.run_until_complete(self.run())
            background_task.cancel()
            loop.run_until_complete(background_task)

    def show(self, s):
        self.output.show(s)
