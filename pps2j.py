#!/usr/bin/env python3
"""EPICS Substitutions file grammar parser and tokeniser.
pps2j.py:
=========
This module has been written to parse any standard EPICS substitution file, generating a Python object which can then be
used in other applications, such as determining the configuration of an IOC.  The motivation to designing this package
was to determine the amount of rack space required to accommodate all the instrumentation for a particular IOC.

The 'pyparsing' module has been used extensively, which is well documented and supported.

Ian Gillingham, October 2019

"""
#
# EPICS Substitution file BNF Grammar
#
# substitutions         ::= substitutions_block+
# substitutions_block   ::= "file", filepath, "{", pattern, instance+, "}"
# pattern               ::= "pattern", "{", ((arg_name, ",")|arg_name)+, "}"
# instance              ::= "{", ((arg_value, ",")|arg_value)+, "}"
#


from pyparsing import (Suppress, removeQuotes, quotedString, originalTextFor,
                       OneOrMore, Word, printables, nestedExpr, delimitedList,
                       ParseException, alphanums, SkipTo, Group, restOfLine, CharsNotIn, lineEnd, Keyword)

import pprint

#  Pre-define some grammar components
l_brace, r_brace = map(Suppress, "{}")
quotedString.addParseAction(removeQuotes)


def substitutions_bnf():
    """ substitutions_bnf()
    Defines the complete aggregated parser grammar for a whole substitutions file
    All template file instances are included as an iterable group of substfile_bnf.

    :return: PyParser BNF Expression
    """
    expr = Group(OneOrMore(substfile_bnf()))
    return expr


def substfile_bnf():
    """ substfile_bnf()
    Defines the parser grammar for each template block within the given substitutions file

    :return: PyParser BNF Expression
    """
    expr = Group(OneOrMore(Keyword('file') + originalTextFor(Word(alphanums+'_$()/') + '.template')
           + l_brace
           + pattern_bnf()
           + OneOrMore(instance_bnf())
           + r_brace))
    # Defines comments
    expr.ignore('#' + restOfLine)

    return expr


def pattern_bnf():
    """ pattern_bnf()
    Defines the parser grammar for a pattern definition block

    :return: PyParser BNF Expression
    """
    macro = OneOrMore(Word(printables, excludeChars="{},"))
    expr = Keyword('pattern') + l_brace + Group(delimitedList(macro)) + r_brace
    return expr


def instance_bnf():
    """ instance_bnf()
    Defines the parser grammar for each instance associated with a pattern.

    :return: PyParser BNF Expression
    """
    arg = OneOrMore(Word(printables, excludeChars='{},').setResultsName('macro*', listAllMatches=True))
    expr = l_brace + Group(delimitedList(arg)) + r_brace
    return expr


def main(filename):
    """ main()
    Encapsulation of the mainline code, to keep it tin its own namespace scope
    (prevents polluting the module scope)
    """
    pp = pprint.PrettyPrinter(2)
    tokens = None
    try:
        bnf = substfile_bnf()
        tokens = bnf.parseFile(filename)
        pp.pprint(tokens.asList())
        # pp.pprint(tokens.asDict())

    except ParseException as err:
        print(err.line)
        print(" " * (err.column - 1) + "^")
        print(err)

    print()
    return tokens


if __name__ == '__main__':
    """
    For testing purposes, the input filename is statically declared.
    This will need to be replaced with argument parsing, so the user can specify the substitutions file and
    output format.
    """
    fname = 'FE02I-CS-IOC-01.substitutions'

    substitutions = main(fname)
