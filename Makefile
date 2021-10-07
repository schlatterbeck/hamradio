# To use this Makefile, get a copy of my SF Release Tools
# git clone git://git.code.sf.net/p/sfreleasetools/code sfreleasetools
# And point the environment variable RELEASETOOLS to the checkout
PNAME=hamradio
ifeq (,${RELEASETOOLS})
    RELEASETOOLS=../releasetools
endif
LASTRELEASE:=$(shell $(RELEASETOOLS)/lastrelease -n)
PYF=adif.py bandplan.py cty.py dbimport.py dxcc.py eqsl.py __init__.py \
    lotw.py qslcard.py qth.py requester.py
VERSIONPY=$(PNAME)/Version.py
VERSION=$(VERSIONPY)
README=README.rst
SRC=Makefile setup.py $(PYF:%.py=$(PNAME)/%.py) \
    MANIFEST.in $(README) README.html

USERNAME=schlatterbeck
PROJECT=$(PNAME)
PACKAGE=$(PNAME)
CHANGES=changes
NOTES=notes

all: $(VERSION)

$(VERSION): $(SRC)

dist: all
	python setup.py sdist --formats=gztar,zip

clean:
	rm -f MANIFEST $(PNAME)/Version.py notes changes default.css    \
	      README.html README.aux README.dvi README.log README.out \
	      README.tex announce_pypi
	rm -rf dist build upload upload_homepage ReleaseNotes.txt

include $(RELEASETOOLS)/Makefile-sf
