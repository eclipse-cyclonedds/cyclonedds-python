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
#include <stdbool.h>

#include "context.h"
#include "ssos.h"
#include "util.h"


#include "idl/string.h"
#include "idl/tree.h"
#include "idl/stream.h"
#include "idl/file.h"
#include "idl/version.h"
#include "idl/visit.h"

#ifdef WIN32
#include <direct.h>
#define mkdir(dir, mode) _mkdir(dir)
#else
#include <sys/stat.h>
#endif

/// * IDL context * ///
typedef struct idlpy_file_defines_ctx_s *idlpy_file_defines_ctx;
struct idlpy_file_defines_ctx_s {
    idlpy_file_defines_ctx next;
    char* file_name;
    idlpy_ssos modules;
    idlpy_ssos entities;
};
static idlpy_file_defines_ctx idlpy_file_defines_ctx_new() {
    idlpy_file_defines_ctx ctx = (idlpy_file_defines_ctx) malloc(sizeof(struct idlpy_file_defines_ctx_s));

    if (!ctx) return NULL;

    ctx->modules = idlpy_ssos_new();
    if (!ctx->modules) {
        free(ctx);
        return NULL;
    }

    ctx->entities = idlpy_ssos_new();
    if (!ctx->entities) {
        idlpy_ssos_free(ctx->modules);
        free(ctx);
        return NULL;
    }
    ctx->next = NULL;
    ctx->file_name = NULL;

    return ctx;
}

static void idlpy_file_defines_ctx_free(idlpy_file_defines_ctx ctx) {
    if (!ctx) return;
    if (ctx->modules) idlpy_ssos_free(ctx->modules);
    if (ctx->entities) idlpy_ssos_free(ctx->entities);
    if (ctx->file_name) free(ctx->file_name);
    if (ctx->next) idlpy_file_defines_ctx_free(ctx->next);
    free(ctx);
}


typedef struct idlpy_module_ctx_s *idlpy_module_ctx;
struct idlpy_module_ctx_s
{
    /// Parent
    idlpy_module_ctx parent;

    /// Strings
    char* name;
    char* path;
    char* fullname;
    char* cache_filename;
    char* real_filename;
    char* manifest_filename;

    /// Defines
    idlpy_file_defines_ctx other_idl_files;
    idlpy_file_defines_ctx this_idl_file;

    /// Imports
    idlpy_ssos referenced_modules;

    /// Cache file
    FILE* fp;
};

typedef struct idlpy_entity_ctx_s
{
    char* name;
    bool did_emit_field;
} *idlpy_entity_ctx;

struct idlpy_ctx_s
{
    idlpy_module_ctx module;
    idlpy_module_ctx root_module;
    idlpy_module_ctx toplevel_module;
    idlpy_entity_ctx entity;
    char* basepath;
    char* idl_file;
    char* pyroot;
};

idlpy_ctx idlpy_ctx_new(const char *path, const char* idl_file, const char *pyroot)
{
    idlpy_ctx ctx = (idlpy_ctx)malloc(sizeof(struct idlpy_ctx_s));
    if (ctx == NULL) return NULL;

    ctx->basepath = idl_strdup(path);

    if (ctx->basepath == NULL) {
        free(ctx);
        return NULL;
    }

    ctx->idl_file = idl_strdup(idl_file);

    if (ctx->idl_file == NULL) {
        free(ctx->basepath);
        free(ctx);
        return NULL;
    }

    if (pyroot) {
        if (pyroot[strlen(pyroot)-1] == '.') {
            ctx->pyroot = idl_strdup(pyroot);
        } else {
            idl_asprintf(&ctx->pyroot, "%s.", pyroot);
        }
    } else {
        ctx->pyroot = idl_strdup("");
    }

    if (ctx->pyroot == NULL) {
        free(ctx->basepath);
        free(ctx->idl_file);
        free(ctx);
        return NULL;
    }

    ctx->module = NULL;
    ctx->root_module = NULL;
    ctx->toplevel_module = NULL;
    ctx->entity = NULL;

    if (ctx->basepath == NULL) {
        free(ctx);
        return NULL;
    }

    if (idlpy_ctx_enter_module(ctx, "") != IDL_VISIT_REVISIT) {
        idlpy_ctx_free(ctx);
        return NULL;
    }

    return ctx;
}

