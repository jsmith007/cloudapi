#!/usr/bin/env python                     

import argparse
import supernova
import sys      
import pycurl   
import re       
import ConfigParser
import os          
import StringIO    
import json        

"""
http://docs.rackspace.com/loadbalancers/api/v1.0/clb-devguide/content/Service_Access_Endpoints-d1e517.html
"""                                                                                                       

def curlCall(url,method,authData,postData=None):
    VALID_METHODS = ["AUTH","GET","POST","DELETE"]
    if method.upper() not in VALID_METHODS:       
        print "Method " + str(method) + " is not valid in for curlCall"
        sys.exit(2)                                                    

    if authData is None:
        print "Call to authenticate missing data"
        sys.exit(2)                              

    curlClient = pycurl.Curl()
    curlResponse = StringIO.StringIO()
    curlClient.setopt(pycurl.URL,str(url))
    if method.upper() == "AUTH":          
        curlClient.setopt(pycurl.POST,1)  
        curlClient.setopt(pycurl.POSTFIELDS,authData)
        curlClient.setopt(pycurl.HTTPHEADER,["Content-Type: application/json"])

    else:
        if method.upper() == "POST":
            curlClient.setopt(pycurl.POST,1)
            if (postData):                  
                curlClient.setopt(pycurl.POSTFIELDS,postData)
        curlClient.setopt(pycurl.HTTPHEADER,["X-Auth-Token: " + authData,"Content-Type: application/json"])
                                                                                                           
    curlClient.setopt(pycurl.WRITEFUNCTION,curlResponse.write)                                             
    curlClient.perform()                                                                                   

    try:
        return json.loads(curlResponse.getvalue())
    except:
        print "Something broke - " + "response code: " + str(curlClient.getinfo(pycurl.HTTP_CODE)) + " url: " + curlClient.getinfo(pycurl.EFFECTIVE_URL) + " error: " + curlClient.errstr()
        sys.exit(2)

def main():

#    try:
#        opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
#    except getopt.error, msg:                                  
#        print msg                                              
#        print "for help use --help"                            
#        sys.exit(2)                                            
#    # process options                                          
#    for o, a in opts:                                          
#        if o in ("-h", "--help"):                              
#            print "No help yet"                                
#            sys.exit(0)                                        
#    # process arguments                                        
#    for arg in args:                                           
#        process(arg) # process() is defined elsewhere          

    possible_configs = [os.path.expanduser("~/.supernova"), '.supernova']
    novaCreds = ConfigParser.RawConfigParser()                           
    novaCreds.read(possible_configs)                                     
    if len(novaCreds.sections()) < 1:                                    
        print "No configuration found"                                   
        sys.exit(0)                                                      

    parser = argparse.ArgumentParser()
#    parser.add_argument('-l', '--list', action=_ListAction,
#                        dest='listenvs',                   
#                        help='list all configured environments')
#    parser.add_argument('-d', '--debug', action='store_true',   
#                        help='show novaclient debug output')    
    parser.add_argument('env',                                   
                        help=('environment to run nova against. '
                              'valid options: %s' %              
                              sorted(novaCreds.sections())))     
