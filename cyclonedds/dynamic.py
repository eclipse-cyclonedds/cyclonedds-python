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

import asyncio
import concurrent.futures
from typing import Union, Dict, Tuple
from collections import deque

from . import _clayer as cl
from .internal import feature_type_discovery
from .core import DDSException
from .domain import DomainParticipant
from .idl import IdlBitmask, IdlEnum, IdlUnion, IdlStruct
from .idl._xt_builder import XTInterpreter, XTTypeIdScanner
from .idl._typesupport.DDS.XTypes._ddsi_xt_type_object import TypeIdentifier, TypeObject


def get_types_for_typeid(participant: DomainParticipant, type_id: TypeIdentifier, timeout: int) -> \
        Tuple[Union[IdlUnion, IdlStruct], Dict[str, Union[IdlUnion, IdlStruct, IdlEnum, IdlBitmask]]]:
    """Attempt to gather the Python types that match a TypeIdentifier. This might involve several
    network roundtrips to request necessary type information.

    Returns
    -------
    (Type, Dict[str, Type])
        Returns a type that can be used in Topic creation (IdlUnion or IdlStruct subclass), as well as all
        types by name that appear at some nesting inside the main type (IdlUnion, IdlStruct, IdlEnum or IdlBitmask)

    Raises
    ------
    DDSException
        If ENABLE_TYPE_DISCOVERY is not set upon compiling Cyclone DDS this does not work.
    """
    if not feature_type_discovery:
        raise DDSException(DDSException.DDS_RETCODE_ILLEGAL_OPERATION, "CycloneDDS was not compiled with type support")

    typemap = {}
    to_resolve = deque((type_id,))

    while to_resolve:
        tid = to_resolve.pop()
        if tid in typemap:
            continue

        # ddspy_get_typeobj releases gil
        ret = cl.ddspy_get_typeobj(participant._ref, tid.serialize(use_version_2=True)[4:], timeout)
        if type(ret) == int:
            raise DDSException(ret, f"Could not fetch typeobject for {tid}")

        try:
            type_object = TypeObject.deserialize(ret, has_header=False, use_version_2=True)
        except Exception as e:
            raise DDSException(DDSException.DDS_RETCODE_ERROR, "Got invalid TypeObject from C layer.") from e

        for dep_tid in XTTypeIdScanner.find_all_typeids(type_object):
            to_resolve.append(dep_tid)

        typemap[tid] = type_object

    return XTInterpreter.xt_to_class(type_id, typemap)


async def async_get_types_for_typeid(participant: DomainParticipant, type_id: TypeIdentifier, timeout: int) -> \
        Tuple[Union[IdlUnion, IdlStruct], Dict[str, Union[IdlUnion, IdlStruct, IdlEnum, IdlBitmask]]]:
    """Async version of get_types_for_typeid. Runs in separate thread."""
    if not feature_type_discovery:
        raise DDSException(DDSException.DDS_RETCODE_ILLEGAL_OPERATION, "CycloneDDS was not compiled with type support")

    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, get_types_for_typeid, participant, type_id, timeout)
