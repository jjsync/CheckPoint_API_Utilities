#
# ping_hosts.py
# version 1.2
#
# Purpose: Pings IP address of all Check Point Management Server host objects and prints results to csv file
# Author: Joshua J. Smith (JJSYNC)
# Writen: October 2018
# Updated: January 2019

# A package for reading passwords without displaying them on the console.
from __future__ import print_function
import getpass
import sys
import os
import csv
import collections
import argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# lib is a library that handles the communication with the Check Point management server.
from lib import APIClient, APIClientArgs
# util is a collection of custom utility classes
from util import Pinger


def main(argv):
    """
    Function to pull all host objects info from check point management server.  Iterates through and pings all
    host objects IP addresses.  Outputs CSV file with 'IP','Active/Inactive Status, Object Name' format
    :param argv: optional arguments to run script without need of user input
    :return: None - outputs csv file
    """

    # default thread count if not supplied by argv
    thread_count = 24
    if argv:
        parser = argparse.ArgumentParser(description="Ping IP address of host objects and outputs to csv file")
        parser.add_argument("-s", type=str, action="store", help="API Server IP address or hostname", dest="api_server")
        parser.add_argument("-u", type=str, action="store", help="User name", dest="username")
        parser.add_argument("-p", type=str, action="store", help="Password", dest="password")
        parser.add_argument("-t", type=int, action="store", help="Number of Ping Threads", dest="thread_count")
        parser.add_argument("-o", type=str, action="store", help="File Name", dest="file_name")

        args = parser.parse_args()

        required = "api_server username password file_name".split()
        for r in required:
            if args.__dict__[r] is None:
                parser.error("parameter '%s' required" % r)

        api_server = args.api_server
        username = args.username
        password = args.password
        file_name = args.file_name
        thread_count = args.thread_count

    else:
        api_server = raw_input("Enter server IP address or hostname:")
        username = raw_input("Enter username: ")
        if sys.stdin.isatty():
            password = getpass.getpass("Enter password: ")
        else:
            print("Attention! Your password will be shown on the screen!")
            password = raw_input("Enter password: ")
        file_name = raw_input("Enter file name: ")

    client_args = APIClientArgs(server=api_server)

    with APIClient(client_args) as client:

        # create debug file. The debug file will hold all the communication between the python script and
        # Check Point's management server.
        client.debug_file = "api_calls.json"

        # The API client, would look for the server's certificate SHA1 fingerprint in a file.
        # If the fingerprint is not found on the file, it will ask the user if he accepts the server's fingerprint.
        # In case the user does not accept the fingerprint, exit the program.
        if client.check_fingerprint() is False:
            print("Could not get the server's fingerprint - Check connectivity with the server.")
            exit(1)

        # login to server:
        login_res = client.login(username, password)

        if login_res.success is False:
            print("Login failed: {}".format(login_res.error_message))
            exit(1)

        # show hosts
        print("Gathering all hosts\nProcessing. Please wait...")
        show_hosts_res = client.api_query("show-hosts", "standard")
        if show_hosts_res.success is False:
            print("Failed to get the list of all host objects: {}".format(show_hosts_res.error_message))
            exit(1)

    # obj_dictionary - for a given IP address, get an diction of host (name) that use this IP address. ie
    # {'10.10.10.10: {'name': "hostname"}}
    obj_dictionary = {}

    # iterates through hosts creating dictionary of key: IP value: host name
    for host in show_hosts_res.data:
        ipaddr = host.get("ipv4-address")
        if ipaddr is None:
            print(host["name"] + " has no IPv4 address. Skipping...")
            continue
        obj_dictionary[ipaddr] = {"name": host["name"]}

    # Calls Pinger class with number of threads and list of ip addresses ['1.1.1.1', '2.2.2.2']
    ping = Pinger(thread_count, obj_dictionary.keys())

    # starts ping test of IP addresses returns result as dequeue list
    queue_list = ping.start_ping()

    # Updates dictionary in place with status of ping results
    for i in queue_list:
        if i is None:
            continue
        else:
            obj_dictionary[i[0]]['status'] = i[1]

    # Orders dictionary for readability
    od_obj_dictionary = collections.OrderedDict(sorted(obj_dictionary.items()))

    ips_dict = []

    # Creates list from dictionary, dictionary values i.e. {key: {key1: value1, key2: value2}} to [key, value1, value2]
    for item in od_obj_dictionary:
        sub_item = list()
        sub_item.append(item)
        for key, value in od_obj_dictionary[item].iteritems():
            sub_item.append(value)
        ips_dict.append(sub_item)

    # writes result to csv file
    with open(file_name, "wb") as f:
        writer = csv.writer(f)
        writer.writerows(ips_dict)


if __name__ == "__main__":
    main(sys.argv[1:])
