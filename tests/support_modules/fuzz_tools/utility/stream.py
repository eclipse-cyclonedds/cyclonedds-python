import re
import io
import traceback
from typing import Any
from textwrap import wrap, indent


class Stream:
    def __init__(self):
        self._indent = 0
        self._string = io.StringIO()
        self._do_indent = False

    def _write(self, data: str):
        self._string.write(data)

    def __format_bytes(self, data: bytes) -> None:
        ls = " ".join(re.findall(".{2}", data.hex()))
        for line in wrap(ls, 3 * 16):
            self << line << self.endl

    def __lshift__(self, element: Any):
        if element == Stream.endl:
            self._write("\n")
            self._do_indent = True
        elif element == Stream.indent:
            self._indent += 4
        elif element == Stream.dedent:
            self._indent -= 4
        elif type(element) in [bytes, bytearray]:
            self.__format_bytes(element)
        elif type(element) == Stream:
            self._write(indent(element.string, ' ' * self._indent))
        else:
            txt = str(element)
            txtspl = txt.splitlines()

            if len(txtspl) > 1:
                txt = ("\n" + (' ' * self._indent)).join(txtspl)

            if self._do_indent:
                self._write(' ' * self._indent)
                self._do_indent = False

            self._write(txt)

        return self

    def write_exception(self, section: str, exc: BaseException) -> None:
        data = traceback.format_exception(exc, value = None, tb = exc.__traceback__)
        self << f"[Received exception in section {section}]" << self.endl
        for line in data:
            self._write("\n  " + (' ' * self._indent) + line)

    @property
    def string(self):
        return self._string.getvalue()

    endl = object()
    indent = object()
    dedent = object()


class FileStream(Stream):
    def __init__(self, file_object):
        self.file_object = file_object
        self._indent = 0
        self._do_indent = False

    def _write(self, data: str):
        self.file_object.write(data)

    @property
    def string(self):
        if not self.file_object.seekable:
            return None

        self.file.seek(0)
        return self.file.read()
