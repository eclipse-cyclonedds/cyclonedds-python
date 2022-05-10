"""
 * Copyright(c) 2021 to 2022 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

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

