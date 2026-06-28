from setuptools import setup, find_packages

setup(
    name="animeiat-cli",
    packages=find_packages(include=["src", "src.*"]),
    extras_require={
        "dev": [
            "pytest",
            "pytest-asyncio",
            "respx",
        ],
    },
)
