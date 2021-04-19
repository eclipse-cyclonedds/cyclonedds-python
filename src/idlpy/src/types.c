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
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

#include "idl/stream.h"
#include "idl/string.h"
#include "idl/processor.h"

#include "context.h"
#include "naming.h"


static idl_retcode_t
emit_module(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx) user_data;
    idl_retcode_t ret = IDL_RETCODE_NO_MEMORY;

    if (!revisit)
    {
        idlpy_enter_module(ctx, node);
        ret = IDL_VISIT_REVISIT;
    }
    else
    {
        idlpy_exit_module(ctx);
        ret = IDL_RETCODE_OK;
    }

    (void)pstate;
    (void)path;

    return ret;
}


/* members with multiple declarators result in multiple members */
static idl_retcode_t
emit_field(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx) user_data;

    const char *name = idl_identifier(node);
    char *type = typename(ctx, idl_type_spec(node));

    idlpy_printf(ctx, "\n    %s: %s", name, type);

    free(type);
    (void)pstate;
    (void)revisit;
    (void)path;
    
    return IDL_RETCODE_OK;
}


char *cdr_struct_decoration(const void *node)
{
    idl_struct_t *_struct = (idl_struct_t*) node;
    const char *extensibility, *autoid;

    switch(_struct->extensibility) {
        case IDL_EXTENSIBILITY_FINAL:
            extensibility = "final=True";
            break;
        case IDL_EXTENSIBILITY_APPENDABLE:
            extensibility = "appendable=True";
            break;
        case IDL_EXTENSIBILITY_MUTABLE:
            extensibility = "mutable=True";
            break;
    }

    switch(_struct->autoid) {
        case IDL_AUTOID_SEQUENTIAL:
            autoid = "";
            break;
        case IDL_AUTOID_HASH:
            autoid = ", autoid_hash=True, ";
            break;
    }

    /// TODO: BUILD KEYLIST

    char* ret;
    idl_asprintf(&ret, "(%s%s)", extensibility, autoid);
    return ret;
}

static idl_retcode_t
emit_struct(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx) user_data;
    idl_retcode_t ret = IDL_RETCODE_NO_MEMORY;

    char *name = define_local(ctx, node);
    char *decorator = cdr_struct_decoration(node);

    if (!revisit)
    {
        idlpy_ensure_toplevel_import(ctx, "cdr");
        idlpy_printf(ctx, "@cdr%s\nclass %s:", decorator, name);
        ret = IDL_VISIT_REVISIT;
    }
    else
    {
        idlpy_write(ctx, "\n\n\n");
        ret = IDL_RETCODE_OK;
    }

    free(name);
    free(decorator);
    (void*) pstate;
    (void*) path;

    return ret;
}

static idl_retcode_t
emit_union(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx) user_data;
    idl_retcode_t ret = IDL_RETCODE_NO_MEMORY;

    char *name = define_local(ctx, node);
    char *discriminator = typename(ctx, ((idl_union_t*)node)->switch_type_spec->type_spec);

    if (!revisit)
    {
        idlpy_ensure_toplevel_import(ctx, "union");
        idlpy_printf(ctx, "@union(%s)\nclass %s:", discriminator, name);
        ret = IDL_VISIT_REVISIT;
    }
    else
    {
        idlpy_write(ctx, "\n\n\n");
        ret = IDL_RETCODE_OK;
    }

    free(name);
    free(discriminator);
    (void)pstate;
    (void)path;

    return ret;
}

static idl_retcode_t
emit_typedef(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx) user_data;

    char *name = define_local(ctx, node);
    char *type = typename(ctx, idl_type_spec(node));

    idlpy_ensure_basetype_import(ctx, "typedef");
    idlpy_printf(ctx, "%s: typedef = %s", name, type);

    free(type);
    free(name);

    return IDL_VISIT_DONT_RECURSE;
}

static idl_retcode_t
emit_enum(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx) user_data;
    idl_retcode_t ret = IDL_RETCODE_NO_MEMORY;
    uint32_t skip = 0, value = 0;

    char *name = define_local(ctx, node);

    idlpy_ensure_basetype_import(ctx, "enum");
    idlpy_ensure_basetype_import(ctx, "auto");
    idlpy_printf(ctx, "class %s(enum):", name);

    idl_enumerator_t *enumerator = ((const idl_enum_t *)node)->enumerators;
    for (; enumerator; enumerator = idl_next(enumerator))
    {
        const char* fmt;

        if (name)
            free(name);
        name = typename(ctx, enumerator);
        value = enumerator->value;

        /* IDL 3.5 did not support fixed enumerator values */
        if (value == skip) // || (pstate->version == IDL35))
            fmt = "    %s = auto()\n";
        else
            fmt = "    %s = %" PRIu32;

        idlpy_printf(ctx, fmt, name, value);
        skip = value + 1;
    }

    idlpy_write(ctx, "\n\n\n");

    ret = IDL_VISIT_DONT_RECURSE;