void idlpy_ctx_free(idlpy_ctx octx)
{
    assert(octx);
    assert(octx->basepath);
    assert(octx->idl_file);
    assert(octx->module != NULL);
    assert(octx->toplevel_module != NULL);
    assert(octx->root_module != NULL);
    assert(octx->entity == NULL);

    idlpy_ctx_exit_module(octx);

    if (octx->pyroot) free(octx->pyroot);

    free(octx->basepath);
    free(octx->idl_file);
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
    ctx->cache_filename = NULL;
    ctx->real_filename = NULL;
    ctx->manifest_filename = NULL;
    ctx->this_idl_file = idlpy_file_defines_ctx_new();
    ctx->other_idl_files = NULL;
    ctx->referenced_modules = idlpy_ssos_new();

    if (ctx->this_idl_file == NULL) {
        free(ctx);
        return NULL;
    }

    if (ctx->referenced_modules == NULL) {
        idlpy_file_defines_ctx_free(ctx->this_idl_file);
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
    if (ctx->cache_filename) free(ctx->cache_filename);
    if (ctx->real_filename) free(ctx->real_filename);
    if (ctx->manifest_filename) free(ctx->manifest_filename);
    if (ctx->this_idl_file) idlpy_file_defines_ctx_free(ctx->this_idl_file);
    if (ctx->other_idl_files) idlpy_file_defines_ctx_free(ctx->other_idl_files);
    if (ctx->referenced_modules) idlpy_ssos_free(ctx->referenced_modules);

    free(ctx);
}

static idlpy_entity_ctx idlpy_entity_ctx_new()
{
    idlpy_entity_ctx ctx = (idlpy_entity_ctx) malloc(sizeof(struct idlpy_entity_ctx_s));

    if (ctx == NULL) return NULL;

    ctx->name = NULL;
    ctx->did_emit_field = false;

    return ctx;
}

static void idlpy_entity_ctx_free(idlpy_entity_ctx ctx)
{
    assert(ctx);

    if (ctx->name != NULL) free(ctx->name);
    free(ctx);
}

idl_retcode_t idlpy_ctx_enter_module(idlpy_ctx octx, const char *name)
{
    assert(octx);
    assert(name);

    idlpy_module_ctx ctx = idlpy_module_ctx_new();
    idl_retcode_t ret = IDL_VISIT_REVISIT;
    FILE *_manifest;

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
        // Root module, types in single python file

        ctx->fullname = idl_strdup(ctx->name);
        octx->root_module = ctx;

        if (ctx->fullname == NULL) {
            idlpy_module_ctx_free(ctx);
            return IDL_RETCODE_NO_MEMORY;
        }

        if (idl_asprintf(&ctx->path, "%s", octx->basepath) <= 0) {
            idlpy_ctx_report_error(octx, "Could not format path to module.");
            ret = IDL_RETCODE_NO_MEMORY;
            goto err;
        }
    } else if (ctx->parent == octx->root_module) {
        // Top level module

        ctx->fullname = idl_strdup(ctx->name);
        octx->toplevel_module = ctx;

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
        // Submodule

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

        if (idlpy_ssos_add(ctx->parent->this_idl_file->modules, ctx->name) != IDLPY_SSOS_RETCODE_OK) {
            idlpy_entity_ctx_free(octx->entity);
            idlpy_ctx_report_error(octx, "Failed to add entity to local defines.");
            return IDL_RETCODE_NO_MEMORY;
        }
    }

    if (idl_asprintf(&ctx->real_filename, "%s/%s%s.py",
                     ctx->path,
                     (octx->root_module == ctx) ? "" : "_",
                     octx->idl_file) <= 0) {
        idlpy_ctx_report_error(octx, "Could not format path of python file.");
        ret = IDL_RETCODE_NO_MEMORY;
        goto err;
    }

    if (idl_asprintf(&ctx->cache_filename, "%s/_%s.cache", ctx->path, octx->idl_file) <= 0) {
        idlpy_ctx_report_error(octx, "Could not format path of python file.");
        ret = IDL_RETCODE_NO_MEMORY;
        goto err;
    }

    mkdir(ctx->path, 0775);
    ctx->fp = open_file(ctx->cache_filename, "w");

    if(!ctx->fp) {
        idlpy_ctx_report_error(octx, "Could not open cache file.");
        ret = IDL_RETCODE_NO_ACCESS;
        goto err;
    }

    if (idl_asprintf(&ctx->manifest_filename, "%s/.idlpy_manifest", ctx->path) <= 0) {
        idlpy_ctx_report_error(octx, "Could not format path of manifest file.");
        ret = IDL_RETCODE_NO_MEMORY;
        goto err;
    }

    _manifest = open_file(ctx->manifest_filename, "r");

    if (_manifest) {
        idlpy_file_defines_ctx current = NULL;
        char line[256];
        int mode = 0;
        bool write = true;

        while (fgets(line, sizeof(line), _manifest)) {
            line[strcspn(line, "\r\n")] = '\0';

            switch(mode) {
                case 0: // file
                {
                    mode = 1;
                    if (strcmp(line, octx->idl_file) == 0) {
                        // we overwrite this file right now
                        write = false;
                        break;
                    }
                    write = true;

                    idlpy_file_defines_ctx next = idlpy_file_defines_ctx_new();
                    if (next == NULL) {
                        goto err;
                    }

                    next->file_name = idl_strdup(line);

                    if (current == NULL) {
                        current = next;
                        ctx->other_idl_files = current;
                    } else {
                        current->next = next;
                        current = next;
                    }
                    break;
                }
                case 1: // modules
                {
                    if (*line == '\0') mode = 2;
                    else if (write) {
                        idlpy_ssos_add(current->modules, line);
                    }
                    break;
                }
                case 2: // entities
                {
                    if (*line == '\0') mode = 0;
                    else if (write) {
                        idlpy_ssos_add(current->entities, line);
                    }
                    break;
                }
                default:
                    assert(0);
            }
        }

        fclose(_manifest);
    }
err:
    if (ret != IDL_VISIT_REVISIT) {
        idlpy_module_ctx_free(ctx);
    }

    return ret;
}

