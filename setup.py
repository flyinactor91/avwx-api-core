"""
avwx_api_core Package Setup
"""

from setuptools import setup, find_packages


setup(
    name="avwx-api-core",
    version="0.1.0",
    description="Core components for AVWX APIs",
    url="https://github.com/avwx-rest/avwx-api-core",
    author="Michael duPont",
    author_email="michael@mdupont.com",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    python_requires=">= 3.6",
    install_requires=[
        'dataclasses>=0.7;python_version<"3.7"',
        "dicttoxml~=1.7",
        "dnspython~=2.0",
        "motor~=2.1",
        "pyyaml~=5.3",
        "quart>=0.13",
        "quart-openapi>=1.6",
        "voluptuous~=0.11",
    ],
    packages=find_packages(),
    tests_require=["pytest-asyncio~=0.14"],
)
