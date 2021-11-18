# -*- coding: utf-8 -*-

name = 'ic_seqrename'

version = '0.1.4'

description = 'Sequence Rename Tool'

variants = [['python-2.7']]

requires = ['ic_ui', 'ic_shared']

authors = ['mjbonnington']

build_command = 'python {root}/build.py {install}'


def commands():
    env.PYTHONPATH.append('{root}')
    env.IC_ICONPATH.append('{root}/icons')
