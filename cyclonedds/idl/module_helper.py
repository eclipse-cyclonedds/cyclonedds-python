from typing import List
import importlib
import pkgutil
import sys


def get_idl_entities(package_name: str) -> List[str]:
    """ Import all files in a module and make types resolve properly for all idl types"""
    package = sys.modules[package_name]

    for loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
        submodule = importlib.import_module(package_name + '.' + name)
        setattr(package, name, submodule if is_pkg else getattr(submodule, name))

    return [
        name for __loader, name, __is_pkg in pkgutil.walk_packages(package.__path__)
    ]
