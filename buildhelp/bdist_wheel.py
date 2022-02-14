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
            with open(Path(self.bdist_dir) / 'cyclonedds' / '__library__.py', "w", encoding='utf-8') as f:
                f.write("from pathlib import Path\n\n")
                f.write("in_wheel = True\n")
                f.write(f"library_path = Path(__file__).parent / '.libs' / '{cyclone.ddsc_library.name}'")

            shutil.copy(cyclone.ddsc_library, newlibdir / cyclone.ddsc_library.name)

            if cyclone.idlc_executable and cyclone.idlc_library:
                shutil.copy(cyclone.idlc_executable, newlibdir / cyclone.idlc_executable.name)
                shutil.copy(cyclone.idlc_library, newlibdir / cyclone.idlc_library.name)

            for lib in cyclone.security_libs:
                shutil.copy(lib, newlibdir / lib.name)

        super().run()
