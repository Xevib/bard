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
@click.option("--file",default=None)
def process(host, db, user, password, file):
    """
    Process file

    :param host:
    :param db:
    :param user:
    :param password:
    :param file:
    :return:
    """

    client = Client()
    try:
        c = Bard(host, db, user, password)
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


@bard.command("initialize")
@click.option('--host', default=None)
@click.option('--db', default=None)
@click.option('--user', default=None)
@click.option('--password', default=None)
def initialize(host, db,user,password):
    """
    Initializes database

    :param host: Database host
    :param db: Database name
    :param user: User database
    :param password: Database password
    :return: None
    """

    c = Bard(host, db, user, password)
    c.initialize_db()
        
def cli_generate_report():
    bard()