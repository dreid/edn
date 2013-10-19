# edn

[![Build Status](https://travis-ci.org/dreid/edn.png?branch=master)](https://travis-ci.org/dreid/edn)
[![Coverage Status](https://coveralls.io/repos/dreid/edn/badge.png)](https://coveralls.io/r/dreid/edn)

Python implementation of [edn](https://github.com/edn-format/edn).

## Features and points of interest

* Gives you complete control over how edn's types are mapped into Python.  If
  you don't want symbols and keywords to be turned into strings, this library
  is for you.

* Uses immutable types by default, allowing the full range of edn code to be
  supported.

* Actually extensible, so your own objects and types can be encoded and
  decoded in edn.

* Gets unicode support right.

* Fully unit tested.

* Parser implement with [Parsley](https://github.com/python-parsley/parsley),
  which makes the code nice and succinct.