static idl_retcode_t write_module_headers(FILE *fh, idlpy_ctx octx, const char* entity_prefix)
{
    static const char *fmt =
        "\"\"\"\n"
        "  Generated by Eclipse Cyclone DDS idlc Python Backend\n"
        "  Cyclone DDS IDL version: v%s\n"
        "  Module: %s\n"
        "\n"
        "\"\"\"\n"
        "\n";

    static const char *fmt_import = "from . import %s\n";
    static const char *fmt_entities = "from .%s%s import ";
    static const char *fmt_entity = "%s%s";

    idl_fprintf(fh, fmt, IDL_VERSION, octx->module->fullname);

    idlpy_file_defines_ctx mctx = octx->module->other_idl_files;
    idlpy_ssos modules = idlpy_ssos_new();

    if (!modules) {
        return IDL_RETCODE_NO_MEMORY;
    }

    while (mctx) {
        for(int i = 0; i < idlpy_ssos_size(mctx->modules); ++i) {
            idlpy_ssos_add(modules, idlpy_ssos_at(mctx->modules, i));
        }
        mctx = mctx->next;
    }
    for(int i = 0; i < idlpy_ssos_size(octx->module->this_idl_file->modules); ++i) {
        idlpy_ssos_add(modules, idlpy_ssos_at(octx->module->this_idl_file->modules, i));
    }

    for(int i = 0; i < idlpy_ssos_size(modules); ++i) {
        idl_fprintf(fh, fmt_import, idlpy_ssos_at(modules, i));
    }

    mctx = octx->module->other_idl_files;
    while (mctx) {
        if (idlpy_ssos_size(mctx->entities) > 0) {
            idl_fprintf(fh, fmt_entities, entity_prefix, mctx->file_name);

            for(int i = 0; i < idlpy_ssos_size(mctx->entities); ++i) {
                idl_fprintf(fh, fmt_entity, i > 0 ? ", " : "", idlpy_ssos_at(mctx->entities, i));
            }

            idl_fprintf(fh, "\n");
        }
        mctx = mctx->next;
    }

    if (idlpy_ssos_size(octx->module->this_idl_file->entities) > 0) {
        idl_fprintf(fh, fmt_entities, entity_prefix, octx->idl_file);

        for(int i = 0; i < idlpy_ssos_size(octx->module->this_idl_file->entities); ++i) {
            idl_fprintf(fh, fmt_entity, i > 0 ? ", " : "", idlpy_ssos_at(octx->module->this_idl_file->entities, i));
        }
        idl_fprintf(fh, "\n");
    }

    idl_fprintf(fh, "__all__ = [");
    for(int i = 0; i < idlpy_ssos_size(modules); ++i) {
        idl_fprintf(fh, "\"%s\", ", idlpy_ssos_at(modules, i));
    }
    mctx = octx->module->other_idl_files;
    while (mctx) {
        if (idlpy_ssos_size(mctx->entities) > 0) {
            for(int i = 0; i < idlpy_ssos_size(mctx->entities); ++i) {
                idl_fprintf(fh, "\"%s\", ", idlpy_ssos_at(mctx->entities, i));
            }
        }
        mctx = mctx->next;
    }

    if (idlpy_ssos_size(octx->module->this_idl_file->entities) > 0) {
        for(int i = 0; i < idlpy_ssos_size(octx->module->this_idl_file->entities); ++i) {
            idl_fprintf(fh, "\"%s\", ", idlpy_ssos_at(octx->module->this_idl_file->entities, i));
        }
    }

    idl_fprintf(fh, "]\n");
    idlpy_ssos_free(modules);

    return IDL_RETCODE_OK;
}