bail:
    if (name)
        free(name);

    (void)pstate;
    (void)revisit;
    (void)path;

    return ret;
}

static void
print_literal(
    const idl_pstate_t *pstate,
    idlpy_ctx ctx,
    const idl_literal_t *literal)
{
    idl_type_t type;

    switch ((type = idl_type(literal)))
    {
    case IDL_CHAR:
        idlpy_printf(ctx, "'%c'", literal->value.chr);
        break;
    case IDL_BOOL:
        idlpy_printf(ctx, "%s", literal->value.bln ? "True" : "False");
        break;
    case IDL_INT8:
        idlpy_printf(ctx, "%" PRId8, literal->value.int8);
        break;
    case IDL_OCTET:
    case IDL_UINT8:
        idlpy_printf(ctx, "%" PRIu8, literal->value.uint8);
        break;
    case IDL_SHORT:
    case IDL_INT16:
        idlpy_printf(ctx, "%" PRId16, literal->value.int16);
        break;
    case IDL_USHORT:
    case IDL_UINT16:
        idlpy_printf(ctx, "%" PRIu16, literal->value.uint16);
        break;
    case IDL_LONG:
    case IDL_INT32:
        idlpy_printf(ctx, "%" PRId32, literal->value.int32);
        break;
    case IDL_ULONG:
    case IDL_UINT32:
        idlpy_printf(ctx, "%" PRIu32, literal->value.uint32);
        break;
    case IDL_LLONG:
    case IDL_INT64:
        idlpy_printf(ctx, "%" PRId64, literal->value.int64);
        break;
    case IDL_ULLONG:
    case IDL_UINT64:
        idlpy_printf(ctx, "%" PRIu64, literal->value.uint64);
        break;
    case IDL_FLOAT:
        idlpy_printf(ctx, "%.6f", literal->value.flt);
        break;
    case IDL_DOUBLE:
        idlpy_printf(ctx, "%f", literal->value.dbl);
        break;
    case IDL_LDOUBLE:
        idlpy_printf(ctx, "%lf", literal->value.ldbl);
        break;
    case IDL_STRING:
        idlpy_printf(ctx, "\"%s\"", literal->value.str);
        break;
    default:
    {
        char *name;
        assert(type == IDL_ENUM);
        name = typename(ctx, literal);
        idlpy_printf(ctx, "%s", name);
        free(name);
    }
    }
    (void)pstate;
}

static idl_retcode_t
emit_const(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx) user_data;

    char *type = typename(ctx, node);
    const idl_literal_t *literal = ((const idl_const_t *) node)->const_expr;

    idlpy_printf(ctx, "%s = ", type);
    print_literal(pstate, ctx, literal);
    idlpy_write(ctx, "\n\n");

    free(type);
    (void)revisit;
    (void)path;

    return IDL_RETCODE_OK;
}


idl_retcode_t generate_types(const idl_pstate_t *pstate, idlpy_ctx ctx)
{
    idl_retcode_t ret;
    idl_visitor_t visitor;

    memset(&visitor, 0, sizeof(visitor));
    visitor.visit = IDL_CONST | IDL_TYPEDEF | IDL_STRUCT | IDL_UNION | IDL_ENUM | IDL_DECLARATOR | IDL_MODULE;
    visitor.accept[IDL_ACCEPT_MODULE] = &emit_module;
    visitor.accept[IDL_ACCEPT_CONST] = &emit_const;
    visitor.accept[IDL_ACCEPT_TYPEDEF] = &emit_typedef;
    visitor.accept[IDL_ACCEPT_STRUCT] = &emit_struct;
    visitor.accept[IDL_ACCEPT_UNION] = &emit_union;
    visitor.accept[IDL_ACCEPT_ENUM] = &emit_enum;
    visitor.accept[IDL_ACCEPT_DECLARATOR] = &emit_field;
    visitor.sources = (const char *[]){pstate->sources->path->name, NULL};
    if ((ret = idl_visit(pstate, pstate->root, &visitor, ctx)))
        return ret;
    return IDL_RETCODE_OK;
}
