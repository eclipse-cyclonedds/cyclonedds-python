/*
 * Copyright(c) 2021 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
 *
 * IDLPY Sorted Set Of Strings
 */

#ifndef IDLPY_SSOS_H
#define IDLPY_SSOS_H


typedef struct idlpy_ssos_s *idlpy_ssos;
typedef enum idlpy_ssos_retcode {
    IDLPY_SSOS_RETCODE_OK,
    IDLPY_SSOS_RETCODE_FAIL,
    IDLPY_SSOS_RETCODE_NOMEMORY
} idlpy_ssos_retcode_t;


idlpy_ssos                  idlpy_ssos_new(void);
void                        idlpy_ssos_free(idlpy_ssos list);
idlpy_ssos_retcode_t        idlpy_ssos_add(idlpy_ssos list, const char *value);
void                        idlpy_ssos_remove(idlpy_ssos list, const char *value);
int                         idlpy_ssos_search(const idlpy_ssos list, const char *value);
const char*                 idlpy_ssos_at(const idlpy_ssos list, int index);
int                         idlpy_ssos_size(const idlpy_ssos list);

#endif // IDLPY_SSOS_H