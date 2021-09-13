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


static char* wrap_size_descriptor(char **type, const void *node)
{
    char* out;

    if (idl_is_array(node)) {
        idl_asprintf(&out, "types.array[%s, %" PRIu32 "]", *type, idl_array_size(node));
    }
    else if (idl_is_sequence(node) && idl_is_bounded(node)) {
        idl_asprintf(&out, "types.sequence[%s, %" PRIu32 "]", *type, idl_bound(node));
    }
    else if (idl_is_sequence(node)) {
        idl_asprintf(&out, "types.sequence[%s]", *type);
    }
    else
        return NULL;

    return out;
}


static char *typename_of_type(idlpy_ctx ctx, idl_type_t type)
{
    switch (type)
    {
    case IDL_BOOL:
        return idl_strdup("bool");
    case IDL_CHAR:
        return idl_strdup("types.char");
    case IDL_INT8:
        return idl_strdup("types.int8");
    case IDL_OCTET:
    case IDL_UINT8:
        return idl_strdup("types.uint8");
    case IDL_SHORT:
    case IDL_INT16:
        return idl_strdup("types.int16");
    case IDL_USHORT:
    case IDL_UINT16:
        return idl_strdup("types.uint16");
    case IDL_LONG:
    case IDL_INT32:
        return idl_strdup("types.int32");
    case IDL_ULONG:
    case IDL_UINT32:
        return idl_strdup("types.uint32");
    case IDL_LLONG:
    case IDL_INT64:
        return idl_strdup("types.int64");
    case IDL_ULLONG:
    case IDL_UINT64:
        return idl_strdup("types.uint64");
    case IDL_FLOAT:
        return idl_strdup("types.float32");
    case IDL_DOUBLE:
        return idl_strdup("types.float64");
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
    if (idl_is_typedef(node)) {
        return absolute_name(node);
    }

    if (idl_is_templ_type(node)) {
        switch(idl_type(node)) {
            case IDL_SEQUENCE:
            {
                const idl_sequence_t *sequence = node;
                char *inner = typename(ctx, sequence->type_spec);
                char *res;

                if (sequence->maximum) {
                    const char *fmt = "types.sequence[%s, %"PRIu32"]";
                    idl_asprintf(&res, fmt, inner, sequence->maximum);
                }
                else {
                    const char *fmt = "types.sequence[%s]";
                    idl_asprintf(&res, fmt, inner);
                }

                free(inner);
                return res;
            }
            break;
            case IDL_STRING:
            {
                const idl_string_t *string = node;
                char *res;

                if (string->maximum) {
                    const char *fmt = "types.bounded_str[%"PRIu32"]";
                    idl_asprintf(&res, fmt, string->maximum);
                }
                else {
                    res = idl_strdup("str");
                }

                return res;
            }
            break;
            default:
                // next if statement
            break;
        }
    }
    if (idl_is_array(node)) {
        const idl_type_spec_t *type_spec = idl_type_spec(node);
        const idl_const_expr_t *const_expr;
        char * inner;

        inner = typename(ctx, type_spec);
        const_expr = ((const idl_declarator_t *)node)->const_expr;

        /* iterate backwards through the list so that the last entries in the list
            are the innermost arrays */
        for (const idl_const_expr_t *ce = const_expr; ce; ce = idl_next(ce))
            const_expr = ce;

        for (const idl_const_expr_t *ce = const_expr; ce; ce = idl_previous(ce)) {
            uint32_t dim = ((const idl_literal_t *)ce)->value.uint32;
            char *res;
            idl_asprintf(&res, "types.array[%s, %"PRIu32"]", inner, dim);
            free(inner);
            inner = res;
        }

        return inner;
    }
    else {
        idl_type_t type = idl_type(node);
        char* typename = typename_of_type(ctx, type);
        if (typename == NULL) return absolute_name(node);
        return typename;
    }
}


char* typename_unwrap_typedef(idlpy_ctx ctx, const void *node)
{
    if (idl_is_array(node)) {
        const idl_type_spec_t *type_spec = idl_type_spec(node);
        const idl_const_expr_t *const_expr;
        char * inner;

        inner = typename_unwrap_typedef(ctx, type_spec);
        const_expr = ((const idl_declarator_t *)node)->const_expr;

        /* iterate backwards through the list so that the last entries in the list
            are the innermost arrays */
        for (const idl_const_expr_t *ce = const_expr; ce; ce = idl_next(ce))
            const_expr = ce;

        for (const idl_const_expr_t *ce = const_expr; ce; ce = idl_previous(ce)) {
            uint32_t dim = ((const idl_literal_t *)ce)->value.uint32;
            char *res;
            idl_asprintf(&res, "types.array[%s, %"PRIu32"]", inner, dim);
            free(inner);
            inner = res;
        }

        return inner;
    }
    if (idl_is_typedef(node)) {
        return typename_unwrap_typedef(ctx, idl_type_spec(node));
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

    if (!(str = malloc(len + 3)))
        return NULL;

    str[0] = '"';
    str[len+1] = '"';
    str[len+2] = '\0';
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
        memmove(str + len + 1, ident, cnt);
        if (len == 0)
            break;
        cnt = strlen(sep);
        assert(cnt <= len);
        len -= cnt;
        memmove(str + len + 1, sep, cnt);
    }
    assert(len == 0);
    return str;
}
