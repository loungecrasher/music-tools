"""
Setup script for music-tools-common package.
"""
from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="music-tools-common",
    version="1.0.0",
    author="Music Tools Team",
    author_email="dev@musictools.example.com",
    description="Shared library for Music Tools ecosystem",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/musictools/music-tools-common",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Multimedia :: Sound/Audio",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=9.0.0",
            "pytest-cov>=6.0.0",
            "black>=25.1.0",
            "flake8>=7.1.0",
            "mypy>=1.18.0",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
