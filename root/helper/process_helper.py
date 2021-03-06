#!/usr/bin/env python3

""" File to handle background process created by the bot """

from multiprocessing import active_children
from re import A
from root.model.cprocess import CProcess as Process
import root.util.logger as logger

PROCESS_NAME = "ultimi_acquisti_process_%s"


def find_process(name_prefix: str) -> Process:
    """Retrieve a process using a prefix name as a key

    Args:
        name_prefix (str): The name prefix used to identify the process

    Returns:
        Process: The found process or None if nothing
    """
    for process in active_children():
        title = PROCESS_NAME % name_prefix
        logger.info("process title %s" % title)
        logger.info("process name %s" % process.name)
        if title == process.name:
            return process
    return None


def stop_process(key: str) -> None:
    """Stop a background process identified by a key

    Args:
        key (str): The identifier of the process
    """
    key = str(key)
    logger.info(f"stopping process with {key}")
    process: Process = find_process(key)
    if not process:
        logger.warn(f"Unable to find the process with name {PROCESS_NAME % key}")
        return
    process.terminate()
    process.shutdown()


def restart_process(key: str, timeout: int = -1) -> bool:
    """Restart a background process identified by a key
    Args:
        key (str): The identifier of the process
        int (int, optional): The timeout of the call, Default -1
    """
    key = str(key)
    logger.info(f"restarting process with {key}")
    process: Process = find_process(key)
    if not process:
        logger.warn(f"Unable to find the process with name {PROCESS_NAME % key}")
        return False
    target = process.target
    args = process.args
    logger.info(args)
    # args = args if timeout < 0 else (args[0], args[1], timeout)
    if timeout != -1:
        args = list(args)
        args[-1] = timeout
        args = tuple(args)
    logger.info(args)
    process.terminate()
    process.shutdown()
    # process.kill()
    # process.close()
    create_process(key, target, args)
    return True


def create_process(name_prefix: str, target: callable, args: tuple) -> None:
    """Create a new background process and start it

    Args:
        name_prefix (str): The name prefix used to identify the process
        target (callable): The target to execute by the process
        args (tuple): The arguments to pass to the target
    """
    logger.info("PROCESS_NAME: %s" % PROCESS_NAME)
    logger.info("PROCESS_PREFIX: %s" % name_prefix)
    name: str = PROCESS_NAME % name_prefix
    process: Process = Process(group=None, target=target, args=args, name=name)
    process.daemon = True
    logger.info(f"starting process {name} with {args}")
    process.start()
