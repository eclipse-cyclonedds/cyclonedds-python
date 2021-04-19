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

#include "types.h"
#include "generator.h"
#include "context.h"
#include "util.h"

#include "idl/file.h"
#include "idl/retcode.h"
#include "idl/stream.h"
#include "idl/string.h"
#include "idl/version.h"
#include "idl/processor.h"


bool generate_setup_py(const char* dir, const char *package_name);


idl_retcode_t
generate(const idl_pstate_t *pstate)
{
    idlpy_ctx ctx;
    idl_retcode_t ret = IDL_RETCODE_NO_MEMORY;
    const char *sep, *ext, *file, *path;
    char empty[1] = { '\0' };
    char *dir = NULL, *basename = NULL, *pkgpath = NULL;

    assert(pstate->paths);
    assert(pstate->paths->name);
    path = pstate->sources->path->name;
    /* use relative directory if user provided a relative path, use current
        work directory otherwise */
    sep = ext = NULL;
    for (const char *ptr = path; ptr[0]; ptr++) {
        if (idl_isseparator((unsigned char)ptr[0]) && ptr[1] != '\0')
        sep = ptr;
        else if (ptr[0] == '.')
        ext = ptr;
    }

    file = sep ? sep + 1 : path;
    if (idl_isabsolute(path) || !sep)
        dir = empty;
    else if (!(dir = idl_strndup(path, (size_t)(sep-path))))
        goto err_dir;
    if (!(basename = idl_strndup(file, ext ? (size_t)(ext-file) : strlen(file))))
        goto err_basename;

    /* replace backslashes by forward slashes */
    for (char *ptr = dir; *ptr; ptr++) {
        if (*ptr == '\\')
        *ptr = '/';
    }

    if (ext == NULL) {
        // no .idl like extension, use default name
        free(basename);
        basename = idl_strdup("idl_py_pkg");
    }

    // Separator from main path is either empty (relative path) or "/" after an absolute path
    sep = dir[0] == '\0' ? "" : "/";

    // Construct full absolute or relative path to our output package directory
    if (!idl_asprintf(&pkgpath, "%s%s%s", dir, sep, basename))
        goto err_pkgpath;

    /// This folder might exist, but we expressly ignore that error here
    /// You might just be overwriting an old generate from the same idl file
    mkdir(pkgpath, 0775);

    if (!generate_setup_py(pkgpath, basename)) {
        printf("Idlpy failed to generate setup.py\n");
        goto err_setup;
    }

    ctx = idlpy_new_ctx(pkgpath);
    ret = generate_types(pstate, ctx);
    idlpy_free_ctx(ctx);

err_setup:
    free(pkgpath);
err_pkgpath:
    free(basename);
err_basename:
    if (dir && dir != empty)
        free(dir);
err_dir:
    return ret;
}


bool generate_setup_py(const char* dir, const char *package_name)
{
    char* setup_py_file;
    if (!idl_asprintf(&setup_py_file, "%s/setup.py", dir))
        return false;
        
    FILE *f = open_file(setup_py_file, "w");
    free(setup_py_file);

    if (!f)
        return false;

    if (!idl_fprintf(f,
                "from setuptools import setup, find_packages\n\n"
                "setup(\n"
                "    name='%s',\n"
                "    packages=find_packages()\n"
                ")\n",
                package_name
    )) {
        fclose(f);
        return false;
    }

    fclose(f);
    return true;
}