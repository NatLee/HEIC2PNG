import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='HEIC2PNG',
    author='Nat Lee',
    author_email='natlee.work@gmail.com',
    description='Convert format of HEIC image to PNG by using Python.',
    keywords='HEIC, PNG, converter, image',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/natlee/HEIC2PNG',
    project_urls={
        'Documentation': 'https://github.com/natlee/HEIC2PNG',
        'Bug Reports': 'https://github.com/natlee/HEIC2PNG/issues',
        'Source Code': 'https://github.com/natlee/HEIC2PNG'
    },
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    classifiers=[
        # see https://pypi.org/classifiers/
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=[
        'pillow',
        'pillow-heif',
        'numpy'
    ],
    extras_require={
        'dev': ['check-manifest'],
        # 'test': ['coverage'],
    },
    entry_points={
        'console_scripts': [
            'heic2png=heic2png.cli:main'
        ]
    }
)
