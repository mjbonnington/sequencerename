# -*- coding: utf-8 -*-

name = 'ic_seqrename'

version = '0.2.7'

description = 'Sequence Rename Tool'

authors = ['mjbonnington']

requires = [
    'ic_ui-2+', 
    'ic_shared', 
]

build_requires = [
    'rezlib', 
]

build_command = 'python -m build {install}'


def commands():
    env.PATH.append("{root}")
    env.PYTHONPATH.append('{root}')
    env.IC_ICONPATH.append('{root}/icons')
    alias("sqrn", "python {root}/sequencerename.py")