static void write_pyfile_finish(idlpy_ctx octx)
{
    assert(octx);
    assert(octx->module);
    assert(octx->module->fullname);
    assert(octx->module->fp);
    assert(octx->entity);
    assert(octx->entity->name);

    FILE *cache, *real;
    int c;

    static const char *fmt =
        "\"\"\"\n"
        "  Generated by Eclipse Cyclone DDS idlc Python Backend\n"
        "  Cyclone DDS IDL version: v%s\n"
        "  Module: %s\n"
        "  IDL file: %s.idl\n"
        "\n"
        "\"\"\"\n"
        "\n"
        "from enum import auto\n"
        "from typing import TYPE_CHECKING, Optional\n"
        "from dataclasses import dataclass\n\n"
        "import cyclonedds.idl as idl\n"
        "import cyclonedds.idl.annotations as annotate\n"
        "import cyclonedds.idl.types as types\n\n"
        "# root module import for resolving types\n"
        "import %s%s\n\n";


    fclose(octx->module->fp);


    if (idlpy_ssos_size(octx->module->this_idl_file->entities) > 0) {
        cache = open_file(octx->module->cache_filename, "r");
        real = open_file(octx->module->real_filename, "w");

        if (!cache || !real) {
            if (cache) fclose(cache);
            if (real) fclose(real);

            idlpy_ctx_report_error(octx, "Could not open cache and/or real files.");
            return;
        }

        idl_fprintf(real, fmt, IDL_VERSION, octx->module->fullname, octx->idl_file, octx->pyroot, octx->toplevel_module->fullname);

        if (idlpy_ssos_size(octx->module->referenced_modules) > 0) {
            idl_fprintf(real, "if TYPE_CHECKING:\n");
            for(int i = 0; i < idlpy_ssos_size(octx->module->referenced_modules); ++i) {
                idl_fprintf(real, "    import %s%s\n", octx->pyroot, idlpy_ssos_at(octx->module->referenced_modules, i));
            }
            idl_fprintf(real, "\n\n");
        }

        while ((c = fgetc(cache)) != EOF) {
            fputc(c, real);
        }
        idl_fprintf(real, "\n");

        fclose(cache);
        fclose(real);
    }

    remove(octx->module->cache_filename);
}


