# **pps2j**

A utility script which reads an EPICS substitution file and converts it to JSON 
format.

Having originally adopted a hand-crafted state-machine model (`s2j.py`), which scanned each line of the file,
a new technique was tried using the _`pyparsing`_ module (`pps2j.py`).  This method proved more reliable and maintainable
than the original. The code size and complexity is also much reduced.

The project is based on Python 3, ussing Pipenv. To establish a development/run-time environment
simply clone the repository, then enter the new directory and type **`pipenv shell`**.

The script presently takes no arguments and the substitution file is hard coded and expected to be in the working directory.
This will be augmented to incorporate an argument parser to allow the input file to be specified and to facilitate selection of 
various output formats.
---   
Ian Gillingham, 31 October 2019

