#!/usr/bin/python3
import logging
from gi.repository import Gst

from lib.config import Config
from lib.tcpmulticonnection import TCPMultiConnection

class AVRawOutput(TCPMultiConnection):
	def __init__(self, channel, port):
		self.log = logging.getLogger('AVRawOutput['+channel+']')
		super().__init__(port)

		self.channel = channel

		pipeline = """
			interaudiosrc channel=audio_{channel} !
			{acaps} !
			queue !
			mux.

			intervideosrc channel=video_{channel} !
			{vcaps} !
			queue !
			mux.

			matroskamux
				name=mux
				streamable=true
				writing-app=Voctomix-AVRawOutput !

			multifdsink
				buffers-max=500
				sync-method=next-keyframe
				name=fd
		""".format(
			channel=self.channel,
			acaps=Config.get('mix', 'audiocaps'),
			vcaps=Config.get('mix', 'videocaps')
		)
		self.log.debug('Creating Output-Pipeline:\n%s', pipeline)
		self.outputPipeline = Gst.parse_launch(pipeline)

		self.log.debug('Binding Error & End-of-Stream-Signal on Output-Pipeline')
		self.outputPipeline.bus.add_signal_watch()
		self.outputPipeline.bus.connect("message::eos", self.on_eos)
		self.outputPipeline.bus.connect("message::error", self.on_error)

		self.log.debug('Launching Output-Pipeline')
		self.outputPipeline.set_state(Gst.State.PLAYING)

	def on_accepted(self, conn, addr):
		self.log.debug('Adding fd %u to multifdsink', conn.fileno())
		fdsink = self.outputPipeline.get_by_name('fd')
		fdsink.emit('add', conn.fileno())

		def on_disconnect(multifdsink, fileno):
			if fileno == conn.fileno():
				self.log.debug('fd %u removed from multifdsink', fileno)
				self.close_connection(conn)

		def on_about_to_disconnect(multifdsink, fileno, status):
			if fileno == conn.fileno() and status == 3: # Gst.MultiHandleSinkClientStatus.Slow
				self.log.warning('about to remove fd %u from multifdsink because it is too slow!', fileno)

		fdsink.connect('client-fd-removed', on_disconnect)
		fdsink.connect('client-removed', on_about_to_disconnect)

	def on_eos(self, bus, message):
		self.log.debug('Received End-of-Stream-Signal on Output-Pipeline')

	def on_error(self, bus, message):
		self.log.debug('Received Error-Signal on Output-Pipeline')
		(error, debug) = message.parse_error()
		self.log.debug('Error-Details: #%u: %s', error.code, debug)
