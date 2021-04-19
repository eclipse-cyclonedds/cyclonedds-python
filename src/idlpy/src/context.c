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
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stddef.h>
#include <stdlib.h>
#include <assert.h>

#include "context.h"
#include "util.h"


#include "idl/string.h"
#include "idl/tree.h"
#include "idl/stream.h"
#include "idl/file.h"
#include "idl/version.h"


#ifdef WIN32
#include <direct.h>
#define mkdir(dir, mode) _mkdir(dir)
#else
#include <sys/stat.h>
#endif

/// * IDL UTILITIES * ///

void idlpy_exit_memory_error()
{
    /// How unlikely is it to get here? If someone actually hits this function out in the wild
    /// without actively pushing for it I will be _very_ suprised.

    printf("Out of memory.");
    assert(0);
}

char *absolute_name(const void *node)
{
    char *str;
    size_t cnt, len = 0;
    const char *sep, *ident;
    const char *separator = ".";
    const idl_node_t *root;

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
        idlpy_exit_memory_error();

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

/// * IMPORT LIST UTILITES * ///
// Note: is it worth it to do hashmaps here?

typedef struct import_list_s *import_list;
struct import_list_s
{
    char *import;
    import_list next;
};

void free_import_list(import_list list)
{
    if (list == NULL)
        return;
    free_import_list(list->next);
    if (list->import != NULL)
        free(list->import);
    free(list);
}

void ensure_on_import_list(import_list *list, const char *type)
{
    import_list cursor = *list;
    import_list *previous = list;

    while (cursor)
    {
        int r = strcmp(type, cursor->import);
        if (r == 0)
            return;
        if (r > 0)
        {
            import_list new_import = malloc(sizeof(struct import_list_s));
            if (new_import == NULL)
                idlpy_exit_memory_error();

            new_import->import = idl_strdup(type);
            new_import->next = cursor;
            *previous = new_import;
            return;
        }
        previous = &(cursor->next);
        cursor = cursor->next;
    }
    import_list new_import = malloc(sizeof(struct import_list_s));
    if (new_import == NULL)
        idlpy_exit_memory_error();

    new_import->import = idl_strdup(type);
    new_import->next = NULL;
    *previous = new_import;
}

bool is_on_import_list(const import_list list, const char *type)
{
    import_list cursor = list;

    while (cursor)
    {
        int r = strcmp(type, cursor->import);
        if (r == 0)
            return true;
        if (r > 0)
            return false;
    }
    return false;
}

/// * IDL context * ///
typedef struct idlpy_module_ctx_s *idlpy_module_ctx;
struct idlpy_module_ctx_s
{
    /// Parent
    idlpy_module_ctx parent;

    /// For which module is this context?
    const void *module_node;

    /// Name
    char *name;

    /// Buffered output
    char *buffer;
    size_t buffer_size;
    size_t buffer_capacity;

    /// Imported names lists
    import_list local_defined_types;
    import_list imported_base_types;
    import_list imported_toplevel_types;
    import_list submodules;

    /// Where are we saving this?
    bool has_sub_modules;
    char *path;
};

struct idlpy_ctx_s
{
    idlpy_module_ctx real;
    char* path;
};

void idlpy_module_ctx_free(idlpy_module_ctx ctx)
{
    free(ctx->name);
    free(ctx->buffer);
    free_import_list(ctx->local_defined_types);
    free_import_list(ctx->imported_base_types);
    free_import_list(ctx->imported_toplevel_types);
    free_import_list(ctx->submodules);
    free(ctx->path);
    free(ctx);
}

idlpy_ctx idlpy_new_ctx(const char *path)
{
    idlpy_ctx ctx = (idlpy_ctx)malloc(sizeof(struct idlpy_ctx_s));
    if (ctx == NULL)
        idlpy_exit_memory_error();
    memset(ctx, 0, sizeof(struct idlpy_ctx_s));

    ctx->path = idl_strdup(path);
    ctx->real = NULL;
}

void idlpy_free_ctx(idlpy_ctx ctx)
{
    free(ctx->path);
}

void idlpy_enter_module(idlpy_ctx octx, const void *module)
{
    idlpy_module_ctx ctx = (idlpy_module_ctx)malloc(sizeof(struct idlpy_module_ctx_s));
    if (ctx == NULL)
        idlpy_exit_memory_error();
    memset(ctx, 0, sizeof(struct idlpy_module_ctx_s));

    ctx->module_node = module;

    ctx->name = idl_strdup(idl_identifier(module));

    ctx->buffer = (char *)malloc(512);
    ctx->buffer_size = 0;
    ctx->buffer_capacity = 512;

    ctx->local_defined_types = NULL;
    ctx->imported_base_types = NULL;
    ctx->imported_toplevel_types = NULL;
    ctx->submodules = NULL;

    if (octx->real == NULL)
    {
        // This is a top level module
        size_t pathlen = strlen(octx->path);
        size_t namelen = strlen(ctx->name);

        ctx->has_sub_modules = false;
        ctx->path = (char *)malloc(pathlen + namelen + 1);
        memcpy(ctx->path, octx->path, pathlen);
        memset(ctx->path + pathlen, '/', 1);
        memcpy(ctx->path + pathlen + 1, ctx->name, namelen);
        octx->real = ctx;
    }
    else
    {
        // This is a child module
        size_t pathlen = strlen(octx->real->path);
        size_t namelen = strlen(ctx->name);

        ctx->has_sub_modules = false;
        ctx->path = (char *)malloc(pathlen + namelen + 1);
        memcpy(ctx->path, octx->real->path, pathlen);
        memset(ctx->path + pathlen, '/', 1);
        memcpy(ctx->path + pathlen + 1, ctx->name, namelen);

        if (!octx->real->has_sub_modules)
        {
            octx->real->has_sub_modules = true;
            ensure_on_import_list(&(octx->real->submodules), ctx->name);
            mkdir(octx->real->path, 0775);
        }
        ctx->parent = octx->real;
        octx->real = ctx;
    }
}


void idlpy_ensure_basetype_import(idlpy_ctx octx, const char *type)
{
    idlpy_module_ctx ctx = octx->real;
    assert(ctx);
    ensure_on_import_list(&(ctx->imported_base_types), type);
}

void idlpy_ensure_toplevel_import(idlpy_ctx octx, const char *type)
{
    idlpy_module_ctx ctx = octx->real;
    assert(ctx);
    ensure_on_import_list(&(ctx->imported_toplevel_types), type);
}

void idlpy_define_local(idlpy_ctx octx, const char *type)
{
    idlpy_module_ctx ctx = octx->real;
    assert(ctx);
    ensure_on_import_list(&(ctx->local_defined_types), type);
}

char *idlpy_imported_name(idlpy_ctx octx, const void *node)
{
    idlpy_module_ctx ctx = octx->real;
    assert(ctx);
    if (idl_parent(node) == ctx->module_node)
    {
        /// This means this thing is local! We can maybe refer to it directly
        /// Except if it is a forward decl
        if (is_on_import_list(ctx->local_defined_types, idl_identifier(node))) {
            /// Nice!
            return idl_strdup(idl_identifier(node));
        } else {
            /// This is forward declared but can be locally resolved
            const char *fmt = "'%s'";
            char *result;
            idl_asprintf(&result, fmt, idl_identifier(node));
            return result;
        }
    }

    /// We must refer to this type by fully specified name
    const char *fmt = "'%s'";
    char *result;
    idl_asprintf(&result, fmt, absolute_name(node));
    return result;
}

void idlpy_write_headers(idlpy_ctx octx, FILE *fh)
{
    idlpy_module_ctx ctx = octx->real;
    assert(ctx);
    static const char *fmt =
        "\"\"\"\n"
        "  Generator by Eclipse Cyclone DDS IDL to Py Translator\n"
        "  Name: %s\n"
        "  Cyclone DDS: v%s\n"
        "\n"
        "\"\"\"\n\n";

    idl_fprintf(fh, fmt, ctx->name, IDL_VERSION);

    if (ctx->imported_toplevel_types != NULL)
    {
        import_list cursor = ctx->imported_toplevel_types;

        idl_fprintf(fh, "from pycdr import ");

        while (cursor)
        {
            idl_fprintf(fh, "%s", cursor->import);
            if (cursor->next)
                idl_fprintf(fh, ", ");
            cursor = cursor->next;
        }
        idl_fprintf(fh, "\n");
    }

    if (ctx->imported_base_types != NULL)
    {
        import_list cursor = ctx->imported_base_types;

        idl_fprintf(fh, "from pycdr.types import ");

        while (cursor)
        {
            idl_fprintf(fh, "%s", cursor->import);
            if (cursor->next)
                idl_fprintf(fh, ", ");
            cursor = cursor->next;
        }
        idl_fprintf(fh, "\n");
    }

    if (ctx->submodules != NULL)
    {
        import_list cursor = ctx->submodules;

        while (cursor)
        {
            idl_fprintf(fh, "import .%s\n", cursor->import);
            cursor = cursor->next;
        }
        idl_fprintf(fh, "\n");
    }

    idl_fprintf(fh, "\n");
}

void idlpy_grow_buffer(idlpy_module_ctx ctx)
{
    ctx->buffer_capacity *= 2;

    char *new_buffer = malloc(ctx->buffer_capacity);
    if (new_buffer == NULL)
        idlpy_exit_memory_error();

    memcpy(new_buffer, ctx->buffer, ctx->buffer_size);
    free(ctx->buffer);
    ctx->buffer = new_buffer;
}

void idlpy_consume(idlpy_ctx octx, char *data)
{
    idlpy_module_ctx ctx = octx->real;
    size_t datalen = strlen(data);
    assert(ctx);

    while (ctx->buffer_size + datalen > ctx->buffer_capacity)
    {
        idlpy_grow_buffer(ctx);
    }

    memcpy(ctx->buffer + ctx->buffer_size, data, datalen);
    free(data);
    ctx->buffer_size += datalen;
}

void idlpy_write(idlpy_ctx octx, const char *data)
{
    idlpy_module_ctx ctx = octx->real;
    size_t datalen = strlen(data);
    assert(ctx);

    while (ctx->buffer_size + datalen > ctx->buffer_capacity)
    {
        idlpy_grow_buffer(ctx);
    }

    memcpy(ctx->buffer + ctx->buffer_size, data, datalen);
    ctx->buffer_size += datalen;
}

void idlpy_printf(idlpy_ctx octx, const char *fmt, ...)
{
    idlpy_module_ctx ctx = octx->real;
    assert(ctx);

    va_list ap, cp;
    va_start(ap, fmt);
    va_copy(cp, ap);

    int len = idl_vsnprintf(ctx->buffer + ctx->buffer_size, ctx->buffer_capacity - ctx->buffer_size, fmt, ap);
    if (ctx->buffer_size + len > ctx->buffer_capacity) {
        while (ctx->buffer_size + len > ctx->buffer_capacity)
        {
            idlpy_grow_buffer(ctx);
        }
        idl_vsnprintf(ctx->buffer + ctx->buffer_size, ctx->buffer_capacity - ctx->buffer_size, fmt, ap);
    }

    ctx->buffer_size += len;

    va_end(ap);
    va_end(cp);
}

void idlpy_exit_module(idlpy_ctx octx)
{
    idlpy_module_ctx ctx = octx->real;
    assert(ctx);

    FILE *file;

    if (ctx->has_sub_modules)
    {
        const char *_file = "/__init__.py";
        size_t filelen = strlen(_file);
        size_t pathlen = strlen(ctx->path);

        char *path = (char *)malloc(pathlen + filelen + 1);
        memcpy(path, ctx->path, pathlen);
        memcpy(path + pathlen, _file, filelen + 1);

        file = open_file(path, "w");
    }
    else
    {
        const char *_file = ".py";
        size_t filelen = strlen(_file);
        size_t pathlen = strlen(ctx->path);

        char *path = (char *)malloc(pathlen + filelen + 1);
        memcpy(path, ctx->path, pathlen);
        memcpy(path + pathlen, _file, filelen + 1);

        file = open_file(path, "w");
    }

    idlpy_write_headers(octx, file);

    if (ctx->buffer_size <= 2) {
        // No action
    } else if (ctx->buffer[ctx->buffer_size-1] != '\n') {
        // No trailing newline, add it
        ctx->buffer[ctx->buffer_size] = '\n';
        ctx->buffer_size++;
    } else {
        // Strip of multiple newlines
        while (ctx->buffer_size > 2 && ctx->buffer[ctx->buffer_size-2] == '\n')
            ctx->buffer_size--;
    }

    fwrite(ctx->buffer, 1, ctx->buffer_size, file);
    fclose(file);

    octx->real = ctx->parent;
    idlpy_module_ctx_free(ctx);
}

void idlpy_report_error(idlpy_ctx ctx, const char* error)
{
    fprintf(stderr, "[ERROR] Module %s: %s\n", ctx->real->name, error);
}
