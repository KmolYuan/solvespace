# -*- coding: utf-8 -*-

"""Compile the Cython libraries of Python-Solvespace."""

__author__ = "Yuan Chang"
__copyright__ = "Copyright (C) 2016-2019"
__license__ = "GPLv3+"
__email__ = "pyslvs@gmail.com"

import sys
from os import walk
from os.path import dirname, isdir, join as pth_join
import re
import codecs
from setuptools import setup, Extension, find_packages
from setuptools.command.build_ext import build_ext
from setuptools.command.sdist import sdist
from distutils import file_util, dir_util
from platform import system

m_path = 'python_solvespace'
include_path = pth_join(m_path, 'include')
src_path = pth_join(m_path, 'src')
platform_path = pth_join(src_path, 'platform')
mimalloc_path = pth_join(m_path, 'extlib', 'mimalloc')
mimalloc_include_path = pth_join(mimalloc_path, 'include')
mimalloc_src_path = pth_join(mimalloc_path, 'src')


def write(doc, *parts):
    with codecs.open(pth_join(*parts), 'w') as f:
        f.write(doc)


def read(*parts):
    with codecs.open(pth_join(*parts), 'r') as f:
        return f.read()


def find_version(*file_paths):
    m = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", read(*file_paths), re.M)
    if m:
        return m.group(1)
    raise RuntimeError("Unable to find version string.")


macros = [
    ('M_PI', 'PI'),
    ('_USE_MATH_DEFINES', None),
    ('ISOLATION_AWARE_ENABLED', None),
    ('LIBRARY', None),
    ('EXPORT_DLL', None),
    ('_CRT_SECURE_NO_WARNINGS', None),
]
compile_args = [
    '-O3',
    '-Wno-cpp',
    '-g',
    '-Wno-write-strings',
    '-fpermissive',
    '-fPIC',
    '-std=c++17',
]
link_args = ['-static-libgcc', '-static-libstdc++',
             '-Wl,-Bstatic,--whole-archive',
             '-lwinpthread',
             '-lbcrypt',
             '-lpsapi',
             '-Wl,--no-whole-archive']
sources = [
    pth_join(m_path, 'slvs.pyx'),
    pth_join(src_path, 'util.cpp'),
    pth_join(src_path, 'entity.cpp'),
    pth_join(src_path, 'expr.cpp'),
    pth_join(src_path, 'constraint.cpp'),
    pth_join(src_path, 'constrainteq.cpp'),
    pth_join(src_path, 'system.cpp'),
    pth_join(src_path, 'lib.cpp'),
    pth_join(platform_path, 'platform.cpp'),
    # MiMalloc
    pth_join(mimalloc_src_path, 'stats.c'),
    pth_join(mimalloc_src_path, 'random.c'),
    pth_join(mimalloc_src_path, 'os.c'),
    pth_join(mimalloc_src_path, 'arena.c'),
    pth_join(mimalloc_src_path, 'region.c'),
    pth_join(mimalloc_src_path, 'segment.c'),
    pth_join(mimalloc_src_path, 'page.c'),
    pth_join(mimalloc_src_path, 'alloc.c'),
    pth_join(mimalloc_src_path, 'alloc-aligned.c'),
    pth_join(mimalloc_src_path, 'alloc-posix.c'),
    pth_join(mimalloc_src_path, 'heap.c'),
    pth_join(mimalloc_src_path, 'options.c'),
    pth_join(mimalloc_src_path, 'init.c'),
]
if {'sdist', 'bdist'} & set(sys.argv):
    sources.append(pth_join(platform_path, 'platform.cpp'))
elif system() == 'Windows':
    # Disable format warning
    compile_args.append('-Wno-format')
    # Solvespace arguments
    macros.append(('WIN32', None))
    if sys.version_info < (3, 7):
        macros.append(('_hypot', 'hypot'))
else:
    macros.append(('UNIX_DATADIR', '"solvespace"'))
compiler_directives = {'binding': True, 'cdivision': True}


def copy_source(dry_run):
    dir_util.copy_tree(pth_join('..', 'include'), include_path, dry_run=dry_run)
    dir_util.copy_tree(pth_join('..', 'extlib', 'mimalloc', 'include'), include_path, dry_run=dry_run)
    dir_util.mkpath(src_path)
    dir_util.mkpath(mimalloc_src_path)
    for path in (pth_join('..', 'src'), pth_join('..', 'extlib', 'mimalloc', 'src')):
        for root, _, files in walk(path):
            for f in files:
                if not (f.endswith('.h') or f.endswith('.c')):
                    continue
                f = pth_join(root, f)
                f_new = f.replace('..', m_path)
                if not isdir(dirname(f_new)):
                    dir_util.mkpath(dirname(f_new))
                file_util.copy_file(f, f_new, dry_run=dry_run)
    for f in sources[1:]:
        file_util.copy_file(f.replace(m_path, '..'), f, dry_run=dry_run)
    # Create an empty header
    open(pth_join(platform_path, 'config.h'), 'a').close()


class Build(build_ext):
    def build_extensions(self):
        compiler = self.compiler.compiler_type
        for e in self.extensions:
            e.cython_directives = compiler_directives
            if compiler in {'mingw32', 'unix'}:
                e.define_macros = macros
                e.extra_compile_args = compile_args
                if compiler == 'mingw32':
                    e.extra_link_args = link_args
            elif compiler == 'msvc':
                e.define_macros = macros[1:]
                e.libraries = ['shell32']
                e.extra_compile_args = ['/O2']
        super(Build, self).build_extensions()

    def run(self):
        has_src = isdir(include_path) and isdir(src_path) and isdir(mimalloc_path)
        if not has_src:
            copy_source(self.dry_run)
        super(Build, self).run()
        if not has_src:
            dir_util.remove_tree(include_path, dry_run=self.dry_run)
            dir_util.remove_tree(src_path, dry_run=self.dry_run)
            dir_util.remove_tree(mimalloc_path, dry_run=self.dry_run)


class PackSource(sdist):
    def run(self):
        copy_source(self.dry_run)
        super(PackSource, self).run()
        if not self.keep_temp:
            dir_util.remove_tree(include_path, dry_run=self.dry_run)
            dir_util.remove_tree(src_path, dry_run=self.dry_run)
            dir_util.remove_tree(mimalloc_path, dry_run=self.dry_run)


setup(
    name="python_solvespace",
    version=find_version(m_path, '__init__.py'),
    author=__author__,
    author_email=__email__,
    description="Python library of Solvespace.",
    long_description=read("README.md"),
    long_description_content_type='text/markdown',
    url="https://github.com/KmolYuan/solvespace",
    packages=find_packages(exclude=('tests',)),
    package_data={'': ["*.pyi", "*.pxd"], 'python_solvespace': ['py.typed']},
    ext_modules=[Extension(
        "python_solvespace.slvs",
        sources,
        language="c++",
        include_dirs=[include_path, src_path, mimalloc_include_path, mimalloc_src_path]
    )],
    cmdclass={'build_ext': Build, 'sdist': PackSource},
    zip_safe=False,
    python_requires=">=3.6",
    install_requires=read('requirements.txt').splitlines(),
    test_suite='tests',
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Cython",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ]
)
