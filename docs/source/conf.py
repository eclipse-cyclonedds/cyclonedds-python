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


# -- Allow documentation building without loading libraries -------------------

os.environ['CYCLONEDDS_PYTHON_NO_IMPORT_LIBS'] = "1"
typing.TYPE_CHECKING = True


# -- Configuration file for the Sphinx documentation builder ------------------
