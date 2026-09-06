# ponytail: clean minimal setuptools cythonize configuration
import os
import numpy
from setuptools import setup, Extension
from Cython.Build import cythonize

sources_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BUILD_SOURCES")

extensions = [
    Extension(
        "detector",
        sources=[os.path.join(sources_dir, "detector.pyx")],
        include_dirs=[numpy.get_include()],
    ),
    Extension(
        "recognizer",
        sources=[os.path.join(sources_dir, "recognizer.pyx")],
        include_dirs=[numpy.get_include()],
    ),
    Extension(
        "pipeline",
        sources=[os.path.join(sources_dir, "pipeline.pyx")],
        include_dirs=[numpy.get_include()],
    ),
    Extension(
        "video_scanner",
        sources=[os.path.join(sources_dir, "video_scanner.pyx")],
        include_dirs=[numpy.get_include()],
    ),
]

setup(
    name="FaceSeekerEngine",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": "3",
            "embedsignature": False,
            "boundscheck": False,
            "wraparound": False,
        },
    ),
)