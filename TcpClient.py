import socket
import sys
import os
from struct import *

class TcpClient():

	# Global variable for assigning and ID to a client
	id = 0
	
	def __init__(self, conn, address, port):
		# Store information for the client
		self.connection = conn
		self.id = TcpClient.id
		self.address = address
		self.port = port
		TcpClient.id = TcpClient.id + 1
		
		# Roll over client ID - this is only for logging/debug
		# If two clients end up getting the same ID its not the end of the world
		if TcpClient.id > 65535:
			TcpClient.id = 0
			
	def receive(self, maxLength, buffer = None):
		buffer = self.connection.recv(maxLength)
		return len(buffer);
		
	def receiveAll(self, length):
		msg = ''
		# Loop until the requested length has been received
		while len(msg) < length:
			part = self.connection.recv(length - len(msg))
			
			# If we didnt get anything back then the connection is terminating so break
			if not part:
				break
			
			msg += str(part)
		return msg;
		
	def receiveMessage(self):
		# Get the length of the next message then receive that many bytes
		return self.receiveAll(self.nextMessageLength())
		
	def nextMessageLength(self):
		# Get the first 4 bytes
		msg = self.receiveAll(4)
		size = -1
		if len(msg) == 4:
			# Unpack the bytes into an integer - unpack deals with byte order for us
			size = unpack('>i', msg)[0]
		return size
		
	def sendMessage(self, msg):
		# Send the size of the message (4 packed bytes)
		self.sendMessageSize(len(msg))
		# Send the entire message
		self.connection.sendall(msg)
		
	def sendMessageSize(self, size):
		# Send the number of bytes of the message as the first 4 bytes
		self.connection.send(pack("!i", size))
		
	def sendRandom(self, fileSize, maxChunk):
		# Send the size of the random string we are going to send
		self.sendMessageSize(fileSize)
		
		# Keep track of how many bytes left need to be sent
		bytesLeftToSend = fileSize;
		
		while bytesLeftToSend > 0:
			# Generate next payload size
			chunkSize = maxChunk if bytesLeftToSend > maxChunk else bytesLeftToSend
			self.connection.sendall(bytearray(os.urandom(chunkSize)))
			bytesLeftToSend -= chunkSize;
				
	def disconnect(self):
		# Terminate the connection
		self.connection.close();
		
	def getId(self):
		# Return the self generated client ID
		return self.id
		
	def getHexId(self, paddingLength):
		# Returns a formatted hex string with zero padding of paddingLength
		return '0x%0*x' % (paddingLength,self.id) 
			
	def getAddress(self):
		# Return the IP address of the client
		return self.address
		
	def getPort(self):
		# Return the port address of the client
		return self.port