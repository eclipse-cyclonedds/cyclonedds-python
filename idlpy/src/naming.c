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


static void size_descriptor(char **type, const void *node)
{
    const char* fmt;

    if (idl_is_array(node)) {
        fmt = "pt.array[%s, %" PRIu32 "]";
    }
    else if (idl_is_sequence(node)) {
        fmt = "pt.sequence[%s, %" PRIu32 "]";
    }
    else if (idl_is_string(node)) {
        fmt = "pt.%s[%" PRIu32 "]";
    }
    else
        return;

    char **nbuf = NULL;

    const idl_literal_t *literal;
    literal = ((const idl_declarator_t *)node)->const_expr;

    for (; literal; literal = idl_next(literal))
    {
        if (idl_asprintf(nbuf, fmt, *type, literal->value.uint32) != 0) 
            return;
        free(*type);
        *type = *nbuf;
        *nbuf = NULL;
    }
    return;
}


static char *typename_of_type(idlpy_ctx ctx, idl_type_t type)
{
    switch (type)
    {
    case IDL_BOOL:
        return idl_strdup("pt.bool");
    case IDL_CHAR:
        return idl_strdup("pt.char");
    case IDL_INT8:
        return idl_strdup("pt.int8");
    case IDL_OCTET:
    case IDL_UINT8:
        return idl_strdup("pt.uint8");
    case IDL_SHORT:
    case IDL_INT16:
        return idl_strdup("pt.int16");
    case IDL_USHORT:
    case IDL_UINT16:
        return idl_strdup("pt.uint16");
    case IDL_LONG:
    case IDL_INT32:
        return idl_strdup("pt.int32");
    case IDL_ULONG:
    case IDL_UINT32:
        return idl_strdup("pt.uint32");
    case IDL_LLONG:
    case IDL_INT64:
        return idl_strdup("pt.int64");
    case IDL_ULLONG:
    case IDL_UINT64:
        return idl_strdup("pt.uint64");
    case IDL_FLOAT:
        return idl_strdup("pt.float32");
    case IDL_DOUBLE:
        return idl_strdup("pt.float64");
    case IDL_LDOUBLE:
        idlpy_ctx_report_error(ctx, "The type 'long double'/'float128' is not supported in Python.");
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
        size_descriptor(&inner, node);
        return inner;
    }
    else if (idl_is_string(node) && idl_is_bounded(node)) {
        char* inner = idl_strdup("bounded_str");
        size_descriptor(&inner, node);
        return inner;
    }
    else {
        idl_type_t type = idl_type(node);
        char* typename = typename_of_type(ctx, type);
        if (typename == NULL) return absolute_name(node);
        return typename;
    }
}


char *absolute_name(const void *node)
{
    char *str;
    size_t cnt, len = 0;
    const char *sep, *ident;
    const idl_node_t *root;
    const char* separator = ".";

    for (root = node, sep = ""; root; root = root->parent)
    {
        if ((idl_mask(root) & IDL_TYPEDEF) == IDL_TYPEDEF)
            continue;
        if ((idl_mask(root) & IDL_ENUM) == IDL_ENUM && root != node)
            continue;
        ident = idl_identifier(root);
        assert(ident);
        len += strlen(sep) + strlen(ident);
        sep = separator;
    }

    if (!(str = malloc(len + 1)))
        return NULL;

    str[len] = '\0';
    for (root = node, sep = separator; root; root = root->parent)
    {
        if ((idl_mask(root) & IDL_TYPEDEF) == IDL_TYPEDEF)
            continue;
        if ((idl_mask(root) & IDL_ENUM) == IDL_ENUM && root != node)
            continue;

        ident = idl_identifier(root);
        assert(ident);
        cnt = strlen(ident);
        assert(cnt <= len);
        len -= cnt;
        memmove(str + len, ident, cnt);
        if (len == 0)
            break;
        cnt = strlen(sep);
        assert(cnt <= len);
        len -= cnt;
        memmove(str + len, sep, cnt);
    }
    assert(len == 0);
    return str;
}
