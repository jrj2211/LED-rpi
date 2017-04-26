import socket
import sys
import os
import RPi.GPIO as GPIO
import time
import json
import math
import errno
import TcpClient
from socket import error as SocketError
from thread import start_new_thread


# Setup Network
HOST = ''
PORT = 9999

channel = -1

patterns = []

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

def sendMessage(message):
	message = json.dumps(message);
	s.send(message)
	
def receiveMessage(size):
	return json.loads(s.recv(size))
	
def getPatterns():
	global patterns
	
	message = {}
	message['patterns-get'] = channel
	sendMessage(message)
	response = receiveMessage(1024)
	patterns = response["patterns-get"]
	print("  Loaded Patterns")
	
getPatterns()

try:
	while True:
		input = raw_input("Command: ")

		if input == "h":
			print("1: Set Channel")
			print("2: Set Color")
			print("3: Brightness (0-100)")
			print("4: Lightness (0-100)")
			print("5: Get Patterns")
			print("6: Set Pattern")
			print("7: Start Pattern")
			print("8: Stop Pattern")
			print("9: Restart Pattern")
			print("d: Disconnect")
			print("h: Show Help")
		if input == "d":
			break
		elif input == "1":
			channel = raw_input("  Channel: ")
		elif input == "2":
			message = {}
			message['channel'] = channel
			message['red'] = raw_input("  Red: ")
			message['green'] = raw_input("  Green: ")
			message['blue'] = raw_input("  Blue: ")
			sendMessage(message)
		elif input == "3":
			message = {}
			message['channel'] = channel
			message['brightness'] = raw_input("  Brightness(0-100): ")
			sendMessage(message)
		elif input == "4":
			message = {}
			message['channel'] = channel
			message['lightness'] = raw_input("  Lightness(0-100): ")
			sendMessage(message)
		elif input == "5":
			getPatterns()
		elif input == "6":
			if len(patterns) > 0:
				for ind, file in enumerate(patterns):
					print("  " + str(ind) + ". " + file)
				message = {}
				message['channel'] = channel
				message['pattern-set'] = patterns[int(raw_input("  ID: "))]
				sendMessage(message)
			else:
				print("  No patterns loaded.")
		elif input == "7":
			message = {}
			message['channel'] = channel
			message['pattern-run'] = True
			sendMessage(message)
		elif input == "8":
			message = {}
			message['channel'] = channel
			message['pattern-run'] = False
			sendMessage(message)
		elif input == "9":
			message = {}
			message['channel'] = channel
			message['pattern-restart'] = True
			sendMessage(message)
			
			
except KeyboardInterrupt:
	print()