from setuptools import setup, find_packages
with open('requirements.txt') as f:
    data = f.read()
requirements = data.split()

setup(
    name='bard',
    version='0.1.1',
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
        changewithin=changewithin.cli:cli_generate_report
    ''',
    package_data={
        'changewithin': [
            "changewithin/templates/text_template.txt",
            "changewithin/templates/html_template.html",
            "changewithin/schema.sql"
        ]
    }
)
