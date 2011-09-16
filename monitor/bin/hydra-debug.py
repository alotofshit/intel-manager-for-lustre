#!/usr/bin/env python
#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from django.core.management import setup_environ
import settings
setup_environ(settings)

from monitor.models import *

from collections_24 import defaultdict
import sys

from logging import getLogger, FileHandler, INFO, StreamHandler
file_log_name = __name__
getLogger(file_log_name).setLevel(INFO)
getLogger(file_log_name).addHandler(FileHandler("%s.log" % 'hydra'))

def log():
    return getLogger(file_log_name)

def screen(string):
    print string 
    log().debug(string)


import cmd
from texttable import Texttable

class HydraDebug(cmd.Cmd, object):
    def __init__(self):
        super(HydraDebug, self).__init__()
        self.prompt = "Hydra> "

    def precmd(self, line):
        log().debug("> %s" % line)
        return line

    def do_EOF(self, line):
        raise KeyboardInterrupt()

    def __volume_row(self, vol, table):
        table.add_row([
            vol.id,
            vol.role(),
            vol.name,
            vol.status_string()
            ])

    def __filesystem_title(self, filesystem):
        screen(filesystem.name)
        screen("=" * len(filesystem.name))

    def __list_volumes_filesystem(self, filesystem):
        table = Texttable()
        table.header(['id', 'kind', 'name', 'status'])

        try:
            self.__volume_row(filesystem.mgs, table)
        except ManagementTarget.DoesNotExist:
            pass

        try:
            mdt = MetadataTarget.objects.get(filesystem = filesystem)
            self.__volume_row(mdt, table)
        except MetadataTarget.DoesNotExist:
            pass

        osts = ObjectStoreTarget.objects.filter(filesystem = filesystem)
        for ost in osts:
            self.__volume_row(ost, table)
        
        self.__filesystem_title(filesystem)
        screen(table.draw())
        screen("\n")


    def do_volume_list(self, filesystem_name):
        """volume_list [filesystem name]
        Show all volumes in filesystem, or all filesystem if no filesystem is given."""
        if filesystem_name:
            filesystem = Filesystem.objects.get(name = filesystem_name)
            self.__list_volumes_filesystem(filesystem)
        else:
            for filesystem in Filesystem.objects.all():
                self.__list_volumes_filesystem(filesystem)

    def __list_clients_filesystem(self, filesystem):
        table = Texttable()
        table.header(['id', 'host', 'mount point', 'status'])
        clients = Client.objects.filter(filesystem = filesystem)
        for client in clients:
            table.add_row([client.id, client.host.address, client.mount_point, self.__mountable_audit_status(client)])

        self.__filesystem_title(filesystem)
        screen(table.draw())
        screen("\n")

    def do_client_list(self, filesystem_name):
        """client_list [filesystem]
        Display clients of filesystem, or all clients if no filesystem is given."""
        if filesystem_name:
            filesystem = Filesystem.objects.get(name = filesystem_name)
            self.__list_clients_filesystem(filesystem)
        else:
            for filesystem in Filesystem.objects.all():
                self.__list_clients_filesystem(filesystem)

    def do_server_list(self, line):
        """server_list
        Display all lustre server hosts"""
        table = Texttable()
        table.header(['id', 'address', 'kind', 'lnet status'])
        for host in Host.objects.all():
            if host.mountable_set.count() > 0:
                table.add_row([host.id, host.address, host.role(), host.status_string()])

        screen(table.draw())

    def do_add_host(self, line):
        """add_host [user@]<hostname>[:port]
        Add a host to be monitored"""
        host, ssh_monitor = SshMonitor.from_string(line)
        host.save()
        ssh_monitor.host = host
        ssh_monitor.save()

    def do_host_list(self, line):
        """host_list
        Display all known hosts"""
        table = Texttable()
        table.header(['id', 'name', 'status'])
        for host in Host.objects.all():
            table.add_row([host.id, host.address, host.status_string()])
        screen(table.draw())

    def do_test_fake_events(self, line):
        from random import randint
        count = int(line)
        hosts = list(Host.objects.all())
        for i in range(0, count):
            import logging
            idx = randint(0, len(hosts) - 1)
            host = hosts[idx]
            LearnEvent(learned_item = host, severity = logging.INFO).save()

    def do_audit_list(self, line):
        for m in Monitor.objects.all():
            from celery.result import AsyncResult
            if m.task_id:
                task_state = AsyncResult(m.task_id).state
            else:
                task_state = ""
            print "%s %s %s %s" % (m.host, m.state, m.task_id, task_state)
    def do_audit_clear(self, line):
        for m in Monitor.objects.all():
            m.update(state = 'idle', task_id = None)



if __name__ == '__main__':
    cmdline = HydraDebug

    if len(sys.argv) == 1:
        try:
            cmdline().cmdloop()
        except KeyboardInterrupt:
            screen("Exiting...")
    else:
        cmdline().onecmd(" ".join(sys.argv[1:]))

