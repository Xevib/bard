# -*- coding: utf-8 -*-
import click
from raven import Client
from bard import Bard


@click.group()
def bardgroup():
    pass


@bardgroup.command("process")
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


@bardgroup.command("adduser")
@click.argument("login")
@click.argument("userpassword")
@click.option('--host', default=None)
@click.option('--db', default=None)
@click.option('--user', default=None)
@click.option('--password', default=None)
def adduser(login, userpassword, host, db, user, password):
    """
    Adds user to bard

    :param login: Login name
    :param userpassword: User password
    :param host:
    :param db: Postgres database
    :param user: Database user
    :param password: Database password
    :return:
    """

    bard = Bard(host, db, user, password)
    bard.create_user(login, userpassword)


@bardgroup.command("addtags")
@click.argument("user")
@click.argument("bbox")
@click.argument("description")
@click.argument("tags")
@click.option("--node/--no-node", default=False)
@click.option("--way/--no-way", default=False)
@click.option("--relation/--no-relation", default=False)
@click.option('--host', default=None)
@click.option('--db', default=None)
@click.option('--user','dbuser', default=None)
@click.option('--password', default=None)
def adduser(user,bbox,description,tags,node,way,relation, host, db, dbuser, password):
    """
    Adds user to bard

    :param user: User to add the tags
    :param bbox: Bounding box to apply the tags
    :param description: Tags description
    :param tags: Tags to evauate
    :param host: Postgres host
    :param db: Database name
    :param dbuser: Database user
    :param password: Database password
    :return:
    """

    bard = Bard(host, db, dbuser, password)
    bard.create_tags(user, bbox, description, tags, node, way, relation)


@bardgroup.command("initialize")
@click.option('--host', default=None)
@click.option('--db', default=None)
@click.option('--user', default=None)
@click.option('--password', default=None)
def initialize(host, db, user, password):
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
