Ham-Radio scripts
=================

:Author: Ralf Schlatterbeck <rsc@runtux.com>

.. |--| unicode:: U+2013   .. en dash

Note that the binaries currently installed with the package work only in
conjunction with my logging database based on Roundup_.

The software in the modules of this python package centers around
handling of QSO logging data, retrieval of electronic QSLs from various
electronic QSL services (currently Logbook of the World LOTW_ and eQSL_)
and interfacing to my logging database written with the bugtracking
framework Roundup_. The logging database is part of my `time-track-tool`_
several packages that build on Roundup_, among them a time tracking tool
and a QSO logger.

.. _Roundup: https://sourceforge.net/projects/roundup/
.. _eQSL: https://www.eqsl.cc/
.. _LOTW: https://lotw.arrl.org/
.. _`time-track-tool`: https://github.com/time-track-tool/time-track-tool

The adif module is used to parse ADIF files.
Basic usage is at the end of the file, it can be called to do a
round-trip of an ADIF file (reading it in and writing it out).

The bandplan module implements a definition of the ham radio bands and
corresponding frequencies for a country. Currently only Austria is
implemented, it should be easy to add other countries. I'm mainly using
it for looking up the corresponding band for a given frequency (e.g.
when receiving data from WSJTX_ which includes only a frequency not the
band).

.. _WSJTX: https://physics.princeton.edu/pulsar/k1jt/wsjtx.html

The dbimport module is used for communicating with my time-track-tool_
logging database via its `REST API`_. It makes use of the requester
module which factors out some of the common `REST API`_ calls.

.. _`REST API`: https://roundup.sourceforge.io/docs/rest.html

The dxcc module is used to parse the `official DXCC list`_ from the ARRL
homepage and do basic callsign lookups via the prefix list given in that
document. Note that the prefix list often does not identify the DXCC
entity unambiguously or even gets the DXCC entity wrong in some cases.

.. _`official DXCC list`:
    http://www.arrl.org/files/file/DXCC/2019_Current_Deleted(3).txt

The cty module is used to extract information from the well known
``CTY.DAT`` `country database`_ by Jim Reisert, AD1C. This database is
much better at matching callsign prefixes to DXCC country, CQ-Zone and
ITU-Zone information than the information in the ARRL list used by the
dxcc module above. The module can be called with a set of callsigns to
look up, the code at the end of the module should give you an idea on
how to use it. Currently only DXCC lookup is implemented, CQ-Zone and
ITU-Zone info may follow at some point.

.. _`country database`: https://www.country-files.com

The eqsl and lotw modules are used for retrieving QSO and QSL log
information from Logbook of the World LOTW_ and eQSL_. Note that the
eqsl package also supports retrieving the QSL "cards". You should have a
`silver membership with eQSL`_ for using that feature. You should get a
quick idea how to use these modules from looking into the dbimport
module. Note that both, eqsl and lotw use the requester module.

.. _`silver membership with eQSL`: http://www.eqsl.cc/qslcard/GeteQSL.txt

The qth module implements conversion from GPS coordinates to Maidenhead
locator. It has a doctest in the Maidenhead_Locator class that should
give you an idea on how to use it. It does support extended locators
beyond length 6 used by some VHF groups.

Changes
-------

Version 0.4: Fix setup.py install_requires

Version 0.2-0.3: Updates to documentation and setup

Version 0.1: Initial release

Note that this project is quite old |--| I'm using it for myself so far
and the first release just now should not scare you too much.
