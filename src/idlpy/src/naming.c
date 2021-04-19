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
#include <assert.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <inttypes.h>

#include "naming.h"

#include "idl/file.h"
#include "idl/retcode.h"
#include "idl/stream.h"
#include "idl/string.h"
#include "idl/version.h"
#include "idl/processor.h"



void size_descriptor(idlpy_ctx ctx, char **type, const void *node)
{
    const char* fmt;

    if (idl_is_array(node)) {
        idlpy_ensure_basetype_import(ctx, "array");
        fmt = "array[%s, %" PRIu32 "]";
    }
    else if (idl_is_sequence(node)) {
        idlpy_ensure_basetype_import(ctx, "sequence");
        fmt = "sequence[%s, %" PRIu32 "]";
    }
    else if (idl_is_string(node)) {
        idlpy_ensure_basetype_import(ctx, *type);
        fmt = "%s[%" PRIu32 "]";
    }
    else
        return;

    char **nbuf;

    const idl_literal_t *literal;
    literal = ((const idl_declarator_t *)node)->const_expr;

    for (; literal; literal = idl_next(literal))
    {
        idl_asprintf(nbuf, fmt, *type, literal->value.uint32);
        free(*type);
        *type = *nbuf;
        *nbuf = NULL;
    }
    return;
}


char *typename_of_type(idlpy_ctx ctx, idl_type_t type)
{
    switch (type)
    {
    case IDL_BOOL:
        return idl_strdup("bool");
    case IDL_CHAR:
        idlpy_ensure_basetype_import(ctx, "char");
        return idl_strdup("char");
    case IDL_INT8:
        idlpy_ensure_basetype_import(ctx, "int8");
        return idl_strdup("int8");
    case IDL_OCTET:
    case IDL_UINT8:
        idlpy_ensure_basetype_import(ctx, "uint8");
        return idl_strdup("uint8");
    case IDL_SHORT:
    case IDL_INT16:
        idlpy_ensure_basetype_import(ctx, "int16");
        return idl_strdup("int16");
    case IDL_USHORT:
    case IDL_UINT16:
        idlpy_ensure_basetype_import(ctx, "uin16");
        return idl_strdup("uint16");
    case IDL_LONG:
    case IDL_INT32:
        idlpy_ensure_basetype_import(ctx, "int32");
        return idl_strdup("int32");
    case IDL_ULONG:
    case IDL_UINT32:
        idlpy_ensure_basetype_import(ctx, "uint32");
        return idl_strdup("uint32");
    case IDL_LLONG:
    case IDL_INT64:
        idlpy_ensure_basetype_import(ctx, "int64");
        return idl_strdup("int64");
    case IDL_ULLONG:
    case IDL_UINT64:
        idlpy_ensure_basetype_import(ctx, "uint64");
        return idl_strdup("uint64");
    case IDL_FLOAT:
        idlpy_ensure_basetype_import(ctx, "float32");
        return idl_strdup("float32");
    case IDL_DOUBLE:
        idlpy_ensure_basetype_import(ctx, "float64");
        return idl_strdup("float64");
    case IDL_LDOUBLE:
        idlpy_report_error(ctx, "The type 'long double'/'float128' is not supported in Python.");
        return idl_strdup("ERROR");
    case IDL_STRING:
        return idl_strdup("str");
    case IDL_SEQUENCE:
        abort(); // Sequences should be handled outside.
    default:
        break;
    }

    return NULL;
}

char* typename(idlpy_ctx ctx, const void *node)
{
    if (idl_is_sequence(node) || idl_is_array(node)) {
        char* inner = typename(ctx, idl_type_spec(node));
        size_descriptor(ctx, &inner, node);
        return inner;
    }
    else if (idl_is_string(node) && idl_is_bounded(node)) {
        char* inner = idl_strdup("bound_str");
        size_descriptor(ctx, &inner, node);
        return inner;
    }
    else {
        idl_type_t type = idl_type(node);
        char* typename = typename_of_type(ctx, type);
        if (typename == NULL) return idlpy_imported_name(ctx, node);
        return typename;
    }
}

char* define_local(idlpy_ctx ctx, const void *node)
{
    char* name = idl_strdup(idl_identifier(node));
    idlpy_define_local(ctx, name);
    return name;
}
