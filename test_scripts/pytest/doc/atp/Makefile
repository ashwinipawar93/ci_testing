# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = python3 -msphinx
SPHINXPROJ    = BDCDriveStageTest
SOURCEDIR     = .
BUILDDIR      = _build
DOXYGEN_CONF  = Doxyfile

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help clean

clean:
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) clean

html:
	# Create the _build and _static directories if they don't exist
	@mkdir -p $(BUILDDIR)
	@mkdir -p _static
	# Build the doxygen documentation
	@doxygen $(DOXYGEN_CONF)
	# Build the Sphinx documentation
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O) -c .
