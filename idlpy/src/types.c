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
    case IDL_WCHAR:
        idl_asprintf(&ret, "None");
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
    case IDL_ENUM:
        idl_asprintf(&ret, "%s.%s", idl_identifier(idl_parent(literal)), idl_identifier(literal));
        break;
    default:
        assert(0);
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

        //Reserved Python keywords support (Issue 105)
        const char *name = idlpy_identifier(node);
        
        ret = idlpy_ctx_enter_module(ctx, name);
        ///////////////////////////
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

    //Reserved Python keywords support (Issue 105)
    const char *name = idlpy_identifier(node);
    ////////////////////////////
    const void* type_spec;

    if (idl_is_array(node))
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
        idl_case_label_t* label = (idl_case_label_t*) mycase->labels;
        const char *comma = "";

        for (; label; label = idl_next(label)) {
            char *formatted = format_literal(ctx, label->const_expr);
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

    if (idl_is_member(parent)) {

        const idl_member_t *member = (const idl_member_t*) parent;

        if (member->optional.annotation && member->optional.value) {
            char *optional_wrapped_type;
            idl_asprintf(&optional_wrapped_type, "Optional[%s]", type);
            free(type);
            type = optional_wrapped_type;
        }
    }

    
    idlpy_ctx_printf(ctx, "\n    %s: %s", name, type);

    //Reserved Python keywords support (Issue 105)
    if (name != idlpy_identifier(node)) {
        idlpy_ctx_printf(ctx, "\n    annotate.member_name(\"%s\",\"%s\")", name, idlpy_identifier(node));
    }
    /////////////////////

    if (idl_is_member(parent)) {

        const idl_member_t *member = (const idl_member_t*) parent;

        if (!pstate->keylists && member->key.annotation && member->key.value) {
            idlpy_ctx_printf(ctx, "\n    annotate.key(\"%s\")", name);
        }

        if (member->external.annotation && member->external.value) {
            idlpy_ctx_printf(ctx, "\n    annotate.external(\"%s\")", name);
        }

        bool hash_id_set = false;
        for (idl_annotation_appl_t *a = ((idl_node_t *) member)->annotations; a; a = idl_next (a)) {
            if (!strcmp (a->annotation->name->identifier, "hashid")) {
                hash_id_set = true;
                if (a->parameters) {

                    idlpy_ctx_printf(ctx, "\n    annotate.member_hash_id(\"%s\", \"%s\")",
                        name,
                        ((const idl_literal_t *)a->parameters->const_expr)->value.str
                    );
                } else {
                    idlpy_ctx_printf(ctx, "\n    annotate.member_hash_id(\"%s\")",
                        name
                    );
                }
            }
        // FIXME: implement unit, min, max
        }

        if (!hash_id_set && member->declarators->id.annotation != NULL) {
            idlpy_ctx_printf(ctx, "\n    annotate.member_id(\"%s\", %" PRIu32 ")",
                name,
                member->declarators->id.value
            );
        }
    }

    free(type);
    (void)pstate;
    (void)revisit;
    (void)path;

    idlpy_ctx_emit_field(ctx);

    return IDL_RETCODE_OK;
}

