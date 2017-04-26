import socket
import sys
import os
import RPi.GPIO as GPIO
import time
import json
import math
import errno
import threading
from socket import error as SocketError
from TcpClient import *

# Setup Network
HOST = ''
PORT = 9999

# Setup GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# Defines
PATTERN_DIR = os.path.join(os.path.dirname(__file__), 'patterns/')

def inRange(value, min, max):
	if value > max:
		value = max
	elif value < min:
		value = min
	return value

class Channels(object):
	added = {};

	@staticmethod
	def get(id):
		id = int(id)
		return Channels.added[id];
		
	@staticmethod
	def match(id):
		id = int(id)
		matched = []
		for channel in Channels.added.itervalues():
			if id == -1 or channel.id == id:
				matched.append(channel)
		return matched
		
	@staticmethod
	def add(id, r, g, b):
		id = int(id)
		Channels.added[id] = Channel(id, r, g, b)
		
class Channel(object):
	def __init__(self, id, r, g, b):
		self.id = id
		self.red = LED(self, r)
		self.green = LED(self, g)
		self.blue = LED(self, b)
		self.leds = [self.red, self.green, self.blue]
		self.brightness = 1.0
		self.lightness = 0.0
		self.pattern = None
		print("Initilized channel " + str(id) + " [" + str(r) + "," + str(g) + "," + str(b) + "]")
		
	def setLightness(self, value):
		self.lightness = inRange(int(value), 0, 100) / 100.0
		self.update()
		
	def setBrightness(self, value):
		self.brightness = inRange(int(value), 0, 100) / 100.0
		self.update()
		
	def setPattern(self, file):
		if self.pattern != None:
			self.pattern.toggle(False)
		self.pattern = Pattern(file, self)
		
	def color(self, r, g, b):
		self.red.set(r)
		self.green.set(g)
		self.blue.set(b)
		self.update()
		
	def update(self):
		for led in self.leds:
			led.set()

class LED(object):
	def __init__(self, channel, pin):
		self.channel = channel
		GPIO.setup(pin, GPIO.OUT)
		self.pin = pin
		self.pwm = GPIO.PWM(pin, 100)
		self.pwm.start(0)
		self.value = 0
		
	def set(self, value=None):
		if value != None:
			self.value = inRange(float(value), 0, 255)
			
		colorRatio = (self.value/255.0)*100
		saturation = (100-colorRatio)*self.channel.lightness
		
		duty = (colorRatio+saturation)*self.channel.brightness
		duty = inRange(duty, 0, 100)
			
		self.pwm.ChangeDutyCycle(duty)
		
	def diff(self, value):
		return float(value)-self.value
		
class Patterns(object):
	added = [];

	@staticmethod
	def load():
		print("Loading patterns...")
		Patterns.added = []
		for file in os.listdir(PATTERN_DIR):
			if file.endswith(".pat"):
				Patterns.added.append(file)
		return list(Patterns.added)
		
class Pattern(object):
	def __init__(self, file, channel):
		self.running = False
		self.cursor = 0
		self.channel = channel
		self.commands = []
		self.thread = None
		
		with open(PATTERN_DIR+file) as f:
			lines = f.read().splitlines()
			for line in lines:
				command = line.split(",")
				if command[0] == "delay":
					self.commands.append({"type": command[0], "delay": float(command[1])})
				elif command[0] == "set":
					self.commands.append({"type": command[0], "delay": float(command[1]), "r": float(command[2]), "g": float(command[3]), "b": float(command[4])})
				elif command[0] == "fade":
					self.commands.append({"type": command[0], "delay": float(command[1]), "r": float(command[2]), "g": float(command[3]), "b": float(command[4])})
		
	def toggle(self, running=None):
		if running == None:
			self.running = not self.running
		else:
			self.running = running
	
		if self.running == True and self.thread == None:
			print("Started pattern: channel " + str(self.channel.id))
			self.thread = Thread(target=self.run, args=())
			self.thread.start()
		elif self.running == False and isinstance(self.thread, Thread):
			self.thread.join()
			self.thread = None
	
	def run(self):
		while self.running == True:
			if self.cursor >= len(self.commands):
				self.cursor = 0
			
			command = self.commands[self.cursor]

			if command["type"] == "delay":
				time.sleep(float(command["delay"]))
			elif command["type"] == "set":
				self.channel.red.set(command["r"])
				self.channel.green.set(command["g"])
				self.channel.blue.set(command["b"])
				time.sleep(float(command["delay"]))
			elif command["type"] == "fade":
				increment_delay = .05
				increments = int(math.floor(float(command["delay"]) / increment_delay))
				
				diff_red = float(self.channel.red.diff(command["r"]) / increments)
				diff_green = float(self.channel.green.diff(command["g"]) / increments)
				diff_blue = float(self.channel.blue.diff(command["b"]) / increments)

				for x in range(0, increments):
					if self.running != True:
						break
						
					self.fader(diff_red, self.channel.red, command["r"])
					self.fader(diff_green, self.channel.green, command["g"])
					self.fader(diff_blue, self.channel.blue, command["b"])

					time.sleep(increment_delay)
			
			self.cursor += 1
			
		print("Stopped pattern: channel " + str(self.channel.id))

	def fader(self, diff, led, desired):
		if diff > 0 and led.value + diff <= desired:
			led.set(led.value + diff)
		elif diff < 0 and led.value + diff >= desired:
			led.set(led.value + diff)
		else:
			led.set(desired)
			
