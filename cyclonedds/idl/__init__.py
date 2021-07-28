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

from dataclasses import dataclass, is_dataclass

from .main import IDL, proto_deserialize, proto_serialize


def idl(*args, **kwargs):
    def in_idl(cls):
        if not is_dataclass(cls):
            cls = dataclass(cls)
        
        IDL(cls, **kwargs)
        cls.serialize = proto_serialize
        cls.deserialize = classmethod(proto_deserialize)
        
        return cls

    if args:
        return in_idl(args[0])
    return in_idl


__all__ = ["idl"]
