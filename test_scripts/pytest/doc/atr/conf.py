# -*- coding: utf-8 -*-
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

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
release = u''
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
    (master_doc, 'SOMANETTestDoc.tex', u'SOMANET Acceptance test report',
     u'Synapticon', 'manual'),
]

latex_docclass = {
    'howto': 'article',
    'manual': 'article',
}

latex_elements = {
    'papersize': r'a4paper',
    'pointsize': r'10pt',
    'pxunit': r'0.75bp',
    'preamble': r'''
        \usepackage{charter}
        \usepackage[defaultsans]{lato}
        \usepackage{inconsolata}
        \usepackage{colortbl}
        \protected\def\sphinxstyletheadfamily {\cellcolor{green}\sffamily}
    ''',
    'fncychap': r'\usepackage[Conny]{fncychap}',
    # Disables table of content
    'tableofcontents':r'',
    # Remove empty page between table of content and content
    'extraclassoptions': 'openany',
    # This is needed to always have the title on the top
    'maketitle':r'''
        \begin{center}
            \Large\textbf{SOMANET Test acceptance report}\\
            \large\textbf{Test}\\
            \large\textit{\today}
        \end{center}
    ''',
}