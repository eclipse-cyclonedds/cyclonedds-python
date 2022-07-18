import io
import textwrap
import zipfile
import random
from types import ModuleType

from subprocess import Popen, PIPE, TimeoutExpired
from dataclasses import dataclass
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import List, Optional, Tuple
from pathlib import Path

from .containers import REntity, RScope, REntity
from .creator import generate_random_idl
from .compile import compile_idl
from .c_app import generate_c_application


@dataclass
class CAppContext:
    executable: NamedTemporaryFile
    xtypes_dynamic_index: str
    running: bool = False
    last_error: str = ""
    last_out: str = ""
    process: Optional[Popen] = None

    def run(self, typename: str, num_samples: int) -> None:
        self.process = Popen([self.executable.name, typename, str(num_samples)], stderr=PIPE, stdout=PIPE)

    def description(self, typename: str) -> Optional[Tuple[bytes, bytes]]:
        self.process = Popen([self.executable.name, typename, "desc"], stderr=PIPE, stdout=PIPE)
        try:
            out, err = self.process.communicate(timeout=2)
        except TimeoutExpired:
            self.process.kill()
            try:
                out, err = self.process.communicate(timeout=2)
                self.last_error = err.decode()
            except:
                self.last_error = "Did not manage to grab error output."
            return None

        hashes = out.decode().splitlines()
        if len(hashes) < 2:
            return None

        return bytes.fromhex(hashes[0]), bytes.fromhex(hashes[1])

    def typebuilder(self, typename: str) -> Tuple[bool, str]:
        self.process = Popen([self.executable.name, typename, "typebuilder"], stderr=PIPE, stdout=PIPE)
        try:
            out, err = self.process.communicate(timeout=2)
        except TimeoutExpired:
            self.process.kill()
            try:
                out, err = self.process.communicate(timeout=2)
                self.last_error = err.decode()
            except:
                self.last_error = "Did not manage to grab error output."
            return -1
        if self.process.returncode == 0:
            return True, ""
        return False, out.decode()

    def result(self) -> Optional[List[bytes]]:
        try:
            out, err = self.process.communicate(timeout=2)
            self.last_out = out.decode()
        except TimeoutExpired:
            self.process.kill()
            try:
                out, err = self.process.communicate(timeout=2)
                self.last_error = err.decode()
                self.last_out = out.decode()
            except:
                self.last_error = "Did not manage to grab error output."
            return None

        self.last_error = err.decode()

        if self.process.returncode == 0:
            return [bytes.fromhex(b[2:]) for b in out.decode().splitlines() if len(b) > 1 and b.startswith('0x')]
        return None


class FullContext:
    def __init__(self, scope: RScope):
        self.scope: RScope = scope
        self.scope.name += f"_{random.randint(0, 1_000_000)}"
        self._idl_file: Optional[str] = None
        self._c_app: Optional[CAppContext] = None
        self._py_module: Optional[ModuleType] = None
        self._py_dir: Optional[TemporaryDirectory] = None

    def __del__(self):
        if self._py_dir is not None:
            self._py_dir.cleanup()

    def get_datatype(self, name: str):
        return getattr(self.py_module, name)

    @property
    def idl_file(self) -> str:
        if not self._idl_file:
            self._idl_file = generate_random_idl(self.scope)
        return self._idl_file

    @property
    def c_app(self) -> CAppContext:
        if self._c_app is None:
            self._c_app = CAppContext(
                *generate_c_application(self.idl_file, self.scope.name, [t.name for t in self.scope.topics])
            )
        return self._c_app

    @property
    def py_module(self) -> ModuleType:
        if self._py_module is None:
            self._py_module, self._py_dir = compile_idl(self.idl_file, self.scope.name)
        return self._py_module

    @property
    def py_dir(self) -> TemporaryDirectory:
        if self._py_dir is None:
            self._py_module, self._py_dir = compile_idl(self.idl_file, self.scope.name)
        return self._py_dir

    @property
    def topic_type_names(self) -> List[str]:
        return [topic.name for topic in self.scope.topics]

    def narrow_context_of(self, name: str) -> 'FullContext':
        for type in self.scope.topics:
            if type.name == name:
                dependants = type.depending()
                new_scope = RScope(
                    name=self.scope.name,
                    seed=0,
                    entities=list(reversed(dependants)) + [type],
                    topics=[type]
                )
                return FullContext(new_scope)
        raise KeyError(f"No such type '{name}' in scope.")

    def narrow_context_of_entity(self, type: REntity) -> 'FullContext':
        dependants = type.depending()
        new_scope = RScope(
            name=self.scope.name,
            seed=0,
            entities=list(reversed(dependants)) + [type],
            topics=[type]
        )
        return FullContext(new_scope)

    def reproducer(self, name: str) -> Tuple[zipfile.ZipFile, io.BytesIO]:
        zipb = io.BytesIO()
        zipf = zipfile.ZipFile(zipb, 'a', zipfile.ZIP_DEFLATED, False)
        zipf.writestr('reproducer/xtypes_dynamic_types.idl', self.idl_file)

        c_app_dir = (Path(__file__).resolve().parent / "c_app")
        for file in c_app_dir.glob('*'):
            if file.is_dir():
                continue
            with open(file, 'rb') as f:
                zipf.writestr(f"reproducer/{file.relative_to(c_app_dir)}", f.read())

        zipf.writestr('reproducer/xtypes_dynamic_index.c', self.c_app.xtypes_dynamic_index)

        zipf.writestr('reproducer/regenerate.sh', textwrap.dedent("""
            #!/bin/bash
            idlc -x final -l py xtypes_dynamic_types.idl
            cmake . -DIDL_FILE=xtypes_dynamic_types.idl
            make
        """).strip())

        with open(self.c_app.executable.name, 'rb') as f:
            zipf.writestr('reproducer/xtypes_sub', f.read())

        py_dir = Path(self.py_dir.name).resolve() / self.scope.name
        for file in py_dir.rglob('*'):
            if file.is_dir():
                continue
            with open(file, 'rb') as f:
                zipf.writestr(f"reproducer/{self.scope.name}/{file.relative_to(py_dir)}", f.read())

        with open(Path(__file__).resolve().parent / "reproducer.py.in", 'r') as f:
            txt = f.read().replace('{module}', self.scope.name).replace('{datatype}', name)
            zipf.writestr('reproducer/publisher.py', txt)

        with open(Path(__file__).resolve().parent / "value.py", 'rb') as f:
            zipf.writestr('reproducer/value.py', f.read())

        return zipf, zipb