static void struct_decoration(idlpy_ctx ctx, const void *node)
{
    idl_struct_t *_struct = (idl_struct_t *)node;

    idlpy_ctx_printf(ctx, "\n@dataclass\n");

    if (_struct->keylist)
    {
        idlpy_ctx_printf(ctx, "@annotate.keylist([");

        idl_key_t *key = _struct->keylist->keys;

        if (key)
        {
            //Reserved Python keywords support (Issue 105)
            const char *nameKey = filter_python_keywords(key->field_name->identifier);

            idlpy_ctx_printf(ctx, "\"%s\"", nameKey);
            ////////////////////

            key++;
        }

        while (key)
        {
            //Reserved Python keywords support (Issue 105)
            const char *nameKey = filter_python_keywords(key->field_name->identifier);

            idlpy_ctx_printf(ctx, ", \"%s\"", nameKey);
            ////////////////////
            
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

        //Reserved Python keywords support (Issue 105)
        const char *name = idlpy_identifier(node);
        ///////////////////////////

        idlpy_ctx_enter_entity(ctx, name);
        struct_decoration(ctx, node);
        char *fullname = idl_full_typename(node);
        idlpy_ctx_printf(ctx, "class %s(idl.IdlStruct, typename=\"%s\"):", name, fullname);
        free(fullname);
        ret = IDL_VISIT_REVISIT;
    }
    else
    {
        if (!idlpy_ctx_did_emit_field(ctx)) {
            idlpy_ctx_printf(ctx, "\n    pass");
        }
        idlpy_ctx_printf(ctx, "\n\n");
        idlpy_ctx_exit_entity(ctx);
        ret = IDL_RETCODE_OK;
    }

    (void)pstate;
    (void)path;

    return ret;
}

static idl_retcode_t
emit_bitmask(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx)user_data;
    idl_bitmask_t *bitmask = (idl_bitmask_t*) node;

    idlpy_ctx_enter_entity(ctx, idl_identifier(bitmask));

    idlpy_ctx_printf(ctx, "\n@dataclass\n");

    if (bitmask->bit_bound.annotation) {
        idlpy_ctx_printf(ctx, "@annotate.bit_bound(%" PRIu16 ")\n", bitmask->bit_bound.value);
    }

    if (bitmask->extensibility.annotation) {
        switch (bitmask->extensibility.value)
        {
        case IDL_FINAL:
            idlpy_ctx_printf(ctx, "@annotate.final\n");
            break;
        case IDL_APPENDABLE:
            idlpy_ctx_printf(ctx, "@annotate.appendable\n");
            break;
        default:
            // According to the spec a Bitmask Type extensibility_kind is always FINAL or APPENDABLE
            assert(0);
            break;
        }
    }

    //Reserved Python keywords support (Issue 105)
    const char *name = idlpy_identifier(node);
    //////////////////////////

    char *fullname = idl_full_typename(node);
    idlpy_ctx_printf(ctx, "class %s(idl.IdlBitmask, typename=\"%s\"):", name, fullname);
    free(fullname);

    for(idl_bit_value_t *v = bitmask->bit_values; v; v = idl_next(v)) {

        //Reserved Python keywords support (Issue 105)
        const char *name = idlpy_identifier(v);
        //////////////////////////
        idlpy_ctx_printf(ctx, "\n    %s: bool = False", name);

        if (v->position.annotation)
            idlpy_ctx_printf(ctx, "\n    annotate.position(\"%s\", %" PRIu16 ")", idl_identifier(v), v->position.value);
    }

    if (bitmask->bit_values == NULL) {
        idlpy_ctx_printf(ctx, "\n    pass");
    }

    idlpy_ctx_printf(ctx, "\n\n");

    idlpy_ctx_exit_entity(ctx);

    (void)pstate;
    (void)path;

    return IDL_RETCODE_OK;
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
        char *discriminator;
        idl_type_spec_t* discriminator_spec = (idl_type_spec_t*) ((idl_union_t *)node)->switch_type_spec->type_spec;

        if (idl_is_enum(discriminator_spec)) {
            idl_enum_t* enum_ = (idl_enum_t*) discriminator_spec;
            discriminator = idl_strdup(enum_->name->identifier);
        }
        else {
            discriminator = typename(ctx, (void*) discriminator_spec);
        }

        if (discriminator == NULL)
            return ret;

        idlpy_ctx_enter_entity(ctx, idl_identifier(node));
        idlpy_ctx_printf(ctx, "\n\n");
        union_decoration(ctx, node);
        char* fullname = idl_full_typename(node);

        //Reserved Python keywords support (Issue 105)
        const char *nameUnion = idlpy_identifier(node);

        idlpy_ctx_printf(ctx,
            "class %s(idl.IdlUnion, discriminator=%s, discriminator_is_key=%s, typename=\"%s\"):",
            nameUnion,
            discriminator,
            ((idl_union_t *)node)->switch_type_spec->key.value ? "True": "False",
            fullname
        );
        ///////////////////

        free(fullname);
        ret = IDL_VISIT_REVISIT;
        free(discriminator);
    }
    else
    {
        if (!idlpy_ctx_did_emit_field(ctx)) {
            idlpy_ctx_printf(ctx, "\n    pass");
        }
        idlpy_ctx_printf(ctx, "\n\n");
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
    char* absname = absolute_name(ctx, (void*) declarator);
    const idl_type_spec_t *type_spec = idl_type_spec(declarator);;

    /*
        There are two distinct possibilities:
        typedef char foo; typedef -> declarator -> char type
        typedef char foo[2]; typedef -> array declarator -> declarator -> char type
        This might be convinient for C, but we really need those array decls and decls swapped
     */

    idlpy_ctx_enter_entity(ctx, name);
    type = typename(ctx, type_spec);

    if (idl_is_array(declarator)) {
        // wrap _type_ in array descriptor
        const idl_const_expr_t* const_expr = declarator->const_expr;

        /* iterate backwards through the list so that the last entries in the list
            are the innermost arrays */
        for (const idl_const_expr_t *ce = const_expr; ce; ce = idl_next(ce))
            const_expr = ce;

        for (const idl_const_expr_t *ce = const_expr; ce; ce = idl_previous(ce)) {
            uint32_t dim = ((const idl_literal_t *)ce)->value.uint32;
            char *res;
            idl_asprintf(&res, "types.array[%s, %"PRIu32"]", type, dim);
            free(type);
            type = res;
        }
    }

    //Reserved Python keywords support (Issue 105)
    const char *nameType = filter_python_keywords(name);

    idlpy_ctx_printf(ctx, "%s = types.typedef[%s, %s]\n", nameType, absname, type);
    ///////////////////
    
    idlpy_ctx_exit_entity(ctx);
    free(absname);
    free(type);

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


static void enum_decoration(idlpy_ctx ctx, const idl_enum_t *_enum)
{

    switch (_enum->extensibility.value)
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

    if (_enum->bit_bound.annotation) {
        idlpy_ctx_printf(ctx, "@annotate.bit_bound(%" PRIu16 ")\n", _enum->bit_bound.value);
    }
}


static idl_retcode_t
emit_enum(
    const idl_pstate_t *pstate,
    bool revisit,
    const idl_path_t *path,
    const void *node,
    void *user_data)
{
    idlpy_ctx ctx = (idlpy_ctx)user_data;
    const idl_enum_t *_enum = (const idl_enum_t *) node;
    idl_retcode_t ret = IDL_RETCODE_NO_MEMORY;

    idlpy_ctx_enter_entity(ctx, idl_identifier(_enum));

    enum_decoration(ctx, _enum);

    char* fullname = idl_full_typename(node);

    //Reserved Python keywords support (Issue 105)
    const char *name = idlpy_identifier(node);
    ///////////////////////////
    idlpy_ctx_printf(ctx, "class %s(idl.IdlEnum, typename=\"%s\"", name, fullname);

    free(fullname);

    //Reserved Python keywords support (Issue 105)
    if (_enum->default_enumerator != NULL)
    {
        const char *nameDefaultEnumerator = filter_python_keywords(_enum->default_enumerator->name->identifier);

        idlpy_ctx_printf(ctx, ", default=\"%s\"", nameDefaultEnumerator);
    }
    ///////////////////////////

    idlpy_ctx_printf(ctx, "):\n");

    idl_enumerator_t *enumerator = ((const idl_enum_t *)node)->enumerators;
    for (; enumerator; enumerator = idl_next(enumerator))
    {
        //Reserved Python keywords support (Issue 105)
        const char *nameEnumerated = filter_python_keywords(enumerator->name->identifier);

        if (enumerator->value.annotation == NULL) {
            idlpy_ctx_printf(ctx, "    %s = auto()\n", nameEnumerated);
        } else {
            idlpy_ctx_printf(ctx, "    %s = %" PRIu32 "\n", nameEnumerated, enumerator->value.value);
        }
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

    const idl_literal_t *literal = ((const idl_const_t *)node)->const_expr;

    idlpy_ctx_enter_entity(ctx, idl_identifier(node));

    //Reserved Python keywords support (Issue 105)
    const char *nameConst = idlpy_identifier(node);
    
    idlpy_ctx_printf(ctx, "%s = ", nameConst);
    ///////////////////

    print_literal(pstate, ctx, literal);
    idlpy_ctx_write(ctx, "\n");
    idlpy_ctx_exit_entity(ctx);

    (void)revisit;
    (void)path;

    return IDL_RETCODE_OK;
}

idl_retcode_t generate_types(const idl_pstate_t *pstate, idlpy_ctx ctx)
{
    idl_retcode_t ret;
    idl_visitor_t visitor;

    memset(&visitor, 0, sizeof(visitor));
    visitor.visit = IDL_CONST | IDL_TYPEDEF | IDL_STRUCT | IDL_UNION | IDL_ENUM | IDL_DECLARATOR | IDL_MODULE | IDL_BITMASK;
    visitor.accept[IDL_ACCEPT_MODULE] = &emit_module;
    visitor.accept[IDL_ACCEPT_CONST] = &emit_const;
    visitor.accept[IDL_ACCEPT_TYPEDEF] = &emit_typedef;
    visitor.accept[IDL_ACCEPT_STRUCT] = &emit_struct;
    visitor.accept[IDL_ACCEPT_UNION] = &emit_union;
    visitor.accept[IDL_ACCEPT_ENUM] = &emit_enum;
    visitor.accept[IDL_ACCEPT_DECLARATOR] = &emit_field;
    visitor.accept[IDL_ACCEPT_BITMASK] = &emit_bitmask;
    visitor.sources = (const char *[]){pstate->sources->path->name, NULL};
    if ((ret = idl_visit(pstate, pstate->root, &visitor, ctx)))
        return ret;
    return IDL_RETCODE_OK;
}
