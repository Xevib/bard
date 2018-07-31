from setuptools import setup, find_packages
with open('requirements.txt') as f:
    data = f.read()
requirements = data.split()

setup(
    name='bard',
    version='0.2.0',
    packages=find_packages(),
    url='https://github.com/Xevib/bard',
    license='MIT',
    author='Xavier Barnada',
    author_email='xbarnada@gmail.com',
    description='Tool control the diffs of OSM',
    install_requires=requirements,
    include_package_data=True,
    entry_points='''
        [console_scripts]
        bard=bard.cli:cli_generate_report
    ''',
    package_data={
        'bard': [
            "bard/templates/text_template.txt",
            "bard/templates/html_template.html",
            "bard/schema.sql"
        ]
    }
)
