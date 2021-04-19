/*
 * Copyright(c) 2021 ADLINK Technology Limited and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
 */
#ifndef IDLPY_CONTEXT_H
#define IDLPY_CONTEXT_H

#include <stdarg.h>

typedef struct idlpy_ctx_s *idlpy_ctx;

idlpy_ctx idlpy_new_ctx(const char* path);
void idlpy_free_ctx(idlpy_ctx ctx);

void idlpy_enter_module(idlpy_ctx ctx, const void *module);
void idlpy_exit_module(idlpy_ctx ctx);

void idlpy_ensure_basetype_import(idlpy_ctx ctx, const char* type);
void idlpy_ensure_toplevel_import(idlpy_ctx ctx, const char* type);
void idlpy_define_local(idlpy_ctx ctx, const char* type);
char* idlpy_imported_name(idlpy_ctx ctx, const void* node);
void idlpy_close_ctx(idlpy_ctx ctx);
void idlpy_consume(idlpy_ctx ctx, char* data);
void idlpy_write(idlpy_ctx ctx, const char* data);
void idlpy_printf(idlpy_ctx ctx, const char *fmt, ...);

void idlpy_report_error(idlpy_ctx ctx, const char* error);

#endif // IDLPY_CONTEXT_H