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

from typing import Tuple
from cyclonedds.idl._typesupport.DDS.XTypes import TypeInformation, TypeMapping


def type_info_equivalence(a: TypeInformation, b: TypeInformation) -> Tuple[bool, str]:
    if a.minimal.typeid_with_size != b.minimal.typeid_with_size:
        return False, "Minimal typeid_with_size not equal"
    if a.complete.typeid_with_size != b.complete.typeid_with_size:
        return False, "Complete typeid_with_size not equal"
    if a.minimal.dependent_typeid_count != b.minimal.dependent_typeid_count:
        return False, "Minimal dependent_typeid_count not equal"
    if a.complete.dependent_typeid_count != b.complete.dependent_typeid_count:
        return False, "Complete dependent_typeid_count not equal"

    for type_id_a in a.minimal.dependent_typeids:
        for type_id_b in b.minimal.dependent_typeids:
            if type_id_a == type_id_b:
                break
        else:
            return False, f"Minimal Type ID {type_id_a} was unmatched."

    for type_id_a in a.complete.dependent_typeids:
        for type_id_b in b.complete.dependent_typeids:
            if type_id_a == type_id_b:
                break
        else:
            return False, f"Complete Type ID {type_id_a} was unmatched"

    return True, "equal"


def type_map_equivalence(a: TypeMapping, b: TypeMapping) -> Tuple[bool, str]:
    for pair_a in a.identifier_object_pair_minimal:
        for pair_b in b.identifier_object_pair_minimal:
            if pair_a.type_identifier == pair_b.type_identifier:
                if pair_a.type_object != pair_b.type_object:
                    return False, f"Differing Type Objects for Minimal Type ID {pair_a.type_identifier}"
                break
        else:
            return False, f"Minimal Type ID {pair_a.type_identifier} was unmatched"

    for pair_a in a.identifier_object_pair_complete:
        for pair_b in b.identifier_object_pair_complete:
            if pair_a.type_identifier == pair_b.type_identifier:
                if pair_a.type_object != pair_b.type_object:
                    return False, f"Differing Type Objects for Complete Type ID {pair_a.type_identifier}"
                break
        else:
            return False, f"Complete Type ID {pair_a.type_identifier} was unmatched"

    for pair_a in a.identifier_complete_minimal:
        for pair_b in b.identifier_complete_minimal:
            if pair_a.type_identifier1 == pair_b.type_identifier1:
                if pair_a.type_identifier2 != pair_b.type_identifier2:
                    return False, f"Type ID Complete/Minimal Pair {pair_a.type_identifier1}/{pair_a.type_identifier2} was inconsistent with {pair_b.type_identifier1}/{pair_b.type_identifier2}"
                break
        else:
            return False, f"Type ID Complete/Minimal Pair {pair_a.type_identifier1}/{pair_a.type_identifier2} was unmatched"

    return True, "equal"
