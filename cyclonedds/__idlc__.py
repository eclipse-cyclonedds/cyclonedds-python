"""
 * Copyright(c) 2021 ADLINK Technology Limited and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

from sys import exit
from pathlib import Path


idlpy_path = list(Path(__file__).resolve().parent.glob("_idlpy*"))[0]


if __name__ == "__main__":
    print(idlpy_path, end="", flush=True)
    exit(0)
