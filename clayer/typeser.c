/*
 * Copyright(c) 2021 to 2022 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
 */

#include "typeser.h"
#include "dds/ddsc/dds_public_alloc.h"
#include "dds/ddsi/ddsi_typelib.h"


void ddspy_typeid_ser (dds_ostream_t * os, dds_typeid_t * type_id)
{
#ifdef DDS_HAS_TYPE_DISCOVERY
    dds_stream_write(os, (char*) type_id, DDS_XTypes_TypeIdentifier_desc.m_ops);
#endif
}

void ddspy_typeid_deser (dds_istream_t * is, dds_typeid_t ** type_id)
{
#ifdef DDS_HAS_TYPE_DISCOVERY
    *type_id = dds_alloc(sizeof (DDS_XTypes_TypeIdentifier));
    dds_stream_read (is, (void *) *type_id, DDS_XTypes_TypeIdentifier_desc.m_ops);
#endif
}

void ddspy_typeobj_ser (dds_ostream_t * os, dds_typeobj_t * type_obj)
{
#ifdef DDS_HAS_TYPE_DISCOVERY
    dds_stream_write(os, (char*) type_obj, DDS_XTypes_TypeObject_desc.m_ops);
#endif
}

void ddspy_typeobj_deser (dds_istream_t * is, dds_typeobj_t ** type_obj)
{
#ifdef DDS_HAS_TYPE_DISCOVERY
    *type_obj = dds_alloc(sizeof (DDS_XTypes_TypeObject));
    dds_stream_read (is, (void *) *type_obj, DDS_XTypes_TypeObject_desc.m_ops);
#endif
}
