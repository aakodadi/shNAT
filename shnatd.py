#!/usr/bin/python
# -*- coding: utf8 -*-
# <shnatd.py>

"""
                  *******************
                 *** shNAT project ***
                  *******************

shnatd.py : shNAT replay server deamon

"""

import sys
import socket
from threading import Thread as Process
import Queue

"""
from multiprocessing import Process
if sys.platform == 'win32':
    import multiprocessing.reduction"""

CLIENT_HOST = ''
CLIENT_PORT = 81
SHNATLD_HOST = ''
SHNATLD_SIG_PORT = 90
SHNATLD_PORT = 8080
BUFLEN = 32768

class sig_link(Process):
	"""docstring for sig_link"""
	def __init__(self, sig_conn, client_soc, shnatld_soc, queue_maxsize=10):
		super(sig_link, self).__init__()
		self.sig_conn = sig_conn
		self.client_soc = client_soc
		self.shnatld_soc = shnatld_soc
		self.queue_maxsize = queue_maxsize

	def run(self):
		client_list = []
		shnatld_list = []
		while True:
			try:
				client_conn, client_addr = self.client_soc.accept()
				print 'client_link with : ', client_addr
				self.sig_conn.send('.')
				shnatld_conn, shnatld_addr = self.shnatld_soc.accept()
				print 'shnatld_link with : ', shnatld_addr
				client_queue = Queue.Queue(maxsize=self.queue_maxsize)
				shnatld_queue = Queue.Queue(maxsize=self.queue_maxsize)
				client = client_link(client_conn, client_queue, shnatld_queue)
				shnatld = shnatld_link(shnatld_conn, client_queue, shnatld_queue)
				client.start()
				shnatld.start()
				client_list.append(client)
				shnatld_list.append(shnatld)
			except socket.error:
				for client in client_list:
					if client.is_alive():
						client.join()
				for shnatld in shnatld_list:
					if shnatld.is_alive():
						client.join()
				return

class client_link(Process):
	"""docstring for client_link"""
	client_reader = object
	client_writer = object
	def __init__(self, client_conn, client_queue, shnatld_queue):
		super(client_link, self).__init__()
		self.client_conn = client_conn
		self.client_queue = client_queue
		self.shnatld_queue = shnatld_queue

	def run(self):
		self.client_reader = recv_data(self.client_conn, self.client_queue)
		self.client_writer = send_data(self.client_conn, self.shnatld_queue)
		self.client_reader.start()
		self.client_writer.start()
		if self.client_reader.is_alive():
			self.client_reader.join()
		if self.client_writer.is_alive():
			self.client_writer.join()

class shnatld_link(Process):
	"""docstring for shnatld_link"""
	shnatld_reader = object
	shnatld_writer = object
	def __init__(self, shnatld_conn, client_queue, shnatld_queue):
		super(shnatld_link, self).__init__()
		self.shnatld_conn = shnatld_conn
		self.client_queue = client_queue
		self.shnatld_queue = shnatld_queue

	def run(self):
		self.shnatld_reader = recv_data(self.shnatld_conn, self.shnatld_queue)
		self.shnatld_writer = send_data(self.shnatld_conn, self.client_queue)
		self.shnatld_reader.start()
		self.shnatld_writer.start()
		if self.shnatld_reader.is_alive():
			self.shnatld_reader.join()
		if self.shnatld_writer.is_alive():
			self.shnatld_writer.join()


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
client_soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
shnatld_soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sig_soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_soc.bind((CLIENT_HOST, CLIENT_PORT))
shnatld_soc.bind((SHNATLD_HOST, SHNATLD_PORT))
sig_soc.bind((SHNATLD_HOST, SHNATLD_SIG_PORT))
client_soc.listen(100)
shnatld_soc.listen(100)
sig_soc.listen(10)
sig_list = []
while True:
	try:
		sig_conn, sig_addr = sig_soc.accept()
		print 'sig_link with : ', sig_addr
		sig = sig_link(sig_conn, client_soc, shnatld_soc)
		sig.start()
		sig_list.append(sig)
	except socket.error:
		for sig in sig_list:
			if sig.is_alive():
				sig.join()
		sig_conn.close()
	except KeyboardInterrupt:
		for sig in sig_list:
			if sig.is_alive():
				sig.join()
		client_soc.close()
		shnatld_soc.close()
		sig_soc.close()
		sys.exit()
