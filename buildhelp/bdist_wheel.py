"""
 * Copyright(c) 2021 to 2022 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

import platform
from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
from cyclone_search import find_cyclonedds
from pathlib import Path
import shutil
import os


class bdist_wheel(_bdist_wheel):
    def initialize_options(self):
        self.standalone = os.environ.get("STANDALONE_WHEELS") == "1"
        super().initialize_options()

    def finalize_options(self):
        if self.standalone:
            self.distribution.entry_points["console_scripts"].append("idlc=cyclonedds.tools.wheel_idlc:command")
        super().finalize_options()

    def run(self):
        if self.standalone:
            cyclone = find_cyclonedds()

            newlibdir = Path(self.bdist_dir) / 'cyclonedds' / '.libs'

            os.makedirs(newlibdir, exist_ok=True)
            (Path(self.bdist_dir) / 'cyclonedds' / '__library__.py').write_text(
                (Path(__file__).parent / "wheel_library.py").read_text()
            )

            if not platform.system() == "Darwin":
                shutil.copy(cyclone.ddsc_library, newlibdir / cyclone.ddsc_library.name)

            if cyclone.idlc_executable and cyclone.idlc_library:
                shutil.copy(cyclone.idlc_executable, newlibdir / cyclone.idlc_executable.name)

        super().run()
