
import logging

import socket

from lxml import etree

import asyncio

import asyncio_datagram

import time


_LOGGER = logging.getLogger(__name__)

class Error(Exception):
	pass

class InvalidTransponderResponseError(Error):
	pass


class InvalidSourceError(Error):
	pass

class InvalidModeError(Error):
	pass


class EmotivaNotifier(object):
	def __init__(self):
		self._devs = {}

	async def _async_register(self, ip, port, callback):

		if ip not in self._devs:
			self._devs[ip] = callback

		stream = await asyncio_datagram.bind((ip, port))

		self._stream = stream

		while True:
			data, remote_addr = await stream.recv()

			_LOGGER.debug("### Received notification %s", data)

			cb = self._devs[ip]

			cb(data)

			await asyncio.sleep(0.1)

	def run(self):
		_LOGGER.debug("Run Called")
		pass

		  
class Emotiva(object):
	XML_HEADER = '<?xml version="1.0" encoding="utf-8"?>'.encode('utf-8')
	DISCOVER_REQ_PORT = 7000
	DISCOVER_RESP_PORT = 7001

	NOTIFY_EVENTS = set([
			'power', 'zone2_power', 'source', 'mode', 'volume', 'audio_input',
			'audio_bitstream', 'video_input', 'video_format',
	]).union(set(['input_%d' % d for d in range(1, 9)]))
	
	__notifier = EmotivaNotifier()


	def __init__(self, ip, transp_xml = "", _ctrl_port = None, _notify_port = None, 
							 _name = 'Unknown_name', _model = 'Unknown_model', _proto_ver = None, _info_port = None, _setup_port = None,
								events = NOTIFY_EVENTS ):

		self._ip = ip
		self._name = _name
		self._model = _model
		self._proto_ver = _proto_ver
		self._ctrl_port = _ctrl_port
		self._notify_port = _notify_port
		self._info_port = _info_port
		self._setup_port_tcp = _setup_port
		self._volume_max = 11
		self._volume_min = -96
		self._volume_range = self._volume_max - self._volume_min
		self._ctrl_sock = None
		self._udp_stream = None
		self._update_cb = None
		self._modes = {"Stereo" :       ['stereo', 'mode_stereo', True],
							"Direct":             ['direct', 'mode_direct', True],
							"Dolby":     ['dolby', 'mode_dolby', True],
							"DTS":                ['dts', 'mode_dts', True], 
							"All Stereo" :        ['all_stereo', 'mode_all_stereo', True],
							"Auto":               ['auto', 'mode_auto', True],
							"Reference Stereo" :  ['reference_stereo', 'mode_ref_stereo',True],
							"Surround":           ['surround_mode', 'mode_surround', True],
							"PLIIx Music":				['dolby', 'mode_pliix_music', True ],
							"PLIIx Movie":				['dolby', 'mode_pliix_movie', True ],
							"dts Neo:6 Cinema":		['dts', 'mode_dts_cinema', True],
							"dts Neo:6 Music":		['dts', 'mode_dts_music', True]}
		self._events = events

		# current state
		self._current_state = dict(((ev, None) for ev in self._events))
		self._current_state.update(dict(((m[1], None) for m in self._modes.values())))
		# Add states for the hidden music modes
		self._current_state.update({'selected_movie_music':None,
							  'mode_music':'Music',
							  'mode_movie':'Movie'})
		self._sources = {}

		self._muted = False

		if not self._ctrl_port or not self._notify_port:
			self.__parse_transponder(transp_xml)

		self._local_ip = self._get_local_ip()
 
		if not self._ctrl_port or not self._notify_port:
			raise InvalidTransponderResponseError("Coulnd't find ctrl/notify ports")
		
		
	def _get_local_ip(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.connect((self._ip, self._ctrl_port))
		_local_ip = sock.getsockname()[0]
		sock.close()
		_LOGGER.debug("Local IP: ", _local_ip)
		return _local_ip

	def connect(self):
		
		self._ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self._ctrl_sock.bind(('', self._ctrl_port))
		self._ctrl_sock.settimeout(0.5)
  		
		
	async def run_notifier(self):
		_LOGGER.debug("Setting up Notify Listener")
		await self.__notifier._async_register(self._local_ip, self._notify_port, self._notify_handler)

	async def async_subscribe_events(self):
		_LOGGER.debug("Subscribing to %s", self._events)
		await self._subscribe_events(self._events)

	async def async_unsubscribe_events(self):
		await self._unsubscribe_events(self._events)


	def _notify_handler(self, data):
		#_LOGGER.debug("Notify Handler received: %s", data)
		resp = self._parse_response(data)
		self._handle_status(resp)

	async def _subscribe_events(self, events):
		msg = self.format_request('emotivaSubscription',
								[(ev, None) for ev in events])
		await self._async_send_request(msg, ack=True)

	async def _unsubscribe_events(self, events):
		msg = self.format_request('emotivaUnsubscribe',
								[(ev, None) for ev in events])
		await self._async_send_request(msg, ack=True)

	def disconnect(self):
		self._ctrl_sock.close()


	async def async_update_status(self, events, _proto_ver = 2.0):
		msg = self.format_request('emotivaUpdate',
															[(ev, {}) for ev in events],
															{'protocol':"3.0"} if _proto_ver == 3 else {})
															#{})
		await self._async_send_request(msg, ack=True)

	def update_status(self, events, _proto_ver = 2.0):
		msg = self.format_request('emotivaUpdate',
															[(ev, {}) for ev in events],
															{'protocol':"3.0"} if _proto_ver == 3 else {})
															#{})
		self._send_request(msg, ack=True)


	def _send_request(self, req, ack=False, process_response=True):

		self.connect()

		try:
			self._ctrl_sock.sendto(req, (self._ip, self._ctrl_port))
		except:
			#try and reconnect and send again
			_LOGGER.debug("Connection lost.  Attepting to reconnect")
			try:
				self.connect()
				self._ctrl_sock.sendto(req, (self._ip, self._ctrl_port))
			except:
				_LOGGER.debug("Cannot reconnect to processor")
			
		while ack:
			try:
				_resp_data, (ip, port) = self._ctrl_sock.recvfrom(4096)
				#
				# _LOGGER.debug("Response on ack: %s",_resp_data)
				if process_response == True:
					resp = self._parse_response(_resp_data)
					self._handle_status(resp)
				break
			except socket.timeout:
				_LOGGER.debug("socket.timeout on ack")
				break

		self.disconnect()

	async def udp_connect(self):
		self._udp_stream = await asyncio_datagram.connect((self._ip, self._ctrl_port),(self._local_ip,self._ctrl_port))
	
	async def udp_disconnect(self):
		self._udp_stream.close()

	async def _udp_client(self, req, ack):

		#_stream = self._udp_stream

		# _stream = await asyncio_datagram.connect((self._ip, self._ctrl_port),(self._local_ip,self._ctrl_port))

		# _stream = await asyncio_datagram.bind((self._local_ip,self._ctrl_port), reuse_port=True)

		try: 
			await self._udp_stream.send(req)
		except:
			try:
				_LOGGER.debug("Connection lost.  Attepting to reconnect")
				self.udp_connect()
				await self._udp_stream.send(req)
			except:
				_LOGGER.debug("Cannot reconnect to processor")
				return

		# await _stream.send(command, (self._ip, self._ctrl_port))
		if ack:
			resp, remote_addr = await self._udp_stream.recv()
			_LOGGER.debug("_udp_client received: %s", resp.decode())
		else:
			resp = None
		
		# _stream.close()
		
		self._resp = resp
		
	async def _async_send_request(self, req, ack=False, process_response=True):
		
		await self._udp_client(req, ack)

		# _LOGGER.debug("_async_send_request received %s", self._resp)

		if ack and process_response:
			resp = self._parse_response(self._resp)
			self._handle_status(resp)

	async def _async_send_emotivacontrol(self, command, value):
		msg = self.format_request('emotivaControl', [(command, {'value': str(value),
														'ack':'yes'})])
		await self._async_send_request(msg, ack=True, process_response=False)	


	def _send_emotivacontrol(self, command, value):
		msg = self.format_request('emotivaControl', [(command, {'value': str(value),
														'ack':'yes'})])
		self._send_request(msg, ack=True, process_response=False)
	
	def __parse_transponder(self, transp_xml):
		# _LOGGER.debug("transp_xml %s", transp_xml)
		elem = transp_xml.find('name')
		if elem is not None: self._name = elem.text.strip()
		elem = transp_xml.find('model')
		if elem is not None: self._model = elem.text.strip()

		ctrl = transp_xml.find('control')
		elem = ctrl.find('version')
		if elem is not None: self._proto_ver = elem.text
		elem = ctrl.find('controlPort')
		if elem is not None: self._ctrl_port = int(elem.text)
		elem = ctrl.find('notifyPort')
		if elem is not None: self._notify_port = int(elem.text)
		elem = ctrl.find('infoPort')
		if elem is not None: self._info_port = int(elem.text)
		elem = ctrl.find('setupPortTCP')
		if elem is not None: self._setup_port_tcp = int(elem.text)

	def _handle_status(self, resp):
		for elem in resp:
			if elem.tag == "property":
				# v3 protocol style response, convert it to v2 style
				# _LOGGER.debug("Handling Protocol V3 xml")
				elem.tag = elem.get('name')
			if elem.tag not in self._current_state:
				_LOGGER.debug('Unknown element: %s' % elem.tag)
				continue
			val = (elem.get('value') or '').strip()
			visible = (elem.get('visible') or '').strip()
			#update mode status
			if (elem.tag.startswith('mode_') and visible != "true"):
				_LOGGER.debug(' %s is no longer visible' % elem.tag)
				for v in self._modes.items():
					if(v[1][1] == elem.tag):
						v[1][2] = False
						self._modes.update({v[0]: v[1]})
			#do not 
			if (elem.tag.startswith('input_') and visible != "true"):
				continue
			if elem.tag == 'volume':
				if val == 'Mute':
					self._muted = True
					continue
				self._muted = False
				# fall through
			if val:
				self._current_state[elem.tag] = val
			if elem.tag.startswith('input_'):
				num = elem.tag[6:]
				self._sources[val] = int(num)
		if self._update_cb:
			self._update_cb()

	def set_update_cb(self, cb):
		self._update_cb = cb

	@classmethod
	def discover(cls, version = 2):
		resp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		try:
			resp_sock.bind(('', cls.DISCOVER_RESP_PORT))
		except:
			time.sleep(1)
			try:
				resp_sock.bind(('', cls.DISCOVER_RESP_PORT))
			except:
				_LOGGER.error("Cannot bind to discovery port")
				return []

		resp_sock.settimeout(0.5)

		req_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		req_sock.bind(('', 0))
		req_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		if version == 3:
			req = cls.format_request('emotivaPing', {}, {'protocol': "3.0"})
		else:
			req = cls.format_request('emotivaPing')
		#_LOGGER.debug("Broadcast Req: %s", req)
		req_sock.sendto(req, ('<broadcast>', cls.DISCOVER_REQ_PORT))

		devices = []
		while True:
			try:
				_resp_data, (ip, port) = resp_sock.recvfrom(4096)
				# _LOGGER.debug("Parsing ping response")
				resp = cls._parse_response(_resp_data)
				devices.append((ip, resp))
			except socket.timeout:
				break
		return devices

	@classmethod
	def _parse_response(cls, data):
		#_LOGGER.debug("parse_response: %s", data)
		try: 
			parser = etree.XMLParser(ns_clean=True, recover = True)
			root = etree.XML(data, parser)
		except etree.ParseError:
			_LOGGER.error("Malformed XML")
			_LOGGER.error(data)
			root = ""
		return root

	@classmethod
	def format_request(cls, pkt_type, req = {}, pkt_attrs = {}):
		"""
		req is a list of 2-element tuples with first element being the command,
		and second being a dict of parameters. E.g.
		('power_on', {'value': "0"})

		pkt_attrs is a dictionary containing element attributes. E.g.
		{'protocol': "3.0"}
		"""
		output = cls.XML_HEADER
		builder = etree.TreeBuilder()
		builder.start(pkt_type,pkt_attrs)
		for cmd, params in req:
			builder.start(cmd, params)
			builder.end(cmd)
		builder.end(pkt_type)
		pkt = builder.close()
		return output + etree.tostring(pkt)

	@property
	def name(self):
		return self._name

	@property
	def model(self):
		return self._model

	@property
	def address(self):
		return self._ip

	@property
	def power(self):
		if self._current_state['power'] == 'On':
			return True
		return False

	#@power.setter
	#def power(self, onoff):
	#	cmd = {True: 'power_on', False: 'power_off'}[onoff]
	#	self._send_emotivacontrol(cmd,0)
		
	@property
	def volume_level(self):
		if self._current_state['volume'] != None:
			_vol = float(self._current_state['volume'].replace(" ", ""))
			return ((_vol-self._volume_min)/self._volume_range)
		return None

	@property
	def volume(self):
		if self._current_state['volume'] != None:
			return float(self._current_state['volume'].replace(" ", ""))
		return None

	#@volume.setter
	#def volume(self, value):
	#	self._send_emotivacontrol('set_volume',value)

	async def _async_volume_step(self, incr):
		await self._async_send_emotivacontrol('volume', incr)

	async def async_volume_set(self, vol):
		await self._async_send_emotivacontrol('set_volume', vol)

	async def async_volume_up(self):
		await self._async_volume_step(1)

	async def async_volume_down(self):
		await self._async_volume_step(-1)

	async def async_mute_toggle(self):
		await self._async_send_emotivacontrol('mute', '0')
	
	async def async_set_mute(self, enable):
		mute_cmd = {True: 'mute_on', False: 'mute_off'}[enable]
		await self._async_send_emotivacontrol(mute_cmd,'0')

	async def async_turn_off(self):
		await self._async_send_emotivacontrol("power_off",'0')

	async def async_turn_on(self):
		await self._async_send_emotivacontrol("power_on",'0')

	def set_input(self, source):
		self._send_emotivacontrol(source, 0)

	def send_command(self, command, value):
		self._send_emotivacontrol(command,value)

	async def async_send_command(self, command, value):
		await self._async_send_emotivacontrol(command,value)

	async def async_send_command_no_ack(self, command, value):

		req = self.format_request('emotivaControl', [(command, {'value': str(value),
														'ack':'no'})])
		
		
		_LOGGER.debug("IP : %s, Port %d, req %s",self._ip, self._ctrl_port,req )

		_stream = await asyncio_datagram.connect((self._ip, self._ctrl_port))

		await _stream.send(req)

		_stream.close()


	@property
	def mute(self):
		return self._muted

	#@mute.setter
	#def mute(self, enable):
	#	mute_cmd = {True: 'mute_on', False: 'mute_off'}[enable]
	#	self._send_emotivacontrol(mute_cmd,0)

	@property
	def sources(self):
		return tuple(self._sources.keys())

	@property
	def source(self):
		return self._current_state['source']

	#@source.setter
	#def source(self, val):
	#	if val not in self._sources:
	#		raise InvalidSourceError('Source "%s" is not a valid input' % val)
	#	elif self._sources[val] is None:
	#		raise InvalidSourceError('Source "%s" has bad value (%s)' % (
	#				val, self._sources[val]))
	#	self._send_emotivacontrol('source_%d' % self._sources[val],0)
 
	async def async_set_source(self, val):
		if val not in self._sources:
			raise InvalidSourceError('Source "%s" is not a valid input' % val)
		elif self._sources[val] is None:
			raise InvalidSourceError('Source "%s" has bad value (%s)' % (
					val, self._sources[val]))
		await self._async_send_emotivacontrol('source_%d' % self._sources[val],"0")
	
	@property
	def modes(self):
		#we return only the modes that are active
		return tuple(dict(filter(lambda elem: elem[1][2] == True, self._modes.items())).keys())
	
	@property
	def mode(self):
		return self._current_state['mode']

	#@mode.setter
	#def mode(self, val):
	#	if val not in self._modes:
	#		raise InvalidModeError('Mode "%s" does not exist' % val)
	#	elif self._modes[val][0] is None:
	#		raise InvalidModeError('Mode "%s" has bad value (%s)' % (
	#				val, self._modes[val][0]))
	#	self._send_emotivacontrol(self._modes[val][0],0)

	async def async_set_mode(self, val):
		if val not in self._modes:
			raise InvalidModeError('Mode "%s" does not exist' % val)
		elif self._modes[val][0] is None:
			raise InvalidModeError('Mode "%s" has bad value (%s)' % (
					val, self._modes[val][0]))
		await self._async_send_emotivacontrol(self._modes[val][0],"0")
		if "Music" in val and self._current_state['selected_movie_music'] != "Music":
			await asyncio.sleep(0.5)
			await self._async_send_emotivacontrol("music",'0')
		elif ("Movie" in val or "Cinema" in val) and self._current_state['selected_movie_music'] != "Movie":
			await asyncio.sleep(0.5)
			await self._async_send_emotivacontrol("movie",'0')



