#!/usr/bin/python3
import os, logging, subprocess

# import library components
from lib.config import Config
from lib.source import Source
from lib.localsink import LocalSink
from lib.rtmpsink import RtmpSink
from lib.mixer import Mixer

class Pipeline(object):
	def __init__(self):
		self.log = logging.getLogger('Pipeline')

		sources = Config.options('sources')
		if len(sources) < 1:
			raise RuntimeError('At least one Source must be configured!')

		self.mixer = Mixer()

		if Config.has_option('output', 'rtmp'):
			self.sink = RtmpSink()
		else:
			self.sink = LocalSink()

		self.sources = []
		for name, url in Config.items('sources'):
			if name.endswith('_v'):
				self.log.debug("adding as inputvideo")
				try:
					self.sources.append(Source(name, url, "inputvideo"))
				except:
					self.log.warning("section inputvideo not present in config!")
			else:
				self.log.debug("adding as input")
				self.sources.append(Source(name, url))
