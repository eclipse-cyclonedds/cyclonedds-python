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

from dataclasses import dataclass as __dataclass

from .main import CDR as __CDR, proto_deserialize as __deserialize, proto_serialize as __serialize


def cdr(*args, **kwargs):
    def in_cdr(cls):
        cls = __dataclass(cls)
        __CDR(cls, **kwargs)
        cls.serialize = __serialize
        cls.deserialize = classmethod(__deserialize)
        return cls

    if args:
        return in_cdr(args[0])
    return in_cdr
