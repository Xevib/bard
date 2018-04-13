# -*- coding: utf-8 -*-
import click
from raven import Client
from bard import Bard


@click.group()
def bard():
    pass


@bard.command()
@click.option('--host', default=None)
@click.option('--db', default=None)
@click.option('--user', default=None)
@click.option('--password', default=None)
@click.option('--initialize/--no-initialize', default=False)
@click.option("--file",default=None)
def bard(host, db, user, password, initialize, file):
    """
    Client entry

    :param host:
    :param db:
    :param user:
    :param password:
    :param initialize:
    :param file:
    :return:
    """

    client = Client()
    try:
        c = Bard(host, db, user, password)
        if initialize:
            c.initialize_db()
        else:
            c.load_config()
            if file is not None:
                c.process_file(str(file))
            else:
                c.process_file()
            c.report()
    except Exception as e:
        print(e.message)
        client.captureException()

        
def cli_generate_report():
    bard()