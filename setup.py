from setuptools import setup, find_packages

setup(
    name     = 'fmd',
    version  = '0.3',
    author   = 'Anton Bobrov',
    author_email = 'bobrov@vl.ru',
    description = 'Minimalist file manager',
    #long_description = open('README.rst').read().replace('https', 'http'),
    zip_safe   = False,
    packages = find_packages(exclude=('tests', )),
    include_package_data = True,
    url = 'http://github.com/baverman/fmd',
    entry_points = {
        'gui_scripts': [
            'fmd = fmd.run:run',
        ]
    },
    classifiers = [
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "Natural Language :: English",
    ],
)
