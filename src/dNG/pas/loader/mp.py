# -*- coding: utf-8 -*-
##j## BOF

"""
MediaProvider
A device centric multimedia solution
----------------------------------------------------------------------------
(C) direct Netware Group - All rights reserved
http://www.direct-netware.de/redirect.py?mp;loader

The following license agreement remains valid unless any additions or
changes are being made by direct Netware Group in a written form.

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along with
this program; if not, write to the Free Software Foundation, Inc.,
59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
----------------------------------------------------------------------------
http://www.direct-netware.de/redirect.py?licenses;gpl
----------------------------------------------------------------------------
#echo(mpLoaderVersion)#
#echo(__FILEPATH__)#
"""

from argparse import ArgumentParser
from time import time

from dNG.pas.data.settings import Settings
from dNG.pas.data.tasks.database import Database as DatabaseTasks
from dNG.pas.data.tasks.memory import Memory as MemoryTasks
from dNG.pas.loader.cli import Cli
from dNG.pas.module.named_loader import NamedLoader
from dNG.pas.net.bus.client import Client as BusClient
from dNG.pas.net.bus.server import Server as BusServer
from dNG.pas.net.http.server_implementation import ServerImplementation as HttpServer
from dNG.pas.plugins.hook import Hook
from .bus_mixin import BusMixin

class Mp(Cli, BusMixin):
#
	"""
"Mp" manages the MediaProvider process.

:author:     direct Netware Group
:copyright:  (C) direct Netware Group - All rights reserved
:package:    vp
:subpackage: loader
:since:      v0.1.00
:license:    http://www.direct-netware.de/redirect.py?licenses;gpl
             GNU General Public License 2
	"""

	# pylint: disable=unused-argument

	def __init__(self):
	#
		"""
Constructor __init__(Mp)

:since: v0.1.00
		"""

		Cli.__init__(self)
		BusMixin.__init__(self)

		self.cache_instance = None
		"""
Cache instance
		"""
		self.server = None
		"""
Server thread
		"""

		self.arg_parser = ArgumentParser()
		self.arg_parser.add_argument("--additionalSettings", action = "store", type = str, dest = "additional_settings")
		self.arg_parser.add_argument("--stop", action = "store_true", dest = "stop")

		Cli.register_run_callback(self._on_run)
		Cli.register_shutdown_callback(self._on_shutdown)
	#

	def _on_run(self, args):
	#
		"""
Callback for execution.

:param args: Parsed command line arguments

:since: v1.0.0
		"""

		Settings.read_file("{0}/settings/pas_global.json".format(Settings.get("path_data")))
		Settings.read_file("{0}/settings/pas_core.json".format(Settings.get("path_data")), True)
		Settings.read_file("{0}/settings/pas_http.json".format(Settings.get("path_data")))
		Settings.read_file("{0}/settings/pas_upnp.json".format(Settings.get("path_data")))
		Settings.read_file("{0}/settings/mp/server.json".format(Settings.get("path_data")))
		if (args.additional_settings != None): Settings.read_file(args.additional_settings, True)

		if (args.stop):
		#
			client = BusClient("mp_bus")

			pid = client.request("dNG.pas.Status.getOSPid")
			client.request("dNG.pas.Status.stop")

			client.disconnect()

			self._wait_for_os_pid(pid)
		#
		else:
		#
			self.cache_instance = NamedLoader.get_singleton("dNG.pas.data.Cache", False)
			if (self.cache_instance != None): Settings.set_cache_instance(self.cache_instance)

			self.log_handler = NamedLoader.get_singleton("dNG.pas.data.logging.LogHandler", False)

			if (self.log_handler != None):
			#
				Hook.set_log_handler(self.log_handler)
				NamedLoader.set_log_handler(self.log_handler)
			#

			Hook.load("http")
			Hook.load("mp")
			Hook.load("tasks")
			Hook.register("dNG.pas.Status.getOSPid", self.get_os_pid)
			Hook.register("dNG.pas.Status.getTimeStarted", self.get_time_started)
			Hook.register("dNG.pas.Status.getUptime", self.get_uptime)
			Hook.register("dNG.pas.Status.stop", self.stop)

			self.server = BusServer("mp_bus")
			self._set_time_started(time())

			http_server = HttpServer.get_instance()

			if (http_server != None):
			#
				Hook.register("dNG.pas.Status.onStartup", http_server.start)
				Hook.register("dNG.pas.Status.onShutdown", http_server.stop)

				database_tasks = DatabaseTasks.get_instance()
				Hook.register("dNG.pas.Status.onStartup", database_tasks.start)
				Hook.register("dNG.pas.Status.onShutdown", database_tasks.stop)

				memory_tasks = MemoryTasks.get_instance()
				Hook.register("dNG.pas.Status.onStartup", memory_tasks.start)
				Hook.register("dNG.pas.Status.onShutdown", memory_tasks.stop)

				upnp_control_point = NamedLoader.get_singleton("dNG.pas.net.upnp.ControlPoint")
				Hook.register("dNG.pas.Status.onStartup", upnp_control_point.start)
				Hook.register("dNG.pas.Status.onShutdown", upnp_control_point.stop)

				if (self.log_handler != None): self.log_handler.info("mp starts listening", context = "mp_server")
				Hook.call("dNG.pas.Status.onStartup")

				self.set_mainloop(self.server.run)
			#
		#
	#

	def _on_shutdown(self):
	#
		"""
Callback for shutdown.

:since: v0.1.00
		"""

		Hook.call("dNG.pas.Status.onShutdown")

		if (self.cache_instance != None): self.cache_instance.disable()
		Hook.free()
	#

	def stop(self, params = None, last_return = None):
	#
		"""
Stops the running server instance.

:param params: Parameter specified
:param last_return: The return value from the last hook called.

:return: (None) None to stop communication after this call
:since:  v0.1.00
		"""

		if (self.server != None):
		#
			self.server.stop()
			self.server = None

			if (self.log_handler != None): self.log_handler.info("mp stopped listening", context = "mp_server")
		#

		return last_return
	#
#

##j## EOF