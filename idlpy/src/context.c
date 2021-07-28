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
#include "ssos.h"
#include "util.h"


#include "idl/string.h"
#include "idl/tree.h"
#include "idl/stream.h"
#include "idl/file.h"
#include "idl/version.h"
#include "idl/visit.h"

/// TEMP:
#include "dds/ddsrt/filesystem.h"
///

#ifdef WIN32
#include <direct.h>
#define mkdir(dir, mode) _mkdir(dir)
#else
#include <sys/stat.h>
#endif

/// * IDL context * ///
typedef struct idlpy_module_ctx_s *idlpy_module_ctx;
struct idlpy_module_ctx_s
{
    /// Parent
    idlpy_module_ctx parent;

    /// Strings
    char* name;
    char* path;
    char* fullname;

    /// Member names
    idlpy_ssos entities;
    idlpy_ssos modules;
};

typedef struct idlpy_entity_ctx_s
{
    char* name;
    FILE* fp;
} *idlpy_entity_ctx;

struct idlpy_ctx_s
{
    idlpy_module_ctx module;
    idlpy_entity_ctx entity;
    char* basepath;
};

idlpy_ctx idlpy_ctx_new(const char *path)
{
    idlpy_ctx ctx = (idlpy_ctx)malloc(sizeof(struct idlpy_ctx_s));
    if (ctx == NULL) return NULL;

    ctx->basepath = idl_strdup(path);
    ctx->module = NULL;
    ctx->entity = NULL;

    if (ctx->basepath == NULL) {
        free(ctx);
        return NULL;
    }

    return ctx;
}

void idlpy_ctx_free(idlpy_ctx octx)
{
    assert(octx);
    assert(octx->basepath);
    assert(octx->module == NULL);
    assert(octx->entity == NULL);

    free(octx->basepath);
    free(octx);
}

static idlpy_module_ctx idlpy_module_ctx_new()
{
    idlpy_module_ctx ctx = (idlpy_module_ctx) malloc(sizeof(struct idlpy_module_ctx_s));

    if (ctx == NULL) return NULL;

    ctx->parent = NULL;
    ctx->name = NULL;
    ctx->path = NULL;
    ctx->fullname = NULL;

    ctx->entities = idlpy_ssos_new();

    if (ctx->entities == NULL) {
        free(ctx);
        return NULL;
    }

    ctx->modules = idlpy_ssos_new();

    if (ctx->modules == NULL) {
        idlpy_ssos_free(ctx->entities);
        free(ctx);
        return NULL;
    }

    return ctx;
}

static void idlpy_module_ctx_free(idlpy_module_ctx ctx)
{
    assert(ctx);

    if (ctx->name) free(ctx->name);
    if (ctx->path) free(ctx->path);
    if (ctx->fullname) free(ctx->fullname);

    idlpy_ssos_free(ctx->entities);
    idlpy_ssos_free(ctx->modules);

    free(ctx);
}

static idlpy_entity_ctx idlpy_entity_ctx_new()
{
    idlpy_entity_ctx ctx = (idlpy_entity_ctx) malloc(sizeof(struct idlpy_entity_ctx_s));

    if (ctx == NULL) return NULL;

    ctx->name = NULL;
    ctx->fp = NULL;

    return ctx;
}

static void idlpy_entity_ctx_free(idlpy_entity_ctx ctx)
{
    assert(ctx);
    assert(ctx->fp == NULL);

    if (ctx->name != NULL) free(ctx->name);
    free(ctx);
}

