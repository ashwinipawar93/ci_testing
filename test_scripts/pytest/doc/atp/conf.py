# -*- coding: utf-8 -*-
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

TEST_DIRECTORY = "robot_axis_chain/test"

current_dir = os.path.dirname(os.path.realpath(__file__))
temp_path = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
tests_location = os.path.join(temp_path, TEST_DIRECTORY)
sys.path.append(os.path.join(os.path.dirname(__file__), tests_location))
print(sys.path)


# -- General configuration ------------------------------------------------
extensions = ['sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.imgmath',
    'sphinx.ext.autodoc',
    'sphinxcontrib.needs',
    'sphinxcontrib.test_reports',
    'sphinx.ext.autosectionlabel'
   ]

source_suffix = '.rst'
master_doc = 'index'
project = u'SOMANET Testing'
slug = re.sub(r'\W+', '-', project.lower())
copyright = u'2019, Synapticon'
author = u'Synapticon'
version = u'1.0'
release = u'1.0'
pygments_style = 'default'


# -- Options for HTML output ----------------------------------------------
html_theme = 'sphinx_rtd_theme'

# Output file base name for HTML help builder.
htmlhelp_basename = 'SOMANETTestDoc'
html_show_sourcelink = True
html_logo = "images/sncn.png"
htmlhelp_basename = slug

# -- Options for LaTeX output ---------------------------------------------

latex_documents = [
  ('index', '{0}.tex'.format(slug), project, author, 'manual'),
]

man_pages = [
    ('index', slug, project, [author], 1)
]

texinfo_documents = [
  ('index', slug, project, author, slug, project, 'Miscellaneous'),
]

latex_elements = {}

latex_documents = [
    (master_doc, 'SOMANETTestDoc.tex', u'SOMANET Test Documentation',
     u'Synapticon', 'manual'),
]
