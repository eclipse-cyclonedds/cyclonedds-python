# will be written to __library__.py
from pathlib import Path
import platform

in_wheel = True

dir = Path(__file__).parent.resolve()

if platform.system() == "Darwin":
    library_path = list((dir / ".dylibs").glob("libddsc*"))[0]
elif platform.system() == "Windows":
    library_path = list((dir / ".." / "cyclonedds.libs").glob("ddsc*"))[0]
else:
    library_path = list((dir / ".." / "cyclonedds.libs").glob("libddsc*"))[0]