idl_retcode_t idlpy_ctx_enter_module(idlpy_ctx octx, const char *name)
{
    assert(octx);
    assert(name);

    idlpy_module_ctx ctx = idlpy_module_ctx_new();
    idl_retcode_t ret = IDL_VISIT_REVISIT;

    if (ctx == NULL) {
        return IDL_RETCODE_NO_MEMORY;
    }

    ctx->name = idl_strdup(name);

    if (ctx->name == NULL) {
        ret = IDL_RETCODE_NO_MEMORY;
        goto err;
    }

    ctx->parent = octx->module;
    octx->module = ctx;

    if (ctx->parent == NULL) {
        ctx->fullname = idl_strdup(ctx->name);

        if (ctx->fullname == NULL) {
            idlpy_module_ctx_free(ctx);
            return IDL_RETCODE_NO_MEMORY;
        }

        if (idl_asprintf(&ctx->path, "%s%s", octx->basepath, ctx->name) <= 0) {
            idlpy_ctx_report_error(octx, "Could not format path to module.");
            ret = IDL_RETCODE_NO_MEMORY;
            goto err;
        }
    } else {
        if (idlpy_ssos_add(ctx->parent->modules, name) == IDLPY_SSOS_RETCODE_NOMEMORY) {
            idlpy_ctx_report_error(octx, "Could not add module name to set.");
            ret = IDL_RETCODE_NO_MEMORY;
            goto err;
        }

        if (idl_asprintf(&ctx->fullname, "%s.%s", ctx->parent->fullname, ctx->name) <= 0) {
            idlpy_ctx_report_error(octx, "Could not format fullname of module.");
            ret = IDL_RETCODE_NO_MEMORY;
            goto err;
        }
        if (idl_asprintf(&ctx->path, "%s/%s", ctx->parent->path, ctx->name) <= 0) {
            idlpy_ctx_report_error(octx, "Could not format path of module.");
            ret = IDL_RETCODE_NO_MEMORY;
            goto err;
        }
    }

    mkdir(ctx->path, 0775);
err:
    if (ret != IDL_VISIT_REVISIT) {
        idlpy_module_ctx_free(ctx);
    }

    return ret;
}

static idl_retcode_t write_module_headers(idlpy_ctx octx, FILE *fh)
{
    idlpy_module_ctx ctx = octx->module;
    assert(ctx);

    static const char *fmt =
        "\"\"\"\n"
        "  Generated by Eclipse Cyclone DDS IDLC Python\n"
        "  Cyclone DDS IDL version: v%s\n"
        "\n"
        "\"\"\"\n"
        "\n"
        "%s";

    const char *scope_creator;

    if (ctx->parent == NULL) {
        scope_creator = "from cyclonedds.idl.scope import Scope\n\nscope = Scope(__name__)\n\n";
    } else {
        scope_creator = "from .. import scope as parent_scope\n\nscope = parent_scope.subscope(__name__)\n\n";
    }

    idl_fprintf(fh, fmt, IDL_VERSION, scope_creator);

    ddsrt_dir_handle_t handle;
    struct ddsrt_dirent dirent;
    char subpath_buffer[DDSRT_PATH_MAX + 1];

    if (ddsrt_opendir(ctx->path, &handle) != DDS_RETCODE_OK) {
        return IDL_RETCODE_NO_ACCESS;
    }

    while(ddsrt_readdir(handle, &dirent) == DDS_RETCODE_OK) {
        size_t len = strlen(dirent.d_name);

        if (strncmp(dirent.d_name, ".", 1) == 0 || strncmp(dirent.d_name, "_", 1) == 0)
            continue;

        if (strcmp(dirent.d_name + len - 3, ".py") == 0) {
            // Entity file
            memcpy(subpath_buffer, dirent.d_name, len - 3);
            subpath_buffer[len-3] = '\0';

            if (idlpy_ssos_search(ctx->entities, subpath_buffer) == -1) {
                char* warning;
                idl_asprintf(&warning, "Module %s contains entity %s but that was not registered during this run of idlc.", ctx->name, subpath_buffer);
                //idlpy_ctx_report_warning(octx, warning);
                free(warning);
            }

            idl_fprintf(fh, "from .%s import %s\n", subpath_buffer, subpath_buffer);

        } else {
            // Submodule dir
            if (idlpy_ssos_search(ctx->modules, dirent.d_name) == -1) {
                char* warning;
                idl_asprintf(&warning, "Module %s contains submodule %s but that was not registered during this run of idlc.", ctx->name, &dirent.d_name[0]);
                //idlpy_ctx_report_warning(octx, warning);
                free(warning);
            }

            idl_fprintf(fh, "import %s.%s as %s\n", ctx->fullname, &dirent.d_name[0], &dirent.d_name[0]);
        }
    }

    idl_fprintf(fh, "\n");
    return IDL_RETCODE_OK;
}

static void write_entity_headers(idlpy_ctx octx)
{
    assert(octx);
    assert(octx->module);
    assert(octx->module->fullname);
    assert(octx->entity);
    assert(octx->entity->fp);
    assert(octx->entity->name);

    static const char *fmt =
        "\"\"\"\n"
        "  Generated by Eclipse Cyclone DDS IDLC Python\n"
        "  Cyclone DDS IDL version: v%s\n"
        "  Module: %s\n"
        "  Entity: %s\n"
        "\n"
        "\"\"\"\n"
        "\n"
        "from cyclonedds.idl import idl\n"
        "import cyclonedds.idl.types as pt\n\n"
        "from . import scope\n\n\n";

    idl_fprintf(octx->entity->fp, fmt, IDL_VERSION, octx->module->fullname, octx->entity->name);
}

