from prompt_toolkit.application.current import get_app
from prompt_toolkit.document import Document
from prompt_toolkit.widgets import TextArea

from druid.io.abstractions import LineHandler, UTF8Writer


class TextAreaLineDisplayer:
    def __init__(self, textarea: TextArea, fmt_func=None):
        self.textarea = textarea
        self.fmt_func = fmt_func

    def show(self, text):
        s = self.textarea.text + self.fmt(text)
        self.textarea.buffer.document = Document(
            text=s,
            cursor_position=len(s),
        )

    def fmt(self, text):
        if self.fmt_func is not None:
            return self.fmt_func(text)
        else:
            return text


class TextAreaLineHandler(LineHandler):
    def __init__(self, textarea: TextArea):
        self.displayer = TextAreaLineDisplayer(textarea)

    def __call__(self, evt, line, args):
        self.displayer.show(self.fmt(evt, line, args))

    def fmt(self, evt, line, args):
        return '{}({})'.format(evt, ','.join(args))


class FormattedTextAreaLineHandler(TextAreaLineHandler):
    def __init__(self, textarea: TextArea, fmt):
        super().__init__(textarea)
        self.fmt_func = fmt

    def fmt(self, evt, line, args):
        return self.fmt_func(evt, line, args)


class TextAreaLineWriter(UTF8Writer):
    def __init__(self,
                 input_field: TextArea, output_field: TextArea):
        self.input_field = input_field
        self.input_field.accept_handler = self.accept
        self.displayer = TextAreaLineDisplayer(
            output_field,
            lambda s: '\n> {}\n'.format(s),
        )

    def accept(self, buff):
        try:
            self.parse(self.input_field.text)
            self.displayer.show(self.input_field.text)
        except Exception as exc:
            self.error(exc)

    def error(self, exc):
        print(exc)
        get_app().exit()

    def parse(self, cmd):
        pass

    def show(self, s):
        self.displayer.show(s)
