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

import sys


if sys.version_info < (3, 9):
    raise NotImplementedError("This package cannot be used in Python version 3.8 or lower.")
else:
    # We are in any Python 3.9 or 3.10 (maybe higher?) version
    from typing import Annotated, get_origin, get_args, get_type_hints, Any  # noqa F401

if sys.version_info >= (3,14):
    import annotationlib
    def get_annotations(cls: Any) -> dict[str, Any]:
        return annotationlib.get_annotations(cls)
elif sys.version_info >= (3, 10):
    import inspect
    def get_annotations(cls: Any) -> dict[str, Any]:
        return inspect.get_annotations(cls)
else:
    def get_annotations(cls: Any) -> dict[str, Any]:
        if isinstance(cls, type):
            return cls.__dict__.get('__annotations__', {})
        else:
            return getattr(cls, '__annotations__', {})


__all__ = ["Annotated", "get_origin", "get_args", "get_type_hints"]
