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

//Reserved Python keywords support (Issue 105)
static const char *python_keywords[] = {
#define _py_(str) "_" str
    _py_("False"), _py_("None"), _py_("True"), _py_("and"), _py_("as"), _py_("assert"), 
    _py_("break"), _py_("class"), _py_("continue"), _py_("def"), _py_("del"), _py_("elif"), 
    _py_("else"), _py_("except"), _py_("finally"), _py_("for"), _py_("from"), _py_("global"), 
    _py_("if"), _py_("import"), _py_("in"), _py_("is"), _py_("lambda"), _py_("nonlocal"), 
    _py_("not"), _py_("or"), _py_("pass"), _py_("raise"), _py_("return"), _py_("try"), 
    _py_("while"), _py_("with"), _py_("yield"), _py_("idl"), _py_("annotate"), _py_("types"), 
    _py_("auto"), _py_("TYPE_CHECKING"), _py_("Optional")
#undef _py_
};



const char *filter_python_keywords(const char *name)
{
    static const size_t n = sizeof(python_keywords) / sizeof(python_keywords[0]);

    /* search through the Python keyword list */
    for (size_t i = 0; i < n; i++)
    {
        if (strcmp(python_keywords[i] + 1, name) == 0)
            return python_keywords[i];
    }

    return name;
}

const char *idlpy_identifier(const void *node)
{
    const char *name = idl_identifier(node);
    name = filter_python_keywords(name);
    return  name;
}
///////////////////////////////////////////////////



static char *typename_of_type(idlpy_ctx ctx, idl_type_t type)
{
    switch (type)
    {
    case IDL_BOOL:
        return idl_strdup("bool");
    case IDL_CHAR:
        return idl_strdup("types.char");
    case IDL_WCHAR:
        idlpy_ctx_report_error(ctx, "The type 'wchar' is not supported in Python.");
        return idl_strdup("ERROR");
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
    if (idl_is_declarator(node) && idl_is_typedef(idl_parent(node))) {
        return absolute_name(ctx, node);
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
        if (typename == NULL) return absolute_name(ctx, node);
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
        if (typename == NULL) return absolute_name(ctx, node);
        return typename;
    }
}

char *absolute_name(idlpy_ctx ctx, const void *node)
{
    char *str;
    size_t cnt, len = 0, parnamelen = 0, pyrootlen;
    const char *sep, *ident, *pyroot;
    const idl_node_t *root;
    const char* separator = ".";

    pyroot = idlpy_ctx_get_pyroot(ctx);
    pyrootlen = strlen(pyroot);

    for (root = node, sep = ""; root; root = root->parent)
    {
        if ((idl_mask(root) & IDL_TYPEDEF) == IDL_TYPEDEF)
            continue;
        if ((idl_mask(root) & IDL_ENUM) == IDL_ENUM && root != node)
            continue;
        
        //Reserved Python keywords support (Issue 105)
        ident = idlpy_identifier(root);
        /////////////////////
        assert(ident);

        len += strlen(sep) + strlen(ident);
        if (root != ((idl_node_t*) node))
            parnamelen += strlen(sep) + strlen(ident);
        
        sep = separator;
    }

    if (!(str = malloc(len + pyrootlen + 3)))
        return NULL;

    str[0] = '\'';
    str[len+pyrootlen+1] = '\'';
    str[len+pyrootlen+2] = '\0';
    memcpy(str + 1, pyroot, pyrootlen);

    for (root = node, sep = separator; root; root = root->parent)
    {
        if ((idl_mask(root) & IDL_TYPEDEF) == IDL_TYPEDEF)
            continue;
        if ((idl_mask(root) & IDL_ENUM) == IDL_ENUM && root != node)
            continue;

        //Reserved Python keywords support (Issue 105)
        ident = idlpy_identifier(root);
        /////////////////////
        assert(ident);

        cnt = strlen(ident);
        assert(cnt <= len);
        len -= cnt;
        memmove(str + pyrootlen + len + 1, ident, cnt);

        if (len == 0)
            break;

        cnt = strlen(sep);
        assert(cnt <= len);
        len -= cnt;
        memmove(str + pyrootlen + len + 1, sep, cnt);
    }
    assert(len == 0);

    str[pyrootlen + parnamelen] = '\0';
    idlpy_ctx_reference_module(ctx, str + pyrootlen + 1);
    str[pyrootlen + parnamelen] = *separator;

    return str;
}


char *idl_full_typename(const void *node)
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

        //Reserved Python keywords support (Issue 105)
        ident = idlpy_identifier(root);
        /////////////////////
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

        //Reserved Python keywords support (Issue 105)
        ident = idlpy_identifier(root);
        ////////////////////////////////
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
