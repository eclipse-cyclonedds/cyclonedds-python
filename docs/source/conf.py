# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import typing

os.environ['CDDS_NO_IMPORT_LIBS'] = "1"
typing.TYPE_CHECKING = True

# -- Project information -----------------------------------------------------

project = 'cyclonedds-py'
copyright = '2020, Thijs Miedema, ADLINK Technology Inc.'
author = 'Thijs Miedema'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.extlinks',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    "sphinx.ext.viewcode",
    'sphinx_markdown_builder'
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