# Async-Client-Server
Implementation of asynchronous client and server code in Python for a chat program that will operate over TCP sockets. Final project for CSI-235 in April 2019.

The basic protocol that this program will follow is sending UTF-8 encoded JSON messages over TCP sockets prefixed by the message length encoded as 4 byte unsigned integers.
Message structure will be: (SRC, DEST, TIMESTAMP, CONTENT).
The associated server will be responsible for monitoring clients that join and notifying other users of new clients.
