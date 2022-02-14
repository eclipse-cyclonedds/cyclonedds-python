from setuptools.command.build_ext import build_ext as _build_ext
from setuptools import Extension


class Library(Extension):
    pass


class build_ext(_build_ext):
    def get_libraries(self, ext):
        if isinstance(ext, Library):
            return ext.libraries
        return super().get_libraries(ext)

    def get_export_symbols(self, ext):
        if isinstance(ext, Library):
            return ext.export_symbols
        return super().get_export_symbols(ext)