void idlpy_ctx_consume(idlpy_ctx octx, char *data)
{
    assert(octx);

    idlpy_ctx_printf(octx, data);
    free(data);
}

void idlpy_ctx_write(idlpy_ctx octx, const char *data)
{
    assert(octx);

    idlpy_ctx_printf(octx, data);
}

void idlpy_ctx_printf(idlpy_ctx octx, const char *fmt, ...)
{
    assert(octx);
    assert(octx->entity);
    assert(octx->entity->fp);

    va_list ap, cp;
    va_start(ap, fmt);
    va_copy(cp, ap);

    idl_vfprintf(octx->entity->fp, fmt, ap);

    va_end(ap);
    va_end(cp);
}

idl_retcode_t idlpy_ctx_exit_module(idlpy_ctx octx)
{
    assert(octx);
    assert(octx->module);
    assert(octx->module->path);

    FILE *file;
    char* path;
    idlpy_module_ctx ctx = octx->module;
    idl_retcode_t ret = IDL_RETCODE_OK;

    if (idl_asprintf(&path, "%s/__init__.py", ctx->path) <= 0) {
        idlpy_ctx_report_error(octx, "Could not construct path for module init writing");
        ret = IDL_RETCODE_NO_MEMORY;
        goto path_err;
    }

    file = open_file(path, "w");

    if (file == NULL) {
        char* error;
        idl_asprintf(&error, "Failed to open file %s for writing.", path);
        idlpy_ctx_report_error(octx, error);
        ret = IDL_RETCODE_NO_ACCESS;
        free(error);
        goto file_err;
    }

    write_module_headers(octx, file);
    fclose(file);

file_err:

    free(path);

path_err:

    octx->module = ctx->parent;
    idlpy_module_ctx_free(ctx);
    return ret;
}

idl_retcode_t idlpy_ctx_enter_entity(idlpy_ctx octx, const char* name)
{
    assert(octx);
    assert(octx->entity == NULL);
    assert(octx->module);
    assert(octx->module->entities);

    if(idlpy_ssos_add(octx->module->entities, name) != IDLPY_SSOS_RETCODE_OK) {
        idlpy_ctx_report_error(octx, "Could not entity name to set.");
        return IDL_RETCODE_NO_MEMORY;
    }

    char *path;
    if (idl_asprintf(&path, "%s/%s.py", octx->module->path, name) <= 0) {
        idlpy_ctx_report_error(octx, "Could not construct path for entity writing.");
        return IDL_RETCODE_NO_MEMORY;
    }

    octx->entity = idlpy_entity_ctx_new();
    if (octx->entity == NULL) {
        free(path);
        idlpy_ctx_report_error(octx, "Could not construct new entity context.");
        return IDL_RETCODE_NO_MEMORY;
    }

    octx->entity->name = idl_strdup(name);
    if (octx->entity->name == NULL) {
        free(path);
        idlpy_entity_ctx_free(octx->entity);
        idlpy_ctx_report_error(octx, "Failed to duplicate name string.");
        return IDL_RETCODE_NO_MEMORY;
    }

    octx->entity->fp = open_file(path, "w");

    if (octx->entity->fp == NULL) {
        char *error;
        idlpy_entity_ctx_free(octx->entity);
        idl_asprintf(&error, "Failed to open file %s for writing.", path);
        idlpy_ctx_report_error(octx, error);
        free(error);
        free(path);
        return IDL_RETCODE_NO_MEMORY;
    }

    free(path);
    write_entity_headers(octx);
    return IDL_RETCODE_OK;
}

idl_retcode_t idlpy_ctx_exit_entity(idlpy_ctx octx)
{
    assert(octx);
    assert(octx->entity);
    assert(octx->entity->fp);

    idlpy_ctx_write(octx, "\n");
    fclose(octx->entity->fp);
    octx->entity->fp = NULL;
    idlpy_entity_ctx_free(octx->entity);
    octx->entity = NULL;

    return IDL_RETCODE_OK;
}

void idlpy_ctx_report_error(idlpy_ctx ctx, const char* error)
{
    fprintf(stderr, "[ERROR] Module %s: %s\n", ctx->module->fullname, error);
}
