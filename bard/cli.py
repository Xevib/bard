# -*- coding: utf-8 -*-
import click
from raven import Client
from bard import Bard


@click.group()
def bard():
    pass


@bard.command("process")
@click.argument("process")
@click.option('--host', default=None)
@click.option('--db', default=None)
@click.option('--user', default=None)
@click.option('--password', default=None)
@click.option('--initialize/--no-initialize', default=False)
@click.option("--file",default=None)
def process(host, db, user, password, initialize, file):
    """
    Process file

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


@bard.command("adduser")
@click.argument("name")
@click.argument("password")
@click.option('--host', default=None)
@click.option('--db', default=None)
@click.option('--user', default=None)
@click.option('--password', default=None)
def bardadduser(login, password):
    """
    Adds user to bard

    :param login: Login name
    :param password: User password
    :return:
    """
    bard = Bard()
    bard.create_user(login, password)

        
def cli_generate_report():
    bard()