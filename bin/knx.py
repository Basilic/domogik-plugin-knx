#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

KNX bus

Implements
==========

- KnxManager

@author: Fritz <fritz.smh@gmail.com> Basilic <Basilic3@hotmail.com>...
@copyright: (C) 2007-2012 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

from domogik_packages.plugin_knx.lib.knx import KNXException
from domogik_packages.plugin_knx.lib.knx import KNX
from domogik_packages.plugin_knx.lib.knx import decodeKNX
from domogik_packages.plugin_knx.lib.knx import encodeKNX
from domogik.common.plugin import Plugin
from domogikmq.message import MQMessage
import threading
import subprocess

sensors_list={}
commands_list={}
datapoint_list={}

class KNXManager(Plugin):
	
	def __init__(self):
		""" Implements a listener for KNX command messages 
			and launch background listening for KNX events
		"""
		# Declare the plugin name 
		Plugin.__init__(self,name='knx')  

        # check if the plugin is configured. If not, this will stop the plugin and log an error
		if not self.check_configured():
			return  #if plugin is not configured stop initialisation 



		knx_device = str(self.get_config('knx'))
		knx_cache = self.get_config('knx')
		self.knx_host = self.get_config('host_ip') #get ip address of the daemon
		self.knx_host_type = self.get_config('host_type') #get the type of daemon EIBD or KNXTOOL
		self.log.info('Host ip: |%s|' %self.knx_host)
		self.log.info('Host type: |%s|' %self.knx_host_type)
		self.device=self.get_device_list(quit_if_no_device = True) # get all device list
		
		self.knx = KNX(self.log, self.send_pub_data, self.knx_host, self.knx_host_type)
		try:
			self.log.info("Start listening to KNX")
			self.knx_listen = threading.Thread(None,
                                          self.knx.listen,
                                          "listen_knx",
                                          (),
                                          {})
			self.knx_listen.start()
			self.register_thread(self.knx_listen)
		except KNXException as err:
			self.log.error(err.value)
			self.force_leave()
			return

		for item in self.device:
			self.log.info(item)
			if item["parameters"]["address_stat"]["value"] != "":
				for sensor in item["sensors"]:
					sensors_list[item["parameters"]["address_stat"]["value"]]=item["sensors"][sensor]["id"]
					if datapoint_list.get(item["parameters"]["address_stat"]["value"],"Default")=="Default":
						datapoint_list[item["parameters"]["address_stat"]["value"]]=item["parameters"]["Stat_Datapoint"]["value"]
					else:
						if item["parameters"]["address_cmd"]["value"] != "":
							sensors_list[item["parameters"]["address_cmd"]["value"]]=item["sensors"]["state"]["id"]

			if item["parameters"]["address_cmd"]["value"] != "":
				for command in item["commands"]:
					commands_list[item["commands"][command]["id"]]=item["parameters"]["address_cmd"]["value"]
				if datapoint_list.get(item["parameters"]["address_cmd"]["value"],"Default")=="Default":
					datapoint_list[item["parameters"]["address_cmd"]["value"]]=item["parameters"]["Cmd_Datapoint"]["value"]
       		self.read_sensors() 
		self.log.info('Sensor list: %s' %sensors_list)
		self.log.info('Command List: %s' %commands_list)
		self.log.info('Datapoint dict: %s' %datapoint_list)
		self.register_cb_update_devices(self.reload_devices)
		self.log.info("Plugin ready :)")
		
		self.ready()


	def reload_devices(self,devices):
		""" Routine call when the devices list is updated
		"""
		sensors_list={}
		commands_list={}
		datapoint_list={}
		self.device=self.get_device_list(quit_if_no_device = True) 
		for item in self.device:
			if item["parameters"]["address_stat"]["value"] != "":
				sensors_list[item["parameters"]["address_stat"]["value"]]=item["sensors"]["state"]["id"]
				if datapoint_list.get(item["parameters"]["address_stat"]["value"],"Default")=="Default":
					datapoint_list[item["parameters"]["address_stat"]["value"]]=item["parameters"]["Stat_Datapoint"]["value"]
				else:
					if item["parameters"]["address_cmd"]["value"] != "":
						sensors_list[item["parameters"]["address_cmd"]["value"]]=item["sensors"]["state"]["id"]

			if item["parameters"]["address_cmd"]["value"] != "":
				commands_list[item["commands"]["switch"]["id"]]=item["parameters"]["address_cmd"]["value"]
				if datapoint_list.get(item["parameters"]["address_cmd"]["value"],"Default")=="Default":
					datapoint_list[item["parameters"]["address_cmd"]["value"]]=item["parameters"]["Cmd_Datapoint"]["value"]
		        
		self.log.info('Sensor list: %s' %sensors_list)
		self.log.info('Command List: %s' %commands_list)
		self.log.info('Datapoint dict: %s' %datapoint_list)
		self.read_sensors()

	def read_sensors(self):
		""" Routine call to read all sensors on the bus
		"""
		for sensor in sensors_list:
			command = "groupread ip:%s %s" %(self.knx_host, sensor)
			if self.knx_host_type == "KNXTOOL":
				command ="knxtool " + command 
			subp=subprocess.Popen(command, shell=True)
	
	def send_pub_data(self, data):
		""" Send message on MQ when a message is detect by the knx pipe
		"""
		### Identify the sender of the message
		self.log.info("Receive knx message from pipe")
		self.log.info(data)
		#identification of the sender
		sender = data[data.find('from')+4:data.find('to')-1].strip()
		groups = 'None'
		val = 'None'
		self.log.info('senser: %s' %sender)
		if sender!="pageinatio":
			command = data[0:4]  
			lignetest=""
			groups = data[data.find('to')+2:data.find(':')]
			groups =groups.strip()
			self.log.info('groups |%s|' %groups)
			### Search the sender in the config list
			i=0
			lignetest=""
			self.log.info(sensors_list.get(groups,"Default"))
			if sensors_list.get(groups,"Default")!="Default" and (command == "Writ" or command == "Resp"):
				sensor_id=sensors_list[groups]
				datatype=datapoint_list[groups]
				val=data[data.find(':')+1:-1]
				val = val.strip()
				val=decodeKNX(datatype,val)
				data={}
				data[sensor_id]=val
				self.log.info( 'Sensor: %s value %s' %(sensor_id,data))
				try:
					self._pub.send_event('client.sensor' ,  data)
					return True, None
				except:
					self.log.info(" Error to send MQ")
					return False, None

	def on_mdp_request(self, msg):
		""" Routine call when a MQ message arrive
		"""
		Plugin.on_mdp_request(self,msg)
		command=""
		self.log.info("Test: %s" %msg)
		if msg.get_action() == "client.cmd":        
			data=msg.get_data()
			self.log.info(data)
			cmdadr = commands_list[data["command_id"]]
			reason = None
			status = True
			val= data['value']
			
			self.log.info(datapoint_list)
			command_id = data['device_id']
			datatype = datapoint_list[cmdadr]
			value=encodeKNX(datatype, val)
			data_type=value[0]
			valeur=value[1]   
			
			if data_type=="s":
				command="groupswrite ip:%s %s %s" %(self.knx_host,cmdadr, valeur)
				if self.knx_host_type == "KNXTOOL":
					command = "knxtool " + command
			  
			if data_type=="l":
				command="groupwrite ip:%s %s %s" %(self.knx_host,cmdadr, valeur)
				if self.knx_host_type == "KNXTOOL":
					command = "knxtool " + command
			if command != "":
				subp=subprocess.Popen(command, shell=True)
			else:
				self.log.info("erreur command non définir, type cmd= %s" %type_cmd)
				reason = "Command not define"
				status = False

			self.send_rep_ack(status, reason, command_id) ;
		   
	def send_rep_ack(self, status, reason, cmd_id):
		""" Send ACQ to a command via MQ
		"""
		#self.log.info(u"==> Reply ACK to command id '%s' for device '%s'" % (cmd_id, dev_name))
		reply_msg = MQMessage()
		reply_msg.set_action('client.cmd.result')
		reply_msg.add_data('status', status)
		reply_msg.add_data('reason', reason)
		self.reply(reply_msg.get())

if __name__ == "__main__":
    INST = KNXManager()
