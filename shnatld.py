#!/usr/bin/python
# -*- coding: utf8 -*-
# <shnatld.py>

"""
                  *******************
                 *** shNAT project ***
                  *******************

shnatld.py : shNAT local deamon

"""

import sys
import socket
from threading import Thread as Process
import Queue

"""
from multiprocessing import Process
if sys.platform == 'win32':
    import multiprocessing.reduction"""

SERVER_HOST = 'localhost'
SERVER_PORT = 80
SHNATD_HOST = 'localhost'
SHNATD_SIG_PORT = 90
SHNATD_PORT = 8080
BUFLEN = 32768
CONNECTED = False

def bridg_link(server_host, server_port, shnatd_host, shnatd_port, queue_maxsize=10):
	"""docstring for bridg_link"""
	shnatd_queue = Queue.Queue(maxsize=queue_maxsize)
	server_queue = Queue.Queue(maxsize=queue_maxsize)
	shnatd_con = client_shnatd(shnatd_host, shnatd_port, shnatd_queue, server_queue)
	server_con = client_server(server_host, server_port, shnatd_queue, server_queue)
	return shnatd_con, server_con

class client_shnatd(Process):
	"""docstring for client_shnatd"""
	soc = object
	shnatd_reader = object
	shnatd_writer = object
	def __init__(self, shnatd_host, shnatd_port, shnatd_queue, server_queue):
		super(client_shnatd, self).__init__()
		self.shnatd_queue = shnatd_queue
		self.server_queue = server_queue
		self.shnatd_host = shnatd_host
		self.shnatd_port = shnatd_port

	def run(self):
		self.soc = socket.create_connection((self.shnatd_host, self.shnatd_port))
		print 'client_link with the shnatd.py...'
		self.shnatd_reader = recv_data(self.soc, self.shnatd_queue)
		self.shnatd_writer = send_data(self.soc, self.server_queue)
		self.shnatd_reader.start()
		self.shnatd_writer.start()
		if self.shnatd_reader.is_alive():
			self.shnatd_reader.join()
		if self.shnatd_writer.is_alive():
			self.shnatd_writer.join()

class client_server(Process):
	"""docstring for client_server"""
	soc = object
	server_reader = object
	server_writer = object
	def __init__(self, server_host, server_port, shnatd_queue, server_queue):
		super(client_server, self).__init__()
		self.shnatd_queue = shnatd_queue
		self.server_queue = server_queue
		self.server_host = server_host
		self.server_port = server_port

	def run(self):
		self.soc = socket.create_connection((self.server_host, self.server_port))
		print 'server_link with the "real server"...'
		self.server_reader = recv_data(self.soc, self.server_queue)
		self.server_writer = send_data(self.soc, self.shnatd_queue)
		self.server_reader.start()
		self.server_writer.start()
		if self.server_reader.is_alive():
			self.server_reader.join()
		if self.server_writer.is_alive():
			self.server_writer.join()

class recv_data(Process):
	"""docstring for recv_data"""
	def __init__(self, soc, queue):
		super(recv_data, self).__init__()
		self.soc = soc
		self.queue = queue

	def run(self):
		global BUFLEN
		while True:
			try:
				data = self.soc.recv(BUFLEN)
				if not data :
					self.soc.close()
					self.queue.put('\quitting\\')
					return
				self.queue.put(data)
			except socket.error:
				self.soc.close()
				self.queue.put('\quitting\\')
				return

class send_data(Process):
	"""docstring for send_data"""
	def __init__(self, soc, queue):
		super(send_data, self).__init__()
		self.soc = soc
		self.queue = queue

	def run(self):
		global BUFLEN
		while True:
			try:
				data = self.queue.get()
				if data == '\quitting\\':
					self.soc.close()
					return
				self.soc.send(data)
			except socket.error:
				self.soc.close()
				return

		
"""docstring for the main program"""
shnatd_con_list = []
server_con_list = []
while True:
	try:
		if not CONNECTED:
			soc = socket.create_connection((SHNATD_HOST, SHNATD_SIG_PORT))
			print 'sig_link with the shnatd.py...'
			CONNECTED = True
		soc.recv(1)
		new_shnatd_con, new_server_con = bridg_link(SERVER_HOST, SERVER_PORT, SHNATD_HOST, SHNATD_PORT)
		new_shnatd_con.start()
		new_server_con.start()
		shnatd_con_list.append(new_shnatd_con)
		server_con_list.append(new_server_con)
	except socket.error:
		if CONNECTED:
			soc.close()
			CONNECTED = False
	except KeyboardInterrupt:
		if CONNECTED:
			soc.close()
		for shnatd_con in shnatd_con_list:
			if shnatd_con.is_alive():
				shnatd_con.join()
		for server_con in server_con_list:
			if server_con.is_alive():
				server_con.join()
		sys.exit()