# CREATE ARGUMENTS 
#'--name=test', '--port=80', '--protocol=http', '--nodes=[{address=1.1.1.1,port=80,condition=enabled},{address=2.2.2.2,port=80,condition=enabled}]', '--virtualips=[{type=public}]'
#    parser.add_argument('--create-name',dest='createName')
#    parser.add_argument('--create-port',dest='createPort')
#    parser.add_argument('--create-protocol',dest='createProto')
#    parser.add_argument('--create-nodes',dest='createNodes')
#    parser.add_argument('--create-virtualip','--create-virtualips','--create-vips',dest='createVirtIp')

    namespace_args, extras = parser.parse_known_args()
    if len(extras) == 0:                  
        print "No action provided: "
        sys.exit(2)

    # get credentials from config file
    nova_re = re.compile(r"(^nova_|^os_|^novaclient)")
    raw_creds = novaCreds.items(namespace_args.env)   
    creds = {}                                        

    for param, value in raw_creds:
        # Skip parameters we're unfamiliar with
        if not nova_re.match(param):           
            continue                           
        param = param.upper()                  
        creds[param] =  value                  
                                               
    # authenticate                             

    authData =  "{{\"auth\":{{\"RAX-KSKEY:apiKeyCredentials\":{{\"username\":\"{0}\",\"apiKey\":\"{1}\"}}}}}}".format(creds['NOVA_USERNAME'],creds['NOVA_PASSWORD'])

    authResponseData = curlCall("https://identity.api.rackspacecloud.com/v2.0/tokens","auth",authData,None)

    lbService = {}
    for service  in authResponseData['access']['serviceCatalog']:
        if service['name'] == "cloudLoadBalancers":              
            lbService = service                                  
            break                                                

    publicURL = ""
    for endpoint in lbService['endpoints']:
        if endpoint['region'].upper() == creds['NOVA_REGION_NAME'].upper():
            publicURL = endpoint['publicURL']
            break

    accessData = authResponseData['access']['token']
    userData = authResponseData['access']['user']
    authToken = str(authResponseData['access']['token']['id'])

    action = extras[0]
    # use the extras variable to determine what we should do.
#    LB_API_CALLS =
#    ['list','show','details','create','remove','update','node-list','node-add','node-modify','node-remove']

    actionMethod = "GET"
    postData = None
#    elif action.lower() == "create":
#
#        print namespace_args.createName
#        print namespace_args.createPort
#        print namespace_args.createProto
#        print namespace_args.createNodes
#        print namespace_args.createVirtIp
#        sys.exit(2)
#
#        actionMethod = "POST"
#        servicePath = "/loadbalancers"

    servicePath = "/loadbalancers"
    if action.lower() != "list":

        if len(extras) < 2:
            print "No load balancer id passed"
            sys.exit(2)
        lbID = str(extras[1])
        if re.match("\d+$",lbID) == None:
            print lbID, 'is not a valid load balancer ID.'
            sys.exit(2)

        # reset to have the trailing /
        servicePath = "/loadbalancers/" + lbID

        nodere = re.search('node',action.lower())
        if re.match('show$|detail',action.lower()):
            # do nothing since we already added the loadbalancer id to the url
#           servicePath.join(str(extras[1]))
            pass

        elif re.match('remove|delete',action.lower()):
            actionMethod = "DELETE"
#            servicePath.join(str(extras[1]))

        elif re.match('stat',action.lower()):
            servicePath += '/stats'

        elif re.search('node',action.lower()) is not None:
            servicePath += '/nodes'
            if re.search('list',action.lower()) is not None:
                pass
            else:
                if len(extras) < 3:
                    print "No node id passed"
                    sys.exit(2)
                nodeID = str(extras[2])
                if re.match("\d+$",nodeID) == None:
                    print nodeID, 'is not a valid nodeID.'
                    sys.exit(2)

                if re.search('(show|detail)',action.lower()) is not None:
                    servicePath += '/' + nodeID
                elif re.search('remove',action.lower()) is  not None:
                    print "action is remove"
                    actionMethod = "DELETE"
                    servicePath += '/' + nodeID

        elif re.search('vips|virtualips',action.lower()):
            servicePath += '/virtualips'

            if re.search('remove|delete',action.lower()):
                if len(extras) < 3:
                    print "No virtual IP(VIP) ID passed"
                    sys.exit(2)
                vipID = str(extras[2])
                if re.match("\d+$",vipID) == None:
                    print vipID, ' is not a valid VIP ID'
                    sys.exit(2)
                actionMethod = "DELETE"
                servicePath += '/' + vipID

    
    lbQueryResults = curlCall(publicURL + servicePath,actionMethod,authToken,postData)
    print json.dumps(lbQueryResults,sort_keys=True,indent=4)

if __name__ == "__main__":
    main()