static void write_toplevel_pyfile_finish(idlpy_ctx octx)
{
    assert(octx);
    assert(octx->module);
    assert(octx->module->fullname);
    assert(octx->module->fp);
    assert(octx->entity);
    assert(octx->entity->name);

    FILE *cache, *real;
    int c;

    static const char *fmt =
        "\"\"\"\n"
        "  Generated by Eclipse Cyclone DDS idlc Python Backend\n"
        "  Cyclone DDS IDL version: v%s\n"
        "  Module: %s\n"
        "  IDL file: %s.idl\n"
        "\n"
        "\"\"\"\n"
        "\n"
        "from enum import auto\n"
        "from typing import TYPE_CHECKING, Optional\n"
        "from dataclasses import dataclass\n\n"
        "import cyclonedds.idl as idl\n"
        "import cyclonedds.idl.annotations as annotate\n"
        "import cyclonedds.idl.types as types\n\n";
    static const char *fmt2 =
        "# root module import for resolving types\n"
        "import %s%s\n\n";


    fclose(octx->module->fp);


    if (idlpy_ssos_size(octx->module->this_idl_file->entities) > 0) {
        cache = open_file(octx->module->cache_filename, "r");
        real = open_file(octx->module->real_filename, "w");

        if (!cache || !real) {
            if (cache) fclose(cache);
            if (real) fclose(real);

            idlpy_ctx_report_error(octx, "Could not open cache and/or real files.");
            return;
        }

        idl_fprintf(real, fmt, IDL_VERSION, octx->module->fullname, octx->idl_file);

        if (strcmp(octx->pyroot, "") != 0 && octx->toplevel_module)
            idl_fprintf(real, fmt2, octx->pyroot, octx->toplevel_module->fullname);

        if (idlpy_ssos_size(octx->module->referenced_modules) > 0) {
            idl_fprintf(real, "if TYPE_CHECKING:\n");
            for(int i = 0; i < idlpy_ssos_size(octx->module->referenced_modules); ++i) {
                idl_fprintf(real, "    import %s%s\n", octx->pyroot, idlpy_ssos_at(octx->module->referenced_modules, i));
            }
            idl_fprintf(real, "\n\n");
        }

        while ((c = fgetc(cache)) != EOF) {
            fputc(c, real);
        }
        idl_fprintf(real, "\n");

        fclose(cache);
        fclose(real);
    }

    remove(octx->module->cache_filename);
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
    assert(octx->module);
    assert(octx->module->fp);

    va_list ap, cp;
    va_start(ap, fmt);
    va_copy(cp, ap);

    idl_vfprintf(octx->module->fp, fmt, ap);

    va_end(ap);
    va_end(cp);
}

