import socket
import argparse
from struct import pack

DEFAULT_PORT = 69
BLOCK_SIZE = 512
DEFAULT_TRANSFER_MODE = 'octet'

OPCODE = {'RRQ': 1, 'WRQ': 2, 'DATA': 3, 'ACK': 4, 'ERROR': 5}
MODE = {'netascii': 1, 'octet': 2, 'mail': 3}

ERROR_CODE = {
    0: "Not defined, see error message (if any).",
    1: "File not found.",
    2: "Access violation.",
    3: "Disk full or allocation exceeded.",
    4: "Illegal TFTP operation.",
    5: "Unknown transfer ID.",
    6: "File already exists.",
    7: "No such user."
}

def send_wrq(filename, mode):
    format = f'>h{len(filename)}sB{len(mode)}sB'
    wrq_message = pack(format, OPCODE['WRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(wrq_message, server_address)
    print(wrq_message)

def send_rrq(filename, mode):
    format = f'>h{len(filename)}sB{len(mode)}sB'
    rrq_message = pack(format, OPCODE['RRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(rrq_message, server_address)
    print(rrq_message)

def send_ack(seq_num, server):
    format = f'>hh'
    ack_message = pack(format, OPCODE['ACK'], seq_num)
    sock.sendto(ack_message, server)
    print(seq_num)
    print(ack_message)

def tftp_put(filename):
    sock.settimeout(5)
    # Send WRQ_message
    send_wrq(filename, DEFAULT_TRANSFER_MODE)

    ack, address = sock.recvfrom(4)

    # Open the file to upload
    with open(filename, 'rb') as file:  # 파일을 읽을 때 with 문을 사용하여 파일을 자동으로 닫아줍니다.
        block_number = 1

        while True:
            # Read data from the file
            file_block = file.read(BLOCK_SIZE)

            # Check if the file_block is empty
            if not file_block:
                break

            # Create DATA packet
            data_packet = pack(f'>hh{len(file_block)}s', OPCODE['DATA'], block_number, file_block)

            # Send DATA packet
            sock.sendto(data_packet, address)

            try:
                # Receive ACK from the server
                ack, address = sock.recvfrom(4)
                ack_opcode = int.from_bytes(ack[:2], 'big')
                ack_block_number = int.from_bytes(ack[2:], 'big')

                if ack_opcode == OPCODE['ACK'] and ack_block_number == block_number:
                    block_number += 1
                    print(f"Block {ack_block_number} ACK received.")
                else:
                    print("Unexpected ACK. Retrying...")
            except socket.timeout:
                print("Timeout. Retrying...")

    print("File upload complete.")
    sock.close()

# parse command line arguments
parser = argparse.ArgumentParser(description='TFTP client program')
parser.add_argument(dest="host", help="Server IP address", type=str)
parser.add_argument(dest="operation", help="get or put a file", type=str)
parser.add_argument(dest="filename", help="name of file to transfer", type=str)
parser.add_argument("-p", "--port", dest="port", type=int)
args = parser.parse_args()

# Create a UDP socket
server_ip = args.host
server_port = DEFAULT_PORT
server_address = (server_ip, server_port)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


mode = DEFAULT_TRANSFER_MODE
operation = args.operation
filename = args.filename

if operation.lower() == 'get':
    # Send RRQ_message
    send_rrq(filename, mode)

    # Open a file to save data from the server
    file = open(filename, 'wb')
    expected_block_number = 1

    while True:
        # receive data from the server
        data, server_new_socket = sock.recvfrom(516)
        opcode = int.from_bytes(data[:2], 'big')

        # check message type
        if opcode == OPCODE['DATA']:
            block_number = int.from_bytes(data[2:4], 'big')
            if block_number == expected_block_number:
                send_ack(block_number, server_new_socket)
                file_block = data[4:]
                file.write(file_block)
                expected_block_number = expected_block_number + 1
                print(file_block.decode())
            else:
                send_ack(block_number, server_new_socket)

        elif opcode == OPCODE['ERROR']:
            error_code = int.from_bytes(data[2:4], byteorder='big')
            print(ERROR_CODE[error_code])
            break

        else:
            break

        if len(file_block) < BLOCK_SIZE:
            file.close()
            print(len(file_block))
            break

elif operation.lower() == 'put':
    tftp_put(filename)

# Close the socket
sock.close()
