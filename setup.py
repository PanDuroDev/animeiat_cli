from setuptools import setup, find_packages

try:
    from Cython.Build import cythonize
    ext_modules = cythonize("anime_cli.py", compiler_directives={"language_level": "3"})
except (ImportError, OSError):
    ext_modules = []

setup(
    name="animeiat-cli",
    ext_modules=ext_modules,
    packages=find_packages(include=["src", "src.*"]),
    extras_require={
        "dev": [
            "pytest",
            "pytest-asyncio",
            "respx",
        ],
    },
)