idl_retcode_t idlpy_ctx_exit_module(idlpy_ctx octx)
{
    assert(octx);
    assert(octx->module);
    assert(octx->module->path);

    FILE *file;
    char* path = NULL;
    idlpy_module_ctx ctx = octx->module;
    idl_retcode_t ret = IDL_RETCODE_OK;
    bool write_init_file = (octx->root_module != ctx) || (strcmp(octx->pyroot, "") != 0);

    if (octx->root_module != ctx) {
        write_pyfile_finish(octx);
    } else {
        write_toplevel_pyfile_finish(octx);
    }

    if (write_init_file) {
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

        const char* prefix =
            (octx->root_module == ctx) ? "" : "_";
        write_module_headers(
            file, octx, prefix
        );
        fclose(file);

        file = open_file(ctx->manifest_filename, "w");

        if (file == NULL) {
            char* error;
            idl_asprintf(&error, "Failed to open file %s for writing.", ctx->manifest_filename);
            idlpy_ctx_report_error(octx, error);
            ret = IDL_RETCODE_NO_ACCESS;
            free(error);
            goto file_err;
        }

        idlpy_file_defines_ctx mctx = octx->module->other_idl_files;
        while (mctx) {
            idl_fprintf(file, "%s\n", mctx->file_name);
            for(int i = 0; i < idlpy_ssos_size(mctx->modules); ++i) {
                idl_fprintf(file, "%s\n", idlpy_ssos_at(mctx->modules, i));
            }
            idl_fprintf(file, "\n");
            for(int i = 0; i < idlpy_ssos_size(mctx->entities); ++i) {
                idl_fprintf(file, "%s\n", idlpy_ssos_at(mctx->entities, i));
            }
            idl_fprintf(file, "\n");
            mctx = mctx->next;
        }
        idl_fprintf(file, "%s\n", octx->idl_file);
        for(int i = 0; i < idlpy_ssos_size(ctx->this_idl_file->modules); ++i) {
            idl_fprintf(file, "%s\n", idlpy_ssos_at(ctx->this_idl_file->modules, i));
        }
        idl_fprintf(file, "\n");
        for(int i = 0; i < idlpy_ssos_size(ctx->this_idl_file->entities); ++i) {
            idl_fprintf(file, "%s\n", idlpy_ssos_at(ctx->this_idl_file->entities, i));
        }

        fclose(file);
    }

file_err:
    if (path)
        free(path);

path_err:

    octx->module = ctx->parent;
    if (octx->root_module == ctx) octx->root_module = NULL;
    if (octx->toplevel_module == ctx) octx->toplevel_module = NULL;

    idlpy_module_ctx_free(ctx);
    return ret;
}

idl_retcode_t idlpy_ctx_enter_entity(idlpy_ctx octx, const char* name)
{
    assert(octx);
    assert(octx->entity == NULL);
    assert(octx->module);

    octx->entity = idlpy_entity_ctx_new();
    if (octx->entity == NULL) {
        idlpy_ctx_report_error(octx, "Could not construct new entity context.");
        return IDL_RETCODE_NO_MEMORY;
    }

    octx->entity->name = idl_strdup(name);
    if (octx->entity->name == NULL) {
        idlpy_entity_ctx_free(octx->entity);
        idlpy_ctx_report_error(octx, "Failed to duplicate name string.");
        return IDL_RETCODE_NO_MEMORY;
    }

    if (idlpy_ssos_add(octx->module->this_idl_file->entities, name) != IDLPY_SSOS_RETCODE_OK) {
        idlpy_entity_ctx_free(octx->entity);
        idlpy_ctx_report_error(octx, "Failed to add entity to local defines.");
        return IDL_RETCODE_NO_MEMORY;
    }

    return IDL_RETCODE_OK;
}

idl_retcode_t idlpy_ctx_exit_entity(idlpy_ctx octx)
{
    assert(octx);
    assert(octx->entity);

    idlpy_entity_ctx_free(octx->entity);
    octx->entity = NULL;

    return IDL_RETCODE_OK;
}

idl_retcode_t idlpy_ctx_reference_module(idlpy_ctx octx, const char* name)
{
    assert(octx);
    assert(octx->module);
    assert(octx->module->fullname);

    if (strcmp(octx->module->fullname, name) == 0)
        return IDL_RETCODE_OK;

    if (idlpy_ssos_add(octx->module->referenced_modules, name) != IDLPY_SSOS_RETCODE_OK)
        return IDL_RETCODE_NO_MEMORY;

    return IDL_RETCODE_OK;
}

void idlpy_ctx_emit_field(idlpy_ctx octx)
{
    octx->entity->did_emit_field = true;
}

bool idlpy_ctx_did_emit_field(idlpy_ctx octx)
{
    return octx->entity->did_emit_field;
}

void idlpy_ctx_report_error(idlpy_ctx ctx, const char* error)
{
    fprintf(stderr, "[ERROR] Module %s: %s\n", ctx->module->fullname, error);
}

const char* idlpy_ctx_get_pyroot(idlpy_ctx ctx)
{
    return ctx->pyroot;
}