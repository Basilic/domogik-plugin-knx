
#!/usr/bin/python
#-*- coding: utf-8 -*-

### configuration ###########################################
plugin = "mirror"
########################################################

import json
import sys
import os
from domogik.common.packagejson import PackageJson

json_file = "/var/lib/domogik/domogik_packages/plugin_{0}/info.json".format(plugin)
if os.path.exists(json_file) :
    json_file = os.path.realpath(json_file)
    data = json.load(open(json_file))
    print data
    print "Package validation ..."
    p = PackageJson(path=json_file)
    if p.validate() == False :
        print "*** Error json validation :{0}".format(json_file)
    else :
        print "Json is validate :{0}".format(json_file)
else :
    print "*** Error *** Don't find file :{0}".format(json_file)
