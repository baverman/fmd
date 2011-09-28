from setuptools import setup, find_packages
from setuptools.command import easy_install

def install_script(self, dist, script_name, script_text, dev_path=None):
    script_text = easy_install.get_script_header(script_text) + (
        ''.join(script_text.splitlines(True)[1:]))

    self.write_script(script_name, script_text, 'b')

easy_install.easy_install.install_script = install_script

setup(
    name     = 'fmd',
    version  = '0.3',
    author   = 'Anton Bobrov',
    author_email = 'bobrov@vl.ru',
    description = 'Minimalist file manager',
    #long_description = open('README.rst').read().replace('https', 'http'),
    zip_safe   = False,
    packages = find_packages(exclude=('tests', )),
    scripts = ['bin/fmd'],
    include_package_data = True,
    url = 'http://github.com/baverman/fmd',
    classifiers = [
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "Natural Language :: English",
    ],
)
