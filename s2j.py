#!/usr/bin/env python3

import getopt
import os
from typing import Dict, List, Any, Union

import sys
import os.path
import re
import json
from enum import Enum, auto
from subprocess import *
from string import *

from argparse import ArgumentParser
from collections import OrderedDict

debugmode = False
testmode = False


class State(Enum):
    SEEKING_TEMPLATE = auto()
    SEEKING_PATTERN = auto()
    SEEKING_MACROS = auto()
    WRITING_OUTPUT = auto()
    eof = auto()


class StateMachine(object):
    __state = State.SEEKING_TEMPLATE

    __instance = None

    @staticmethod
    def getInstance():
        """ Static access method. """
        if StateMachine.__instance is None:
            StateMachine()
        return StateMachine.__instance

    def __init__(self):
        """ Virtually private constructor. """
        if StateMachine.__instance is not None:
            raise Exception("This class is a Singleton!")
        else:
            StateMachine.__instance = self

    @property
    def state(self):
        return StateMachine.__state

    @state.setter
    def state(self, newstate):
        StateMachine.__state = newstate


class LineAttributes(Enum):
    """ class LineAttributes
    A simple collection of enumerations to return a hint attribute from the FileHandler class method readline()
    """
    WHITESPACE = auto()
    COMMENT = auto()
    PATTERN = auto()
    TEMPLATE = auto()
    MACROS = auto()
    GENERAL = auto()
    UNDEF = auto()


class FileHandler(object):

    def __init__(self, filename):
        if os.path.isfile(filename):
            self._f = open(filename, 'r')
        else:
            self._f = None

        self.__eof = False

        self.re_template = re.compile(r'(?:^file\s*?)((?:\S)+)\.template.*')
        #  self.re_pattern = re.compile(r'(?:\s*?pattern\s*?{)?(?:{)?(?:((\w+),?))')
        self.re_pattern = re.compile(r'(?:{)?(?:(\w+)\s*[,}]\s*)')
        self.re_macros = re.compile(r'(?:\s*{\s*)?(?:(?:\s*)([:/{}\-\w]*)[\"]?(?:[\s,}]*))')

    @property
    def eof(self):
        return self.__eof

    def readline(self):
        line = None
        attr = LineAttributes.UNDEF
        if self._f is not None:
            if not self._f.closed:
                line = self._f.readline()
                if len(line) == 0:
                    self.__eof = True
                    self._f.close()
                else:
                    attr = LineAttributes.GENERAL
                    line = line.strip()
                    if line.startswith('#'):
                        attr = LineAttributes.COMMENT
                    elif line.startswith('{') and line.endswith('}'):
                        attr = LineAttributes.MACROS
        return line, attr

    def get_next_template(self):
        _template_name = None
        while (not self.eof) and (_template_name is None):
            line, attr = self.readline()
            if not self.eof:
                #  print('get_next_template(): Line => {0}'.format(line))
                res = self.re_template.search(line)

                if (res is not None) and (res.lastindex > 0):
                    _template_name = res.group(1)
                    # print('get_next_template(): match found')
            # print('get_next_template(): => {0}'.format(_template_name))
        return self.eof, _template_name

    def get_pattern(self):
        _pattern = []
        while (not self.eof) and (len(_pattern) == 0):
            line, attr = self.readline()
            if not self.eof:
                res = self.re_pattern.findall(line)

                if (res is not None) and (len(res) > 0):
                    for i in range(len(res)):
                        _pattern.append(res[i])
                    break

            # print('get_pattern(): => {0}'.format(_pattern))
        return _pattern

    def get_macros(self):
        end_of_block = False
        _macros_table = []
        instance = 0
        while not end_of_block:
            line, attr = self.readline()
            if not self.eof:
                # Split the line, removing enclosing '{}' and delimiting on ','
                #  res = self.re_macros.findall(line)
                #  Remove leading and trailing whitespace

                # The first and last character of a valid macro line should be '{'
                if attr == LineAttributes.MACROS:
                    # Remove the leading and trailing braces
                    line = line.strip('{}')

                    # Split the line into discrete arguments delimited by ','
                    res = line.split(',')

                    _macros = []
                    if (res is not None) and (len(res) > 0):
                        for i in range(len(res)):
                            _macros.append(res[i].strip(' \"'))  # Removing enclosing whitespace and quotes
                        _macros_table.append(_macros)

                elif line.startswith('}'):  # terminating macro block
                    end_of_block = True
            else:  # EOF
                end_of_block = True

            # print('get_macros(): => {0}'.format(_macros))
        return _macros_table


