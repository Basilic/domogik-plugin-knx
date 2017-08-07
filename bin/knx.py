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

listknx=[]
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
		self.log.info('Host ip: %s' %self.knx_host)
		self.log.info('Host type: %s' %self.knx_host_type)
		self.device=self.get_device_list(quit_if_no_device = True) # get all device list
		
		self.knx = KNX(self.log, self.send_pub_data)
		try:
			self.log.info("Start listening to KNX")
			knx_listen = threading.Thread(None,
                                          self.knx.listen,
                                          "listen_knx",
                                          (),
                                          {})
			knx_listen.start()
		except KNXException as err:
			self.log.error(err.value)
			self.force_leave()
			return

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
		self.log.info("Plugin ready :)")
		
		self.ready()

	def send_pub_data(self, data):
		""" Send message on MQ when a message is detect by the knx pipe
		"""
		### Identify the sender of the message
		self.log.info("Receive knx message from pipe")

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
			if sensors_list.get(groups,"Default")!="Default":
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

	def on_mq_request(self, msg):
		Plugin.on_mdp_request(self,msg)
		command=""
		print message
		if msg.get_action() == "client.cmd":        
			valeur=data["value"] 
			command="knxtool groupswrite ip:%s 1/1/4 %s" %(self.knx_host,valeur)
			try:
				type_cmd = message.data['command'] #type_cmd = "Write"
				groups = message.data['address']
				print groups
				lignetest=""
				valeur=message.data['value']
				print "Message XPL %s" %message
				for i in range(len(listknx)):
					if listknx[i].find(groups)>=0:
						lignetest=listknx[i]
						break
				print "ligne test=|%s|" %lignetest
			except Exception, e:
				lignetest=""
			   #si wirte groups_cmd/si read, groups stat
			if lignetest!="":
				datatype=lignetest[lignetest.find('datatype:')+9:lignetest.find(' adr_dmg')]
				cmdadr=lignetest[lignetest.find('adr_cmd:')+8:lignetest.find(' adr_stat')]
				command=""
			
			if type_cmd=="Write":
				valeur = message.data['value']
				val=valeur

				value=encodeKNX(datatype, val)
				data_type=value[0]
				valeur=value[1]   
			
			if data_type=="s":
				command="groupswrite ip:%s %s %s" %(self.knx_host,cmdadr, valeur)
			  
			if data_type=="l":
				command="groupwrite ip:%s %s %s" %(self.knx_host,cmdadr, valeur)

			
			if type_cmd == "Read":
				print("dmg Read")
				command="groupread ip:%s %s" %(self.knx_host,cmdadr)
			
			if type_cmd == "Response":
				print("dmg Response")
				data_type=message.data['type']
				valeur = message.data['value']

			if data_type=="s":
				command="groupsresponse ip:%s %s %s" %(self.knx_host,cmdadr,valeur)

			if data_type=="l":
				command="groupresponse ip:%s %s %s" %(self.knx_host,cmdadr,valeur)
			
			if command!="":
				if self.knx_host_type == "KNXTOOL":
					command= "knxtool %s" %command
				print "envoie de la command %s" %command
				subp=subprocess.Popen(command, shell=True)

			if command=="":
				print("erreur command non définir, type cmd= %s" %type_cmd)

	def send_rep_ack(self, status, reason, cmd_id, dev_name):
		""" Send ACQ to a command via MQ
		"""
		self.log.info(u"==> Reply ACK to command id '%s' for device '%s'" % (cmd_id, dev_name))
		reply_msg = MQMessage()
		reply_msg.set_action('client.cmd.result')
		reply_msg.add_data('status', status)
		reply_msg.add_data('reason', reason)
		self.reply(reply_msg.get())

if __name__ == "__main__":
    INST = KNXManager()
