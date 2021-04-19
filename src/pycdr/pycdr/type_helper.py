"""
 * Copyright(c) 2021 ADLINK Technology Limited and others
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


if sys.version_info < (3, 6):
    raise NotImplementedError("This package cannot be used in Python version 3.5 or lower.")
elif sys.version_info < (3, 7):
    # We are in any Python 3.6 version
    from typing_extensions import Annotated
    from typing_inspect import get_origin, get_args
    from typing import get_type_hints as _get_type_hints
    def get_type_hints(cls, include_extras=False):
        return _get_type_hints(cls)
elif sys.version_info < (3, 9):
    # We are in any Python 3.7 or 3.8 version
    from typing_extensions import Annotated, get_origin, get_args, get_type_hints
else:
    # We are in any Python 3.9 or 3.10 (maybe higher?) version
    from typing import Annotated, get_origin, get_args, get_type_hints
