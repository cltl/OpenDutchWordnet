# -*- coding: utf-8 -*-
"""Setup file."""

from setuptools import setup
from setuptools import find_packages


setup(name='opendutchwordnet',
      version='1.3',
      description='Dutch version of Wordnet',
      author='Marten Postma',
      author_email='martenp@gmail.com',
      url='',
      license='MIT',
      packages=find_packages(exclude=['examples', 'documentation']),
      install_requires=[],
      classifiers=[
          'Intended Audience :: Developers',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',],
      keywords='wordnet',
      zip_safe=True)
