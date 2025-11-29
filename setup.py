#!/usr/bin/env python3
"""
Setup script for GitHub AI Agent v2.0
Run with: python setup.py install
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="github-ai-agent",
    version="2.0.0",
    author="Your Name",
    description="Professional AI Agent for GitHub with code execution and Git integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/t2m19102001/github-ai-agent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyGithub>=2.2.0",
        "requests>=2.32.0",
        "python-dotenv>=1.0.1",
        "Flask>=3.0.0",
        "flask-cors>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "github-ai-agent=main:main",
            "github-ai-web=run_web:main",
        ]
    },
)
