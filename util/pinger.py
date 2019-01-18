from __future__ import print_function
from threading import Thread
import subprocess
import Queue
import platform
import os


class Pinger:
    """
    Class provides threaded ping utility.
    Must pass thread_count as integer and ip_list as list of IPs/hostname in string notation
    ie. ['10.0.0.1', '10.0.0.2', 'www.google.com']
    """
    def __init__(self, thread_count, ip_list):
        self.thread_count = thread_count
        self.ip_list = ip_list
        # The queue of addresses to ping
        self.ips_q = Queue.Queue()
        # The queue of results
        self.out_q = Queue.Queue()

    @ staticmethod
    def determine_platform_ping_arg():
        """
        Provides ping arguments based on platform of device executing program.
        Needed due to differences between OS ping options
        :return: list of ping command with arguments
        """
        # Platform determination for ping command arguments
        plat = platform.system()
        if plat == 'Windows':
            ping_args = ["ping", "-n", "1", "-w", "1"]
        elif plat == 'Linux':
            ping_args = ["ping", "-c", "1", "-w", "1"]
        else:
            raise ValueError("Unknown platform")
        return ping_args

    def ping_wrapper(self):
        """
        ping function wrapper for threads
        performs subprocess ping
        :return: None
        """
        try:
            while True:
                # get an IP item from queue
                address = self.ips_q.get_nowait()

                # ping IP address
                # os.devnull used to send output to null
                with open(os.devnull, "wb") as limbo:
                    result = subprocess.Popen(self.determine_platform_ping_arg() + [address], stdout=limbo,
                                              stderr=limbo).wait()
                    # add results to output queue
                    if result:
                        self.out_q.put((address, "inactive"))
                    else:
                        self.out_q.put((address, "active"))
        except Queue.Empty:
            # No more addresses.
            pass
        finally:
            self.out_q.put(None)

    def start_ping(self):
        """
        Thread function to ping list of IP addresses
        :return: output queue as deque list (list of tuples)
        """

        # create the workers
        workers = []
        for i in range(self.thread_count):
            workers.append(Thread(target=self.ping_wrapper))

        # put all of the IPs in the ips_q queue
        for ip in self.ip_list:
            self.ips_q.put(ip)

        # Start all the workers
        for w in workers:
            w.daemon = True
            w.start()

        # wait until worker threads are done to exit
        for w in workers:
            w.join()

        return self.out_q.queue


if __name__ == '__main__':
    iplist = ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4', '10.0.0.0', '10.0.0.255', '10.0.0.100',
        'google.com', 'github.com', 'nonexisting', '127.0.1.2', '*not able to ping!*', '8.8.8.8']
    pingIPs = Pinger(8, iplist)
    print(pingIPs.start_ping())