class Message(object):
	def __init__(self, text):
		self.message = {}
		try:
			self.message = json.loads(text)
		except:
			pass
		
	def getAttr(self, attr):
		if self.hasAttr(attr):
			return self.message[attr];
		return None
		
	def hasAttr(self, attr):
		return attr in self.message;
		
# Handle a client
class Client(threading.Thread): 
	def __init__(self, conn, addr):
		threading.Thread.__init__(self)
		self.conn = conn
		self.tcp = TcpClient(conn, addr[0], addr[1])
	
	def run(self):
		print("[S] " + self.tcp.getHexId(4) + " | Client connected")
		
		while True:
			# Get next message size
			size = self.tcp.nextMessageLength()
			if size != -1:
				msg = Message(self.tcp.receiveAll(size))
				
				if msg.hasAttr("channel"):
					channels = Channels.match(msg.getAttr("channel"))
					
					for channel in channels:
						if msg.hasAttr("red"):
							channel.red.set(msg.getAttr("red"))
							if channel.pattern != None:
								channel.pattern.toggle(False)
							
						if msg.hasAttr("green"):
							channel.green.set(msg.getAttr("green"))
							if channel.pattern != None:
								channel.pattern.toggle(False)
							
						if msg.hasAttr("blue"):
							channel.blue.set(msg.getAttr("blue"))
							if channel.pattern != None:
								channel.pattern.toggle(False)
							
						if msg.hasAttr("lightness"):
							channel.setLightness(msg.getAttr("lightness"))
							
						if msg.hasAttr("brightness"):
							channel.setBrightness(msg.getAttr("brightness"))
							
						if msg.hasAttr("pattern-set"):
							channel.setPattern(msg.getAttr("pattern-set"))
							channel.pattern.toggle(True)
							
						if msg.hasAttr("pattern-run"):
							if channel.pattern != None:
								channel.pattern.toggle(msg.getAttr("pattern-run"))
							
						if msg.hasAttr("pattern-restart"):
							if channel.pattern != None:
								channel.pattern.cursor = 0;
								channel.pattern.toggle(True)
							
				if msg.hasAttr("patterns-get"):
					message = {}
					message['patterns-get'] = Patterns.load()
					self.send(message)
			else:
				break
			
		print("[S] " + self.tcp.getHexId(4) + " | Client disconnected")
		self.tcp.disconnect()
		
class Server(object):
	def __init__(self, host, port):
		# Create socket
		print("[SERVER] Starting...")
		self.clients = {}
		
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		 
		# Bind socket to local host and port
		try:
			self.sock.bind((host, port))
		except socket.error as msg: 
			print("[SERVER] Bind failed: " + msg[1] + "[" + str(msg[0]) + "]")
			sys.exit()
		
	def listen(self, num):
		self.sock.listen(10)
		print("[SERVER] Listening")
		
	def acceptClients(self):
		# Wait for clients until keyboard interrupt
		try:
			while True:
				# Handle client connection
				conn, addr = self.sock.accept()
				clientThread = Client(conn, addr)
				clientThread.start()
		except KeyboardInterrupt:
			pass
			
	def stop(self):
		print("[SERVER] Stopping...")
		
		# Stop all the patterns
		for channel in Channels.added.itervalues():
			if channel.pattern != None:
				channel.pattern.toggle(False)
			channel.color(0,0,0)
				
		time.sleep(.1)
		
		self.sock.close()
		GPIO.cleanup()
	
Channels.add(0, 37, 33, 35)
Channels.add(1, 11, 13, 15)

Patterns.load();
		
server = Server(HOST, PORT)
server.listen(10)
server.acceptClients()

server.stop()