class Device(object):
    __device_count = 0

    def __init__(self, template_id):
        super().__init__()
        self.__template = template_id
        self.__pattern = []
        self.__macros = []
        self.__instances = {'dev': self.__template, 'instances': []}
        Device.__device_count += 1

    def __repr__(self):
        print('Device.__repr__(): {0}'.format(self.__template))
        return json.dumps({'dev': {'template': self.__template, 'pattern': self.__pattern, 'macros': self.__macros}})

    @staticmethod
    def count():
        return Device.__device_count

    @staticmethod
    def last_index():
        return Device.__device_count - 1

    @property
    def template(self):
        return self.__template

    @template.setter
    def template(self, name):
        self.__template = name

    @property
    def pattern(self):
        return self.__pattern

    @pattern.setter
    def pattern(self, pattern_list):
        self.__pattern = pattern_list

    @property
    def macros(self):
        return self.__macros

    @macros.setter
    def macros(self, macro_list):
        self.__macros = macro_list

    def set_macros_list_list(self, macros_list_list):
        self.__macros = macros_list_list

    @property
    def instances(self):
        return self.__instances

    def associate(self):
        arginst = {}

        for macroline in self.__macros:
            # Ensure that the number of macro args equals the number of pattern args
            if len(macroline) == len(self.__pattern):
                # Iterate through the macros and associate them with the pattern args
                i = 0
                arginst.clear()
                for entry in macroline:
                    arginst[self.__pattern[i]] = macroline[i]
                    i += 1
                self.__instances['instances'].append(arginst.copy())

    def write_json(self):
        j = json.dumps(self.__instances)
        print('Writing JSON file for {0}'.format(self.__template))
        print(j)


class Substitutions(object):
    def __init__(self, name):
        super().__init__()
        self._name = name
        self._devices = []

    def add_device(self, dev):
        self._devices.append(dev)

    def to_json(self, fn):
        with open(fn, 'w') as f:
            output_object = {'IOC': self._name, 'devices': self.to_obj()}
            json.dump(output_object, f)
            f.close()

    def to_obj(self):
        devlist = []
        for dev in self._devices:
            dev.associate()
            devlist.append(dev.instances)
        return devlist


def error_exit(errmsgs):
    usage = "usage: subst2json -i <ioc_name> [-f <filename>] <-t test mode> <-d debug mode>"
    print(usage)
    if isinstance(errmsgs, list):
        for msg in errmsgs:
            print(msg)


def main():
    global debugmode
    global testmode

    usage = "usage: %(prog)s [-f filename] <-t test mode> <-d debug mode>"
    errmsgs = []

    parser = ArgumentParser(usage=usage)
    parser.add_argument('-f', '--file', nargs='+')
    parser.add_argument('-o', '--outputfile', nargs='+')
    parser.add_argument('-i', '--ioc', nargs='+')
    parser.add_argument('-t', '--test', action='store_true')
    parser.add_argument('-d', '--debug', action='store_true')

    args = parser.parse_args()
    if args.debug:
        print("Debug mode on")
        debugmode = True
    if args.test:
        print("Test mode on - result will be directed to stdout")
        testmode = True
    if args.file:
        filename = args.file[0]
    else:
        filename = None
        errmsgs.append('Must Specify substitutions file name (-f <filename>')

    if args.outputfile:
        outputfile = args.outputfile[0]
    else:
        outputfile = None
    if args.ioc:
        iocname = args.ioc[0]
    else:
        iocname = None
        errmsgs.append('Must Specify IOC name (-i <name>)')

    if len(errmsgs) > 0:
        error_exit(errmsgs)
    else:  # All good
        devices = []

        if filename is not None:
            print('Filename: {0}'.format(filename))
            fhandler = FileHandler(filename)
            if fhandler is not None:
                _template = None
                _pattern = []
                _macros_table = []
                _substitutions = Substitutions(iocname)

                # First thing - look for a template instantiation
                StateMachine.state = State.SEEKING_TEMPLATE
                while True:
                    if StateMachine.state == State.SEEKING_TEMPLATE:
                        eof, _template = fhandler.get_next_template()
                        if (not eof) and (_template is not None):
                            device = Device(_template)
                            devices.append(device)
                            _substitutions.add_device(device)
                            StateMachine.state = State.SEEKING_PATTERN
                        else:
                            StateMachine.state = State.eof

                    elif StateMachine.state == State.SEEKING_PATTERN:
                        _pattern = fhandler.get_pattern()
                        devices[Device.last_index()].pattern = _pattern
                        StateMachine.state = State.SEEKING_MACROS

                    elif StateMachine.state == State.SEEKING_MACROS:
                        _macros_table = fhandler.get_macros()
                        if len(_macros_table) > 0:
                            devices[Device.last_index()].set_macros_list_list(_macros_table)
                            # devices[Device.last_index()].macros.append(_macros_table)
                            # devices[Device.last_index()].write_json()
                        StateMachine.state = State.SEEKING_TEMPLATE

                    elif StateMachine.state == State.eof:
                        print('=== eof ===')
                        print('Device templates found: {0}'.format(Device.count()))
                        if outputfile is not None:
                            _substitutions.to_json(outputfile)

                        break


if __name__ == '__main__':

    main()
