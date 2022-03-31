"""
avwx_api_core Package Setup
"""

from setuptools import setup, find_namespace_packages


setup(
    name="avwx-api-core",
    version="0.1.0",
    description="Core components for AVWX APIs",
    url="https://github.com/avwx-rest/avwx-api-core",
    author="Michael duPont",
    author_email="michael@dupont.dev",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">= 3.10",
    install_requires=[
        "dicttoxml @ git+https://github.com/avwx-rest/dicttoxml",
        "avwx-engine>=1.7",
        "dnspython~=2.2",
        "motor~=2.5",
        "pyyaml~=6.0",
        "quart~=0.17",
        "quart-openapi>=1.7.1",
        "voluptuous~=0.13",
    ],
    packages=find_namespace_packages(include=["avwx_api_core*"]),
    package_data={"avwx_api_core.data": ["navaids.json"]},
    tests_require=["pytest-asyncio~=0.18"],
)
