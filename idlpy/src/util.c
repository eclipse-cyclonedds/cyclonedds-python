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

#include "util.h"


FILE* open_file(const char *pathname, const char *mode)
{
#if _WIN32
    FILE *handle = NULL;
    if (fopen_s(&handle, pathname, mode) != 0)
        return NULL;
    return handle;
#else
    return fopen(pathname, mode);
#endif
}
