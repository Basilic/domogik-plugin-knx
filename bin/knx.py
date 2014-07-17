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

#from urllib import *
from domogik.xpl.common.xplconnector import Listener
from domogik.xpl.common.plugin import XplPlugin
from domogik.xpl.common.xplmessage import XplMessage
#from domogik.xpl.common.queryconfig import Query
from domogik_packages.plugin_knx.lib.knx import KNXException
from domogik_packages.plugin_knx.lib.knx import KNX
from domogik_packages.plugin_knx.lib.knx import decodeKNX
from domogik_packages.plugin_knx.lib.knx import encodeKNX
#from domogik.common.configloader import *

import threading
import subprocess

listknx=[]

class KNXManager(XplPlugin):
    """ Implements a listener for KNX command messages 
        and launch background listening for KNX events
    """

    def __init__(self):
        """ Create listener and launch bg listening
        """
        XplPlugin.__init__(self, name = 'knx')

   
        # Configuration : KNX device
       # self._config = Query(self.myxpl, self.log)
#        device = self._config.query('knx', 'device')

        ### Create KNX object
        try:
            self.knx = KNX(self.log, self.send_xpl)
            self.log.info("Open KNX")
#            self.knx.open(device)

        except KNXException as err:
            self.log.error(err.value)
            print(err.value)
            self.force_leave()
            return

        ### Start listening 
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
            print(err.value)
            self.force_leave()
            return


        ### Create listeners for commands
        self.log.info("Creating listener for KNX")
        Listener(self.knx_cmd, self.myxpl,{'schema':'knx.basic'})
        self.add_stop_cb(self.knx.close)
        self.enable_hbeat()


	self.device=self.get_device_list(quit_if_no_device = True)
	print len(self.device)
	for item in self.device:
		ligne="datatype:"+item["parameters"]["Cmd_Datapoint"]["value"]
		ligne = ligne + " adr_dmg:"+ item["name"]
		ligne = ligne + " adr_cmd:"+ item["parameters"]["address1"]["value"]
		ligne = ligne +" adr_stat:"+ item["parameters"]["address2"]["value"]
		ligne = ligne +" dpt_stat:"+ item["parameters"]["Stat_Datapoint"]["value"]
		listknx.append(ligne)
		print ligne

	self.log.info("Plugin ready :)")
		

    def send_xpl(self, data):
        """ Send xpl-trig to give status change
        """
        ### Identify the sender of the message
        lignetest=""
        command = ""
        dmgadr =""
        msg_type=""
        test = ""
        val=""
        sender = 'None'
        sender = data[data.find('from')+4:data.find('to')-1]
        sender = sender.strip()
        groups = 'None'
        val = 'None'
        msg_type = 'None'
        command = 'None'
        if sender!="pageinatio":
           print "emetteur |%s|" %sender
           command = data[0:4]  
           lignetest=""
           groups = data[data.find('to')+2:data.find(':')]
           groups =":"+groups.strip()+" "
           print "groups |%s|" %groups

        ### Search the sender in the config list
           i=0
           lignetest=""
           for i in range(len(listknx)):
              if listknx[i].find(groups)>=0:
                 lignetest = listknx[i]
                 typeadr=lignetest[lignetest.find(groups)-4:lignetest.find(groups)]
                 typeadr=typeadr.replace("_","")
                 test=lignetest[lignetest.find('datatype:')+9:]
                 datatype=test[:test.find(' ')]
                 if typeadr=="stat":
                    if lignetest.find('dpt_stat')!=-1:
                       test=lignetest[lignetest.find('dpt_stat:')+9:]
                       datatype=test[:test.find(' ')]
                 test=lignetest[lignetest.find('adr_dmg:')+8:]
                 dmgadr=test[:test.find(' ')]
                 datatype=lignetest[lignetest.find('datatype:')+9:lignetest.find(' adr_dmg')]
                 msg=XplMessage()
                 msg.set_schema('knx.basic')

                 if command != 'Read':
                    val=data[data.find(':')+1:-1]
                    val = val.strip()
                    print "valeur=|%s|" %val
                    print "datapoint type=|%s|" %datatype
                    msg_type = datatype

                    val=decodeKNX(datatype,val)

                    print "Valeur decode=|%s|" %val

                    if command == 'Writ':
                       print("knx Write xpl-trig")
                       command = 'Write'
                       msg.set_type("xpl-trig")
                    if command == 'Resp':
                       print("knx Response xpl-stat")
                       command = 'Response'
                       if sender!="0.0.0":
                          msg.set_type("xpl-stat")
                       else:
                          msg.set_type("xpl-trig")

                 if command == 'Read':
                    print("knx Read xpl-cmnd")
                    if sender!="0.0.0":
                       msg.set_type("xpl-cmnd")
                    else:
                       msg.set_type("xpl-trig")

                 if sender!="0.0.0":
                    msg.add_data({'command' : command+' bus'})
                 else:
                    msg.add_data({'command': command+' ack'})

                 msg.add_data({'group' :  dmgadr})
                # msg.add_data({'type' :  msg_type})
                 msg.add_data({'data': val})
                 print "sender: %s typeadr:%s" %(sender, typeadr)

                 self.myxpl.send(msg)

    def knx_cmd(self, message):
        type_cmd = message.data['command']
        groups = message.data['group']
        groups = "adr_dmg:"+groups+" "
        lignetest=""
        valeur=message.data['data']
        print "Message XPL %s" %message
        for i in range(len(listknx)):
           if listknx[i].find(groups)>=0:
              lignetest=listknx[i]
              break
        print "ligne test=|%s|" %lignetest

           #si wirte groups_cmd/si read, groups stat
        if lignetest!="":
           datatype=lignetest[lignetest.find('datatype:')+9:lignetest.find(' adr_dmg')]
           cmdadr=lignetest[lignetest.find('adr_cmd:')+8:lignetest.find(' adr_stat')]
           command=""
           print "Command: |%s|" %type_cmd
           print "Groups: |%s|" %cmdadr
           print "datatype: |%s|" %datatype
           print "valeur avant codage: |%s|" %valeur

           if type_cmd=="Write":
              print("dmg Write %s") %type_cmd
              valeur = message.data['data']
              print "valeur avant modif:%s" %valeur
              val=valeur

              value=encodeKNX(datatype, val)
              data_type=value[0]
              valeur=value[1]   
              print "Valeur modifier |%s|" %valeur
              
              if data_type=="s":
                 command="groupswrite ip:127.0.0.1 %s %s" %(cmdadr, valeur)
              if data_type=="l":
                 command="groupwrite ip:127.0.0.1 %s %s" %(cmdadr, valeur)

           if type_cmd == "Read":
              print("dmg Read")
              command="groupread ip:127.0.0.1 %s" %cmdadr
           if type_cmd == "Response":
              print("dmg Response")
              data_type=message.data['type']
              valeur = message.data['data']
              if data_type=="s":
                 command="groupsresponse ip:127.0.0.1 %s %s" %(cmdadr,valeur)
              if data_type=="l":
                 command="groupresponse ip:127.0.0.1 %s %s" %(cmdadr,valeur)
           if command!="":
              print "envoie de la command %s" %command
              subp=subprocess.Popen(command, shell=True)
           if command=="":
              print("erreur command non définir, type cmd= %s" %type_cmd)


if __name__ == "__main__":
    INST = KNXManager()
