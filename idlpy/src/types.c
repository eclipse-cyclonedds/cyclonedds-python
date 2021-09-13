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
#include "types.h"



static char *
format_literal(
    idlpy_ctx ctx,
    const idl_literal_t *literal)
{
    char *ret;
    idl_type_t type;

    switch ((type = idl_type(literal)))
    {
    case IDL_CHAR:
        idl_asprintf(&ret, "'%c'", literal->value.chr);
        break;
    case IDL_BOOL:
        idl_asprintf(&ret, "%s", literal->value.bln ? "True" : "False");
        break;
    case IDL_INT8:
        idl_asprintf(&ret, "%" PRId8, literal->value.int8);
        break;
    case IDL_OCTET:
    case IDL_UINT8:
        idl_asprintf(&ret, "%" PRIu8, literal->value.uint8);
        break;
    case IDL_SHORT:
    case IDL_INT16:
        idl_asprintf(&ret, "%" PRId16, literal->value.int16);
        break;
    case IDL_USHORT:
    case IDL_UINT16:
        idl_asprintf(&ret, "%" PRIu16, literal->value.uint16);
        break;
    case IDL_LONG:
    case IDL_INT32:
        idl_asprintf(&ret, "%" PRId32, literal->value.int32);
        break;
    case IDL_ULONG:
    case IDL_UINT32:
        idl_asprintf(&ret, "%" PRIu32, literal->value.uint32);
        break;
    case IDL_LLONG:
    case IDL_INT64:
        idl_asprintf(&ret, "%" PRId64, literal->value.int64);
        break;
    case IDL_ULLONG:
    case IDL_UINT64:
        idl_asprintf(&ret, "%" PRIu64, literal->value.uint64);
        break;
    case IDL_FLOAT:
        idl_asprintf(&ret, "%.6f", literal->value.flt);
        break;
    case IDL_DOUBLE:
        idl_asprintf(&ret, "%f", literal->value.dbl);
        break;
    case IDL_LDOUBLE:
        idl_asprintf(&ret, "%Lf", literal->value.ldbl);
        break;
    case IDL_STRING:
        idl_asprintf(&ret, "\"%s\"", literal->value.str);
        break;
    default:
    {
        char *name;
        assert(type == IDL_ENUM);
        name = typename(ctx, literal);
        idl_asprintf(&ret, "%s", name);
        free(name);
    }
    }
    return ret;
}

static idl_retcode_t
emit_module(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx)user_data;
    idl_retcode_t ret = IDL_RETCODE_NO_MEMORY;

    if (!revisit)
    {
        ret = idlpy_ctx_enter_module(ctx, idl_identifier(node));
    }
    else
    {
        ret = idlpy_ctx_exit_module(ctx);
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
    idlpy_ctx ctx = (idlpy_ctx)user_data;
    const void *parent = idl_parent(node);

    const char *name = idl_identifier(node);
    const void* type_spec;

    if (idl_is_array(node) || idl_is_typedef(node))
        type_spec = node;
    else
        type_spec = idl_type_spec(node);

    char *type = typename(ctx, type_spec);

    if (idl_is_default_case(parent)) {
        char *ctype;
        idl_asprintf(&ctype, "types.default[%s]", type);
        free(type);
        type = ctype;
    }
    else if (idl_is_case(parent)) {
        const idl_case_t *mycase = (const idl_case_t*) parent;
        char *ctype, *labels = idl_strdup("");
        idl_literal_t* literal = (idl_literal_t*) mycase->labels->const_expr;
        const char *comma = "";

        for (; literal; literal = idl_next(literal)) {
            char *formatted = format_literal(ctx, literal);
            char *nlabels;
            idl_asprintf(&nlabels, "%s%s%s", labels, comma, formatted);
            free(labels);
            free(formatted);
            labels = nlabels;
            comma = ", ";
        }

        idl_asprintf(&ctype, "types.case[[%s], %s]", labels, type);
        free(type);
        free(labels);
        type = ctype;
    }

    idlpy_ctx_printf(ctx, "\n    %s: %s", name, type);

    if (!pstate->keylists && idl_is_member(parent) && ((const idl_member_t*)parent)->key.value) {
        idlpy_ctx_printf(ctx, "\n    annotate.key(%s)", name);
    }

    free(type);
    (void)pstate;
    (void)revisit;
    (void)path;

    return IDL_RETCODE_OK;
}

