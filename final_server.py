import argparse
import asyncio
import json
import time
import struct


class Server(asyncio.Protocol):
    """A server to host conversations between users."""

    # Class static variables
    clients = {}
    messages = []

    def connection_made(self, transport):
        """Establish a connection with client and identify their address."""

        self.transport = transport
        self.address = transport.get_extra_info('peername')
        self.buffer = b''
        self.username = ""
        print('Accepted connection from {}'.format(self.address))

    def data_received(self, data):
        """Receive data sent from the client."""

        self.buffer += data
        if len(self.buffer) > 4:
            length = struct.unpack("!I", self.buffer[:4])
            if len(self.buffer[4:]) < length[0]:
                pass
            else:
                message = json.loads(self.buffer[4:].decode('UTF-8'))
                self.buffer = b''
                self.form_response(message)

    def form_response(self, message):
        """Discerns how to respond to client message."""

        # Connection with valid username
        if "USERNAME" in message.keys() and message["USERNAME"] not in Server.\
                clients.keys():
            self.username = message["USERNAME"]
            self.broadcast({"USERS_JOINED": [self.username]})
            Server.clients[self.username] = self
            self.send_message({"USERNAME_ACCEPTED": "true", "INFO": "Welcome!",
                               "USER_LIST": list(Server.clients.keys()),
                               "MESSAGES": self.send_backlog()})

        # Connection with unavailable username
        elif "USERNAME" in message.keys() and message["USERNAME"] in \
                Server.clients.keys():
            self.send_message({"USERNAME_ACCEPTED": "false",
                               "INFO": "The provided username "
                                       "is already in use."})

        # Receive a message to be forwarded along
        elif "MESSAGES" in message.keys():
            for item in message["MESSAGES"]:

                # Non-spoofed message
                if message["MESSAGES"][0][0] == self.username:
                    Server.messages.append(item)

                    # Broadcast message
                    if message["MESSAGES"][0][1] == "ALL":
                        content = (self.username, "ALL", int(time.time()),
                                   message["MESSAGES"][0][3])
                        package = {"MESSAGES": [content]}
                        self.broadcast(package)

                    # Private message
                    elif message["MESSAGES"][0][1] in Server.clients.keys():
                        content = (self.username, message["MESSAGES"][0][1],
                                   int(time.time()), message["MESSAGES"][0][3])
                        package = {"MESSAGES": [content]}
                        self.send_message(package, message["MESSAGES"][0][1])

                    # Error in recipient field
                    else:
                        self.send_message("ERROR: Listed destination is not a"
                                          " connected user, and also not ALL. "
                                          "The server threw out this message.")
                        del Server.messages[len(Server.messages)-1]

                # Spoofed source
                else:
                    self.send_message("ERROR: Source field doesn't match "
                                      "username in cache for this socket. "
                                      "No spoofing!")

        # Client sent an incorrectly formatted message
        else:
            self.send_message({"ERROR": "Invalid message received."})

    def send_message(self, contents, recipient=None):
        """Send message back to clients in accordance to protocol."""

        data = json.dumps(contents).encode('UTF-8')
        length = struct.pack("!I", len(data))

        # Respond to client on this socket
        if not recipient:
            self.transport.write(length + data)

        # Respond to client on listed socket
        else:
            Server.clients[recipient].transport.write(length + data)

    def broadcast(self, message):
        """Send a message to all users currently connected to the server."""

        for key in Server.clients:
            self.send_message(message, key)

    def send_backlog(self):
        """Send a user their message history upon joining."""

        messages = []

        for message in Server.messages:
            if message[1] == self.username or message[1] == "ALL":
                messages["MESSAGES"].append(message)

        return messages

    def connection_lost(self, exc):
        """Handle terminated connections."""

        if exc:
            print('Client {} error: {}'.format(self.address, exc))
            if Server.clients != {}:
                del Server.clients[self.username]
                self.broadcast({"USERS_LEFT": [self.username]})

        else:
            print('Client {} closed socket'.format(self.address))
            if Server.clients != {}:
                del Server.clients[self.username]
                self.broadcast({"USERS_LEFT": [self.username]})


def run_server(host, port):
    """Create and start a server on specified host and port."""

    address = (host, port)
    loop = asyncio.get_event_loop()
    coroutine = loop.create_server(Server, *address)
    server = loop.run_until_complete(coroutine)
    print('Listening at {}'.format(address))

    try:
        loop.run_forever()
    finally:
        server.close()
        loop.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TCP File Uploader')
    parser.add_argument('host', help='interface the server listens at;'
                        ' host the client sends to')
    parser.add_argument('-p', metavar='PORT', type=int, default=7000,
                        help='TCP port (default 8900)')
    args = parser.parse_args()
    run_server(args.host, args.p)
