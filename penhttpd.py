#!/usr/bin/env python
""" penhttpd
Simple HTTP/HTTPS server for penetration testing.
"""
__author__ = "413x4"
__version__ = "0.1"
__status__ = "dev"
__licence__ = "MIT"

import os
import ssl
import sys
import argparse

"""===============================================
            PERSISTENT CONFIGURATION
==============================================="""
verbose = True
https = False
host = "0.0.0.0"
port = 8000
cert = ''
privkey = ''
workingdir = '.'
"""============================================"""

# X-version imports
if sys.version_info[0] == 2:
    # Python 2.x imports
    import SimpleHTTPServer
    import SocketServer
    import urlparse
else:
    # Python 3.x imports
    import http.server as SimpleHTTPServer
    import socketserver as SocketServer
    import urllib.parse as urlparse

# Colorama support
try:
    from colorama import init, Fore
    colour = True
except ImportError:
    print("[-] Colorama is not installed")
    print("|--> pip install colorama\n")
    colour = False


def cstart():
    _start_line = "\n====== Request Start ======"
    if verbose:
        if colour:
            print(Fore.BLUE + _start_line + Fore.YELLOW)
        else:
            print(_start_line)


def cend():
    _end_line = "====== Request End ======\n"
    if verbose:
        if colour:
            print(Fore.BLUE + _end_line + Fore.RESET)
        else:
            print(_end_line)


def creset():
    if colour:
        print(Fore.RESET)


def cprint(text):
    if verbose:
        print(text)


def generate_certificate():
    command = "openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -subj '/CN=localhost' -nodes"
    os.system(command)
    pass


class penhttpdRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    """Simple HTTP request handler with GET and HEAD commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method.

    The GET and HEAD requests are identical except that the HEAD
    request omits the actual contents of the file.

    The POST supports "100 Continue" requests and displays the content
    being sent by the client.

    Code adapted from:
    https://github.com/enthought/Python-2.7.3/blob/master/Lib/SimpleHTTPServer.py
    """
    _server_version = "penhttpd/{}".format(__version__)

    # Colour support for windows
    if colour:
        init()

    def do_GET(self):
        """ Serve GET request """

        cstart()
        f = self.send_head()
        creset()

        if f:
            self.copyfile(f, self.wfile)
            f.close()

        cprint(self.headers)
        cend()


    def do_HEAD(self):
        """ Serve HEAD request """
        cstart()
        f = self.send_head()
        creset()

        if f:
            f.close()

        cprint(self.headers)
        cend()

    def do_POST(self):
        """ Serve POST request """
        cstart()
        f = self.send_post()
        creset()

        if f:
            self.copyfile(f, self.wfile)  # TODO: Is this really needed ??
            f.close()

        cprint(self.headers)
        cprint(self.data)
        cend()

    """ PUT and DELETE are handled as POST and GET respectively. """
    do_PUT = do_POST
    do_DELETE = do_GET

    def _handle100(self):
        """ Support for "100 Continue" requests """
        try:
            expect = self.headers['Expect']
        except KeyError:
            expect = None

        if expect and expect.startswith('100'):
            self.send_response(100)
            self.end_headers()

        con_length = int(self.headers['Content-Length'])
        return self.rfile.read(con_length).decode('UTF-8')

    def send_post(self):
        """Code for POST and PUT commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            self.data = ""
            parts = urlparse.urlsplit(self.path)

            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urlparse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None

            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                self.data = self._handle100()
                return self.list_directory(path)

        ctype = self.guess_type(path)

        try:
            f = open(path, 'rb')
        except IOError:
            self.data = self._handle100()
            self.send_error(404, "File not found")
            return None

        try:
            self.data = self._handle100()
            self.send_response(200)
            self.send_header("Content-type", ctype)
            fs = os.fstat(f.fileno())
            self.send_header("Content-Length", str(fs[6]))
            self.end_headers()
            return f
        except Exception:
            f.close()
            raise


def _print_start_message():
    print("[*] Server started")
    print("|--> Host   : {}".format(host))
    print("|--> Port   : {}".format(port))
    print("|--> Root   : {}".format(os.getcwd()))
    print("|--> Host   : {}".format(host))
    if https:
        print("|--> Cert   : {}".format(cert))
    print("|--> Verbose: {}\n".format(verbose))


def start_server():
    penhttpd = SocketServer.TCPServer((host, port), penhttpdRequestHandler)
    try:
        if workingdir:
            if not os.path.exists(workingdir):
                os.makedirs(workingdir)

            os.chdir(workingdir)

        if https:
            if not os.path.isfile(cert):
                print("[+] Generate certificate")
                generate_certificate()
                penhttpd.socket = ssl.wrap_socket(penhttpd.socket,
                                                  certfile="cert.pem",
                                                  keyfile="key.pem",
                                                  server_side=True)

            elif privkey:
                penhttpd.socket = ssl.wrap_socket(penhttpd.socket,
                                                  certfile=cert,
                                                  keyfile=privkey,
                                                  server_side=True)
            else:
                penhttpd.socket = ssl.wrap_socket(penhttpd.socket,
                                                  certfile=cert,
                                                  server_side=True)
        _print_start_message()
        penhttpd.serve_forever()

    except KeyboardInterrupt:
        pass

    print("[*] Server stopped")
    penhttpd.shutdown()
    penhttpd.server_close()
    exit(0)


if __name__ == '__main__':
        # Menu
        _description = "Standalone HTTP/HTTPS server for pentesters."
        parser = argparse.ArgumentParser(description=_description)
        parser.add_argument('--host', dest='host', action='store',
                            help='Set listening host.')
        parser.add_argument('--port', dest='port', action='store',
                            help='Set listening port.')
        parser.add_argument('--ssl', dest='ssl', action='store_true',
                            help='Set transport over SSL (HTTPS)')
        parser.add_argument('--cert', dest='cert', action='store',
                            help='Set path to server certificate')
        parser.add_argument('--key', dest='key', action='store',
                            help='Set path to private key')
        parser.add_argument('-w', '--wd', dest='working_directory',
                            action='store',
                            help='Display requests content.')
        parser.add_argument('-v', '--verbose', dest='verbose',
                            action='store_true',
                            help='Display requests content.')
        args = parser.parse_args()

        # Parse arguments
        if args.host:
            host = args.host
        if args.port:
            port = int(args.port)
        if args.ssl:
            https = args.ssl
            if args.cert:
                cert = args.cert
            if args.key:
                privkey = args.key
        if args.verbose:
            verbose = args.verbose
        if args.working_directory:
            workingdir = args.working_directory

        start_server()