static void struct_decoration(idlpy_ctx ctx, const void *node)
{
    idl_struct_t *_struct = (idl_struct_t *)node;

    idlpy_ctx_printf(ctx, "@dataclass\n");

    if (_struct->keylist)
    {
        idlpy_ctx_printf(ctx, "@annotate.keylist([");

        idl_key_t *key = _struct->keylist->keys;

        if (key)
        {
            idlpy_ctx_printf(ctx, "\"%s\"", key->field_name->identifier);
            key++;
        }

        while (key)
        {
            idlpy_ctx_printf(ctx, ", \"%s\"", key->field_name->identifier);
            key++;
        }

        idlpy_ctx_printf(ctx, "])\n");
    }

    switch (_struct->extensibility.value)
    {
    case IDL_FINAL:
        idlpy_ctx_printf(ctx, "@annotate.final\n");
        break;
    case IDL_APPENDABLE:
        idlpy_ctx_printf(ctx, "@annotate.appendable\n");
        break;
    case IDL_MUTABLE:
        idlpy_ctx_printf(ctx, "@annotate.mutable\n");
        break;
    default:
        break;
    }

    switch (_struct->autoid.value)
    {
    case IDL_HASH:
        idlpy_ctx_printf(ctx, "@annotate.autoid(\"hash\")\n");
        break;
    case IDL_SEQUENTIAL:
        idlpy_ctx_printf(ctx, "@annotate.autoid(\"sequential\")\n");
        break;
    default:
        break;
    }

    if (_struct->nested.value)
    {
        idlpy_ctx_printf(ctx, "@annotate.nested\n");
    }
}

static idl_retcode_t
emit_struct(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx)user_data;
    idl_retcode_t ret = IDL_RETCODE_NO_MEMORY;

    if (!revisit)
    {
        idlpy_ctx_enter_entity(ctx, idl_identifier(node));
        struct_decoration(ctx, node);
        char *fullname = absolute_name(node);
        idlpy_ctx_printf(ctx, "class %s(idl.IdlStruct, typename=%s):", idl_identifier(node), fullname);
        free(fullname);
        ret = IDL_VISIT_REVISIT;
    }
    else
    {
        idlpy_ctx_exit_entity(ctx);
        ret = IDL_RETCODE_OK;
    }

    (void)pstate;
    (void)path;

    return ret;
}

static void union_decoration(idlpy_ctx ctx, const void *node)
{
    idl_union_t *_union = (idl_union_t *)node;

    switch (_union->extensibility.value)
    {
    case IDL_FINAL:
        idlpy_ctx_printf(ctx, "@annotate.final\n");
        break;
    case IDL_APPENDABLE:
        idlpy_ctx_printf(ctx, "@annotate.appendable\n");
        break;
    case IDL_MUTABLE:
        idlpy_ctx_printf(ctx, "@annotate.mutable\n");
        break;
    default:
        break;
    }

    if (_union->nested.value)
    {
        idlpy_ctx_printf(ctx, "@annotate.nested\n");
    }
}

static idl_retcode_t
emit_union(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx)user_data;
    idl_retcode_t ret = IDL_RETCODE_NO_MEMORY;

    if (!revisit)
    {
        char *discriminator = typename(ctx, ((idl_union_t *)node)->switch_type_spec->type_spec);
        if (discriminator == NULL)
            return ret;

        idlpy_ctx_enter_entity(ctx, idl_identifier(node));
        union_decoration(ctx, node);
        char* fullname = absolute_name(node);
        idlpy_ctx_printf(ctx,
            "class %s(idl.IdlUnion, discriminator=%s, discriminator_is_key=%s, typename=%s):",
            idl_identifier(node),
            discriminator,
            ((idl_union_t *)node)->switch_type_spec->key.value ? "True": "False",
            fullname
        );
        free(fullname);
        ret = IDL_VISIT_REVISIT;
        free(discriminator);
    }
    else
    {
        idlpy_ctx_exit_entity(ctx);
        ret = IDL_RETCODE_OK;
    }

    (void)pstate;
    (void)path;

    return ret;
}

static idl_retcode_t
expand_typedef(
    idlpy_ctx ctx,
    const idl_declarator_t *declarator)
{
    char *type = NULL;
    const char *name = idl_identifier(declarator);
    const idl_type_spec_t *type_spec;

    idlpy_ctx_enter_entity(ctx, name);

    if (idl_is_array(declarator))
        type_spec = declarator;
    else
        type_spec = idl_type_spec(declarator);

    type = typename(ctx, type_spec);
    idlpy_ctx_printf(ctx, "%s = %s;\n\n", name, type);
    idlpy_ctx_exit_entity(ctx);

    return IDL_RETCODE_OK;
}

static idl_retcode_t
emit_typedef(
    const idl_pstate_t *pstate,
    const bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx)user_data;
    const idl_typedef_t *_typedef = (const idl_typedef_t *)node;
    const idl_declarator_t *declarator;

    (void)pstate;
    (void)revisit;
    (void)path;

    idl_retcode_t ret = IDL_RETCODE_OK;
    IDL_FOREACH(declarator, _typedef->declarators)
    {
        if ((ret = expand_typedef(ctx, declarator)) != IDL_RETCODE_OK)
            break;
    }

    return ret;
}

