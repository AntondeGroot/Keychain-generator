import socket

from keychain.web.server import HOST, server_on_free_port


def test_server_moves_to_another_port_when_the_asked_one_is_taken():
    with socket.socket() as other_program:
        other_program.bind((HOST, 0))  # any free port, as another program would hold it
        other_program.listen()
        taken_port = other_program.getsockname()[1]

        server = server_on_free_port(taken_port)
        try:
            assert server.server_address[1] != taken_port
        finally:
            server.server_close()
