============
spiderflunky
============

Spiderflunky is a proof-of-concept JS static analysis tool based on Mozilla's
SpiderMonkey runtime. It uses SpiderMonkey's ``Reflect.parse`` to do the
parsing and then takes it from there with a flattened-out form of alias
analysis. Ultimately, it will develop into a JS plugin for DXR
(http://dxr.allizom.org/).


Getting Started
===============

Build SpiderMonkey's ``js`` executable. Check out mozilla-central, and then
build the interpreter::

    hg clone https://hg.mozilla.org/mozilla-central/ mozilla-central
    cd mozilla-central
    cd js/src
    autoconf213  # must be 2.13
    ./configure
    make
    sudo cp dist/bin/js /usr/local/bin/

All you can really do so far is run the tests. Enjoy doing that! ::

    python setup.py test
