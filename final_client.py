import asyncio
import json
import struct
import time


class AsyncClient(asyncio.Protocol):
    """A client to allow communication with a server."""

    def connection_made(self, transport):
        """Establish a connection with server and identify their address."""

        self.transport = transport
        self.address = transport.get_extra_info('peername')
        self.buffer = b''
        print('Made connection with {}'.format(self.address))
        self.username = input('Select a username: \n')
        self.connected = False  # set to true upon username being accepted

        data = json.dumps({"USERNAME": self.username}).encode('UTF-8')
        length = struct.pack("!I", len(data))

        self.transport.write(length + data)

    def data_received(self, data):
        """Handle data received from the server."""

        self.buffer += data
        if len(self.buffer) > 4:
            length = struct.unpack("!I", self.buffer[:4])

            if len(self.buffer[4:]) < length[0]:
                pass

            else:
                message = self.buffer[4:4+length[0]].decode('UTF-8')
                self.buffer = self.buffer[4+length[0]:]
                print(message)

                # Confirm connection by checking if username was accepted
                if not self.connected:
                    message = json.loads(message)

                    if message["USERNAME_ACCEPTED"] == "true":
                        self.connected = True
                        print("Enter your message. You will select a "
                              "recipient after.")

                self.data_received(b'')


@asyncio.coroutine
def handle_user_input(loop, client):
    """Handle user input by reading input in separate thread."""

    while True:
        message = yield from loop.run_in_executor(None, input, "> ")

        if message == 'quit':
            print("Disconnecting from the server.")
            loop.stop()
            break

        elif client.connected:
            recipient = input("Choose a recipient: @username for private "
                              "message, ALL to send a broadcast: \n")

            # Private message
            if recipient[0] == "@":
                dest = recipient[1:]

            # Broadcast
            elif recipient.upper() == "ALL":
                dest = "ALL"

            # Invalid destination
            else:
                while recipient[0] != "@" and recipient.lower() != "all":
                    recipient = input("Invalid recipient. Please try again and"
                                      " give a username or ALL: \n")

                if "@" in recipient:
                    dest = recipient[1:]
                else:
                    dest = recipient

            content = (client.username, dest, int(time.time()), message)
            messages = {"MESSAGES": [content]}

            data = json.dumps(messages).encode('UTF-8')
            length = struct.pack("!I", len(data))

            client.transport.write(length + data)

        # Re-entering a username
        else:
            client.username = \
                input('You still need a username, try another: \n')
            data = json.dumps({"USERNAME": client.username}).encode('UTF-8')
            length = struct.pack("!I", len(data))

            client.transport.write(length + data)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    client = AsyncClient()

    coroutine = loop.create_connection(lambda: client, "localhost", 7000)
    loop.run_until_complete(coroutine)
    asyncio.ensure_future(handle_user_input(loop, client))

    try:
        loop.run_forever()
    finally:
        loop.close()
