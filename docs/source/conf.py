# -- Configuration file for the Sphinx documentation builder ------------------

import os
import typing


# -- Prevent circular imports in Sphinx ---------------------------------------

import sphinx.builders.html
import sphinx.builders.latex
import sphinx.builders.texinfo
import sphinx.builders.text
import sphinx.ext.autodoc


# -- Project information ------------------------------------------------------

project = 'Eclipse Cyclone DDS Python'
copyright = '2020, Eclipse Cyclone DDS Python Committers'
author = 'Eclipse Cyclone DDS Python Committers'

extlinks = {
    "c_repo":           ("https://github.com/eclipse-cyclonedds/cyclonedds/", None),
    "py_repo":          ("https://github.com/eclipse-cyclonedds/cyclonedds-python/", None),
    "venv":             ("https://docs.python.org/3/tutorial/venv.html", None),
    "poetry":           ("https://python-poetry.org/", None),
    "pipenv":           ("https://pipenv.pypa.io/en/latest/", None),
    "pyenv":            ("https://github.com/pyenv/pyenv", None),
    "py_installing":    ("https://docs.python.org/3/installing/index.html", None)
}


# -- General configuration ----------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.extlinks',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    "sphinx.ext.viewcode"
]
autodoc_mock_imports=["ctypes.CDLL", "ddspy"]
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'

intersphinx_mapping = {'python': ('https://docs.python.org/3', None)}

napoleon_google_docstring = False
napoleon_numpy_docstring = True

templates_path = ['templates']
html_static_path = ['static']

exclude_patterns = ['Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
pygments_style = 'friendly'

# -- Configuration file for the Sphinx documentation builder ------------------
