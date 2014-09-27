# -*- coding: utf-8 -*-
"""High level functional API for using arcomm modules"""

import urlparse
import re
import time
from .util import to_list
from .protocol import factory_connect
from .credentials import Creds
from .exceptions import Timeout

def authorize(connection, secret=""):
    """Authorize the given connection for elevated privileges"""
    connection.authorize(secret)

def authorized(connection):
    """Return authorization status of connection"""
    return connection.authorized

def close(connection):
    """Close the connection"""
    connection.close()

def configure(connection, commands, *args, **kwargs):
    """Similar to execute, but wraps the commands in a configure/end block"""
    commands = to_list(commands)
    commands.insert(0, "configure")
    commands.append("end")
    return execute(connection, commands, *args, **kwargs)

def connect(host, creds, protocol=None, timeout=None, **kwargs):
    """Connect to a host"""
    return factory_connect(host, creds, protocol, timeout, **kwargs)


def connect_with_password(host, username, password="", **kwargs):
    """Use a username and password to connect to host"""
    creds = get_credentials(username=username, password=password)
    return connect(host, creds, **kwargs)

def connect_with_uri(uri, **kwargs):
    """Connect to host using a URI
    example:
        ssh://joe:p4ssw3rd@switch:2222
    """
    parsed = urlparse.urlparse(uri)

    creds = get_credentials(parsed.username, parsed.password)

    return connect(host=parsed.hostname, creds=creds, protocol=parsed.scheme,
                   port=parsed.port, **kwargs)

def create_uri(host, protocol, username, password, port):
    """Create a URI from given parts"""

    creds = get_credentials(username=username, password=password)
    credspart = creds.username
    if creds.password:
        credspart += ":{}".format(creds.password)

    portpart = ":{}".format(port) if port else ""

    uri = "{}://{}@{}{}".format(protocol, host, credspart, portpart)

    return uri

def create_pool(hosts, creds, commands, **kwargs):
    """Return a `Pool` object of hosts and commands

    Example:
    pool = create_pool(["spine1a", "spine2a"], creds, "show version")
    pool.start()
    # do other stuff...
    pool.join()
    for result in pool.results:
        print result
    """
    from .async import Pool
    pool = Pool(hosts, creds=creds, commands=commands, **kwargs)
    return pool

def execute(connection, commands):
    """Execute a command or series of commands and return the results"""
    return connection.execute(commands)

def execute_bg(host, creds, commands, **kwargs):
    """Returns a command ready to be run in the background
    example:

    proc = execute_bg(host, creds, "show version")
    proc.start()
    # do other stuff...
    proc.join()
    for result in proc.results:
        print result
    """
    from .async import Background
    proc = Background(host, creds=creds, commands=commands, **kwargs)
    return proc

def execute_once(host, creds, commands):
    """Executes a single command and closes the connection"""
    connection = connect(host, creds)
    response = execute(connection, commands)
    connection.close()
    return response

def execute_pool(hosts, creds, commands, **kwargs):
    """Given a list of hosts and a Creds() object execute the commands
    asynchronously"""
    pool = create_pool(hosts=hosts, creds=creds, commands=commands, **kwargs)
    pool.run()
    for result in pool.results:
        yield (result.get("host"), result.get("response"))

def execute_until(connection, commands, condition, timeout=30,
                  sleep=5, exclude=False):
    """Runs a command until a condition has been met or the timeout
    (in seconds) is exceeded. If 'exclude' is set this function will return
    only if the string is _not_ present"""
    start_time = time.time()
    check_time = start_time
    response = None
    while (check_time - timeout) < start_time:
        response = execute(connection, commands)
        _match = re.search(re.compile(condition), response)
        if exclude:
            if not _match:
                return response
        elif _match:
            return response
        time.sleep(sleep)
        check_time = time.time()
    raise Timeout("Timed out waiting for response to match condition")

def get_credentials(username, password="", authorize_password=None,
                    private_key=None):
    """Return a Creds object. If username and password are not passed the user
    will be prompted"""
    return Creds(username=username, password=password,
                 authorize_password=authorize_password, private_key=private_key)

