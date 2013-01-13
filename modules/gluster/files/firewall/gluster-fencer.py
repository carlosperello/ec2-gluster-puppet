#!/usr/bin/python
import getopt
import os
import re
import socket
import subprocess
import sys

from netfilter.rule import Rule, Match
from netfilter.table import Table, IptablesError


class InvalidCmdException(Exception):
    """Raised when the cmd to execute is not valid."""
    pass


class InvalidVolumeNameException(Exception):
    """Raised when the volume name provided is not valid."""
    pass


def execute_command(cmd):
    """Execute a system command and returns its output.

    :cmd: Array with the command to execute and its arguments.
    """

    if cmd is None or len(cmd) == 0:
        raise InvalidCmdException(name)

    p = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    out, err = p.communicate()
    status = p.wait()
    # check exit status
    if not os.WIFEXITED(status) or os.WEXITSTATUS(status):
        raise RuntimeError('Error getting volume status')
    return out, err


def get_volume_status(name):
    """Return the :name: gluster volume status.

    :name: The gluster volume name we what the status.
    """

    if name is None or len(name) < 1:
        raise InvalidVolumeNameException(name)

    cmd = ['gluster', 'volume', 'status', name]
    out, err = execute_command(cmd)

    return out.splitlines()


def get_volumes():
    """Return a list of gluster volumes."""

    cmd = ['gluster', 'volume', 'list']
    out, err = execute_command(cmd)

    return out.splitlines()


def get_ports_to_filter():
    """Return the list of input and output ports to filter."""

    # Default list of ports.
    filter_ports = {
        'input': {
            'udp': ['111'],
            'tcp': ['24007', '24008'],
        },
        'output': {
            'udp': ['111'],
            'tcp': ['24007', '24008'],
        },
    }

    for volume in get_volumes():

        for line in get_volume_status(volume):
            found = re.match("Brick\s(\S+):\S+\s+(\d+)\s+.*", line)
            if found is not None:
                # It's a Brick connection.
                if found.group(1) == socket.getfqdn():
                    # It's a port we are serving, filter on input.
                    filter_ports['input']['tcp'].append(found.group(2))
                else:
                    # It's a port we are connecting to, filter on output.
                    filter_ports['output']['tcp'].append(found.group(2))

    return filter_ports


def filter_ports(device, ports):
    """Adds to iptables the ports to filter for the given device."""

    input_filter = 'gluster-input'
    output_filter = 'gluster-output'

    table = Table('filter')

    if input_filter in table.list_chains():
        print "Gluster ports are already filtered out. Ignoring request..."
        return

    # Create and prepare the chains that will hold gluster rules.
    table.create_chain(input_filter)
    in_rule = Rule(
        in_interface=device,
        jump=input_filter)
    table.append_rule('INPUT', in_rule)

    table.create_chain(output_filter)
    out_rule = Rule(
        out_interface=device,
        jump=output_filter)
    table.append_rule('OUTPUT', out_rule)

    # Now we actually do the filtering.
    for protocol in ports['input'].keys():
        for port in ports['input'][protocol]:

            in_rule = Rule(
                in_interface=device,
                protocol=protocol,
                matches=[Match(protocol, '--dport %s' % port)],
                jump='DROP')

            print "Filtering port %s from INPUT on device %s..." % (port, device)
            table.append_rule(input_filter, in_rule)

    for protocol in ports['output'].keys():
        for port in ports['output'][protocol]:

            out_rule = Rule(
                out_interface=device,
                protocol=protocol,
                matches=[Match(protocol, '--dport %s' % port)],
                jump='DROP')

            print "Filtering port %s from OUTPUT on device %s..." % (port, device)
            table.append_rule(output_filter, out_rule)


def unfilter_ports(device):
    """Removes from iptables the ports related with gluster on the given device."""

    input_filter = 'gluster-input'
    output_filter = 'gluster-output'

    print "Removing Gluster port filtering..."

    table = Table('filter')

    chains = table.list_chains()

    if input_filter in chains:

        in_rule = Rule(in_interface=device, jump=input_filter)
        try:
            table.delete_rule('INPUT', in_rule)
        except IptablesError:
            pass
        table.flush_chain(input_filter)
        table.delete_chain(input_filter)
    else:
        print "Gluster input ports are not filtered. Ignoring request..."

    if output_filter in chains:

        out_rule = Rule(out_interface=device, jump=output_filter)
        table.delete_rule('OUTPUT', out_rule)
        table.flush_chain(output_filter)
        table.delete_chain(output_filter)
    else:
        print "Gluster output ports are not filtered. Ignoring request..."


def main(action, device):
    if action == 'filter':
        filter_ports(device, get_ports_to_filter())
    elif action == 'unfilter':
        unfilter_ports(device)


if __name__ == '__main__':

    if not os.geteuid()==0:
        sys.exit("\nOnly root can run this script\n")

    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option(
        "-a","--action",dest="action", help="Action to execute",
        metavar=" filter | unfilter", default='filter')
    parser.add_option(
        "-d","--device",dest="device", help="Device name",
        metavar=" <device name>" , default='eth0')

    (opts,args)=parser.parse_args()

    if opts.action not in ['filter', 'unfilter']:
        parser.print_help()
        parser.error("The action %s is unknown." % opts.action)
        sys.exit(1)

    main(opts.action, opts.device)