/*
static idl_retcode_t
emit_typedef(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    if (!idl_is_typedef(node) || !revisit)
        return IDL_VISIT_REVISIT;

    idlpy_ctx ctx = (idlpy_ctx)user_data;
    const char *name = ((const idl_typedef_t *)node)->declarators->name->identifier;

    const idl_type_spec_t *type_spec = idl_type_spec(node);

    char *type = typename(ctx, type_spec);
    if (type == NULL)
        return IDL_RETCODE_NO_MEMORY;

    idlpy_ctx_enter_entity(ctx, name);
    idlpy_ctx_printf(ctx, "%s = %s", name, type);
    idlpy_ctx_exit_entity(ctx);

    free(type);

    (void)revisit;
    (void)path;
    (void)pstate;

    return IDL_VISIT_DONT_RECURSE;
}
*/

static idl_retcode_t
emit_enum(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx)user_data;
    idl_retcode_t ret = IDL_RETCODE_NO_MEMORY;
    uint32_t value = 0;

    idlpy_ctx_enter_entity(ctx, idl_identifier(node));
    idlpy_ctx_printf(ctx, "class %s(enum):", idl_identifier(node));

    idl_enumerator_t *enumerator = ((const idl_enum_t *)node)->enumerators;
    for (; enumerator; enumerator = idl_next(enumerator))
    {
        const char *fmt;

        char *name = typename(ctx, enumerator);
        value = enumerator->value.value;

        /* IDL 3.5 did not support fixed enumerator values */
        if (enumerator->value.annotation == NULL) // || (pstate->version == IDL35))
            fmt = "    %s = auto()\n";
        else
            fmt = "    %s = %" PRIu32;

        idlpy_ctx_printf(ctx, fmt, name, value);
        free(name);
    }

    idlpy_ctx_exit_entity(ctx);

    ret = IDL_VISIT_DONT_RECURSE;

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
        idlpy_ctx_printf(ctx, "'%c'", literal->value.chr);
        break;
    case IDL_BOOL:
        idlpy_ctx_printf(ctx, "%s", literal->value.bln ? "True" : "False");
        break;
    case IDL_INT8:
        idlpy_ctx_printf(ctx, "%" PRId8, literal->value.int8);
        break;
    case IDL_OCTET:
    case IDL_UINT8:
        idlpy_ctx_printf(ctx, "%" PRIu8, literal->value.uint8);
        break;
    case IDL_SHORT:
    case IDL_INT16:
        idlpy_ctx_printf(ctx, "%" PRId16, literal->value.int16);
        break;
    case IDL_USHORT:
    case IDL_UINT16:
        idlpy_ctx_printf(ctx, "%" PRIu16, literal->value.uint16);
        break;
    case IDL_LONG:
    case IDL_INT32:
        idlpy_ctx_printf(ctx, "%" PRId32, literal->value.int32);
        break;
    case IDL_ULONG:
    case IDL_UINT32:
        idlpy_ctx_printf(ctx, "%" PRIu32, literal->value.uint32);
        break;
    case IDL_LLONG:
    case IDL_INT64:
        idlpy_ctx_printf(ctx, "%" PRId64, literal->value.int64);
        break;
    case IDL_ULLONG:
    case IDL_UINT64:
        idlpy_ctx_printf(ctx, "%" PRIu64, literal->value.uint64);
        break;
    case IDL_FLOAT:
        idlpy_ctx_printf(ctx, "%.6f", literal->value.flt);
        break;
    case IDL_DOUBLE:
        idlpy_ctx_printf(ctx, "%f", literal->value.dbl);
        break;
    case IDL_LDOUBLE:
        idlpy_ctx_printf(ctx, "%lf", literal->value.ldbl);
        break;
    case IDL_STRING:
        idlpy_ctx_printf(ctx, "\"%s\"", literal->value.str);
        break;
    default:
    {
        char *name;
        assert(type == IDL_ENUM);
        name = typename(ctx, literal);
        idlpy_ctx_printf(ctx, "%s", name);
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
    idlpy_ctx ctx = (idlpy_ctx)user_data;

    char *type = typename(ctx, node);
    if (type == NULL)
        return IDL_RETCODE_NO_MEMORY;

    const idl_literal_t *literal = ((const idl_const_t *)node)->const_expr;

    idlpy_ctx_enter_entity(ctx, idl_identifier(node));
    idlpy_ctx_printf(ctx, "%s = ", type);
    print_literal(pstate, ctx, literal);
    idlpy_ctx_write(ctx, "\n\n");
    idlpy_ctx_exit_entity(ctx);

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
