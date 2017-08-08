#!/usr/bin/python
#-*- coding: utf-8 -*-create_device.py

### configuration ######################################
DEVICE_NAME_MIRROR = "test_knx"

from domogik.tests.common.testdevice import TestDevice
from domogik.common.utils import get_sanitized_hostname

plugin = 'knx'

def create_device():
    ### create the device, and if ok, get its id in device_id
    client_id  = "plugin-{0}.{1}".format(plugin, get_sanitized_hostname())
    print "Creating the knx device..."
    td = TestDevice()
    params = td.get_params(client_id, "mirror")
        # fill in the params
    params["device_type"] = "switch"
    params["name"] = DEVICE_NAME_MIRROR
    params["Cmd_Datapoint"] = "1.001"
    params["Stat_Datapoint"] = "1.001"
    params["address_cmd"] = "1/1/1"
    params["address_stat"] = "1/0/1"


    # go and create
    td.create_device(params)
    print "Device KNX {0} configured".format(DEVICE_NAME_KAROTZ)

    
if __name__ == "__main__":
    create_device()


