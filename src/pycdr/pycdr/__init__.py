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

from dataclasses import dataclass

from .main import CDR, proto_deserialize, proto_serialize


def cdr(*args, **kwargs):
    def in_cdr(cls):
        cls = dataclass(cls)
        CDR(cls, **kwargs)
        cls.serialize = proto_serialize
        cls.deserialize = classmethod(proto_deserialize)
        return cls

    if args:
        return in_cdr(args[0])
    return in_cdr
