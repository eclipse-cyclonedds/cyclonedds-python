/*
 * Copyright(c) 2021 to 2022 ZettaScale Technology and others
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


const char* prefix_root_module = NULL;

idl_retcode_t
generate(const idl_pstate_t *pstate, const idlc_generator_config_t *config)
{
    idlpy_ctx ctx;
    idl_retcode_t ret = IDL_RETCODE_NO_MEMORY;

    const char *sep, *file, *path, *ext;
    char *basename = NULL;

    assert(pstate->paths);
    assert(pstate->paths->name);
    (void) config;

    path = pstate->sources->path->name;
    sep = ext = NULL;
    for (const char *ptr = path; ptr[0]; ptr++) {
        if (idl_isseparator((unsigned char)ptr[0]) && ptr[1] != '\0')
            sep = ptr;
        else if (ptr[0] == '.')
            ext = ptr;
    }

    file = sep ? sep + 1 : path;
    if (!(basename = idl_strndup(file, ext ? (size_t)(ext-file) : strlen(file))))
        goto err;

    ctx = idlpy_ctx_new("./", basename, prefix_root_module);

    // Enter root
    if (idlpy_ctx_enter_module(ctx, "") != IDL_VISIT_REVISIT) {
        idlpy_ctx_free(ctx);
        goto err;
    }

    ret = generate_types(pstate, ctx);

    if (ret == IDL_RETCODE_OK) {
        ret = idlpy_ctx_exit_module(ctx);
        if (ret == IDL_RETCODE_OK) {
            ret = idlpy_ctx_write_all(ctx);
        }
    }

    idlpy_ctx_free(ctx);
    free(basename);

err:
    return ret;
}


static const idlc_option_t *opts[] = {
    &(idlc_option_t) {
        IDLC_STRING, {.string = &prefix_root_module},
        'p', "py-root-prefix", "path.to.submodule",
        "Prefix all idl modules with a python path as root module. Handy if you want to include idl types as submodule in your project."
    },
    NULL
};

const idlc_option_t** generator_options(void)
{
    return opts;
}