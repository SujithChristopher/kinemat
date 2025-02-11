"""This program is for recording IMU data, through HC05 bluetooth module"""

import struct
import keyboard
import csv
from sys import stdout
import time
from visualizer import rs_time
import socket
import threading
import numpy as np
import os
from numba import njit

@njit()
def roll(data):
    return np.roll(data, -1, axis=1)
     
class MobboCom(object):
    # Contains functions that enable communication between the docking station and the IMU watches

    def __init__(self, port = 23000, csv_path="", csv_enable=False, single_file_protocol=False, csv_name=None):
        # Initialise serial payload
        self.count = 0
        self.plSz = 0
        self.payload = bytearray()

        local_ip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        local_ip.connect(("8.8.8.8", 80))

        # Get the local IPv4 address from the socket
        self.local_ip_address = local_ip.getsockname()[0]

        # Define the broadcast ip and port
        self.broadcast_ip = ''.join([ip + "." for ip in self.local_ip_address.split(".")[:-1]]) + "255" # getting broadcast ip address
        self.broadcast_port = port
        
        self.plot_data_id1 = np.zeros((4, 1000))
        self.plot_data_id2 = np.zeros((4, 1000))
        
        self.stop_st = False

        time.sleep(1)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.settimeout(0.5)
        
        self.hospital_id = ''
        self.start_rec = False

        stdout.write("Initializing mobbo program\n")

    def jedi_read(self, _bytes):
        """returns bool for valid read, also returns the data read"""
        
        if (_bytes[0] == b'\xff') and (_bytes[1] == b'\xff'):
            chksum = 255 + 255
            self.plSz = _bytes[2]
            chksum += self.plSz
            self.payload = _bytes[3:3+self.plSz]
            print(self.payload)
            chksum += sum(self.payload)
            chksum = bytes([chksum % 256])
            _chksum = _bytes[-1]            
            return _chksum == chksum

        return False

    def disconnect(self):
        stdout.write("disconnected\n")
        
    def stop_streaming(self):
        stdout.write("streaming stopped\n")
        self.stop_st = True

    def record_stream(self):
        if not os.path.exists(os.path.join('data', self.hospital_id)):
            os.makedirs(os.path.join('data', self.hospital_id))  
            
         
        self.csv_file1 = open(os.path.join('data', self.hospital_id, 'board1.csv'), 'w')
        self.csv_file2 = open(os.path.join('data', self.hospital_id, 'board2.csv'), 'w')
        
        self.csv_writer1 = csv.writer(self.csv_file1)
        self.csv_writer2 = csv.writer(self.csv_file2)
        self.start_rec = True

    def stop_recording(self):
        self.start_rec = False
        self.csv_file1.close()
        self.csv_file2.close()
    

    def send_broadcast(self):
        self.stop_st = True

        time.sleep(1)
        for i in range(10):
            self.udp_socket.sendto('A'.encode(), (self.broadcast_ip, self.broadcast_port))
        
        self.stop_st = False
        
        self.run()
        

    def run_program(self):

        message = "A"

        self.udp_socket.sendto(message.encode(), (self.broadcast_ip, self.broadcast_port))
        self.udp_socket.sendto(message.encode(), (self.broadcast_ip, self.broadcast_port))
        self.udp_socket.sendto(message.encode(), (self.broadcast_ip, self.broadcast_port))
        self.udp_socket.sendto(message.encode(), (self.broadcast_ip, self.broadcast_port))
        self.udp_socket.sendto(message.encode(), (self.broadcast_ip, self.broadcast_port))
        self.udp_socket.sendto(message.encode(), (self.broadcast_ip, self.broadcast_port))
        self.udp_socket.sendto(message.encode(), (self.broadcast_ip, self.broadcast_port))
        self.udp_socket.sendto(message.encode(), (self.broadcast_ip, self.broadcast_port))
        print(f"Multicast Sent: {message}")
        while True:
            
            if self.stop_st:
                break
            
            return_message = self.udp_socket.recvfrom(23000)
            self.udp_socket.settimeout(3)
            self.current_id = return_message[0][3]
            
            match self.current_id:
                case 1:
                    data = struct.unpack('4l', return_message[0][4:4+16])
                    self.plot_data_id1[:, -1] = data
                    self.plot_data_id1 = np.roll(self.plot_data_id1, -1, axis=1)
                    # self.plot_data_id1 = roll(self.plot_data_id1)
                    if self.start_rec:
                        self.csv_writer1.writerow([rs_time(),*data])
                case 2:
                    data = struct.unpack('4l', return_message[0][4:4+16])
                    self.plot_data_id2[:, -1] = data
                    self.plot_data_id2 = np.roll(self.plot_data_id2, -1, axis=1)
                    if self.start_rec:
                        self.csv_writer2.writerow([rs_time(), *data])

            if self.jedi_read(return_message[0]):
                print(f"Multicast Received: {struct.unpack('4l', self.payload[1:])}")
        
    def get_data(self):
        return 'data'
    
    def run(self):
        thread = threading.Thread(target=self.run_program)
        thread.start()
        # thread.join()


if __name__ == '__main__':

    _filepath = r"D:\CMC\visualizer\data_dumps"
    myport = MobboCom(csv_path=_filepath, csv_enable=False)
    myport.run()

