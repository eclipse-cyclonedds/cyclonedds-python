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

#ifndef TYPESER_H
#define TYPESER_H

#include "dds/dds.h"
#include "dds/cdr/dds_cdrstream.h"

void ddspy_typeid_ser (dds_ostream_t*, dds_typeid_t *);
void ddspy_typeid_deser (dds_istream_t*, dds_typeid_t **);
void ddspy_typeobj_ser (dds_ostream_t*, dds_typeobj_t *);
void ddspy_typeobj_deser (dds_istream_t*, dds_typeobj_t **);

#endif // TYPESER_H
