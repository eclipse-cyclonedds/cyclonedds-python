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
 */
#ifndef IDLPY_context_H
#define IDLPY_context_H

#include <stdarg.h>
#include <stdbool.h>
#include "idl/retcode.h"

typedef struct idlpy_ctx_s *idlpy_ctx;

idlpy_ctx     idlpy_ctx_new(const char* path, const char* idl_file, const char* pyroot);
void          idlpy_ctx_free(idlpy_ctx ctx);
idl_retcode_t idlpy_ctx_write_all(idlpy_ctx ctx);

idl_retcode_t idlpy_ctx_enter_module(idlpy_ctx ctx, const char *name);
idl_retcode_t idlpy_ctx_exit_module(idlpy_ctx ctx);

idl_retcode_t idlpy_ctx_enter_entity(idlpy_ctx ctx, const char *name);
idl_retcode_t idlpy_ctx_exit_entity(idlpy_ctx ctx);
idl_retcode_t idlpy_ctx_reference_module(idlpy_ctx octx, const char* name);

void          idlpy_ctx_consume(idlpy_ctx ctx, char* data);
void          idlpy_ctx_write(idlpy_ctx ctx, const char* data);
void          idlpy_ctx_printf(idlpy_ctx ctx, const char *fmt, ...);

void          idlpy_ctx_report_error(idlpy_ctx ctx, const char* error);
const char*   idlpy_ctx_get_pyroot(idlpy_ctx ctx);

void          idlpy_ctx_emit_field(idlpy_ctx octx);
bool          idlpy_ctx_did_emit_field(idlpy_ctx octx);

#endif // IDLPY_context_H