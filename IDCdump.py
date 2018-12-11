#!/usr/bin/python
import requests
import json
import pexpect
import sys
import operator
import time    
import re
import yaml


#./IDCdump.py 149879607854972716_production_live_crs-app

def dumpTWAS(connect,appName):
    
    cmd="ssh \""+username+"\"@"+connect["hostname"]
    c = pexpect.spawn(cmd)
    c.logfile = sys.stdout
    index=c.expect(['password: ','\(yes/no\)\? '])
    if index == 0:
        c.sendline(password)
    elif index == 1:
        c.sendline('yes')
        c.expect('password: ')
        c.sendline(password)
    c.expect('\$ ')
    c.sendline("sudo rm -f -r /tmp/ts_*")
    c.expect('ibm.com: ')
    c.sendline(password)
    c.expect('\$ ')
    c.sendline("sudo docker exec "+connect["containerId"]+" sh -c \"rm -f -r javacore*\"")
    c.expect('\$ ',timeout=None)
    c.sendline("sudo docker exec "+connect["containerId"]+" cat /tmp/PASSWORD")
    c.expect('\r\n(.*?)\r\n.*?\$ ')
    twas_pwd=c.match.group(1)
    c.sendline("sudo docker exec "+connect["containerId"]+" sh -c \"/opt/WebSphere/AppServer/profiles/default/bin/wsadmin.sh -user configadmin -password "+twas_pwd+" -c \\\"servobj=AdminControl.queryNames('WebSphere:type=JVM,process=server1,*')\\\" -c \\\"AdminControl.invoke(servobj, 'dumpThreads')\\\"\"")
    c.expect('\$ ',timeout=None)
    c.sendline("sudo docker exec "+connect["containerId"]+" find ./ -name \"javacore*\"")
    #child.sendline("docker exec "+container['containerId']+" rm -f -r \"javacore*\"")
    c.expect('\r\n\./(.*?)\r\n.*?\$ ',timeout=None)
    javacore=c.match.group(1)
    c.sendline("sudo docker cp "+connect["containerId"]+":/"+javacore+" /tmp/"+appName+"_"+connect["containerId"]+"_"+javacore)
    c.expect('\$ ',timeout=None)
    c.sendline('logout')
    time.sleep(3)
    c.close()
    # print "The PASSWORD is ",twas_pwd
    # print "The javacore is ",javacore
    return [appName+"_"+connect["containerId"]+"_"+javacore]



def dumpLibertyCommand(connect,appName):

    cmd="ssh \""+username+"\"@"+connect["hostname"]
    c = pexpect.spawn(cmd)
    c.logfile = sys.stdout
    index=c.expect(['password: ','\(yes/no\)\? '])
    if index == 0:
        c.sendline(password)
    elif index == 1:
        c.sendline('yes')
        c.expect('password: ')
        c.sendline(password)
    c.expect('\$ ')
    c.sendline("sudo rm -f -r /tmp/crs_javacore* /tmp/"+appName+"*")
    c.expect('ibm.com: ')
    c.sendline(password)
    c.expect('\$ ')
    c.sendline("sudo docker exec "+connect["containerId"]+" sh -c \"rm -f -r /opt/WebSphere/Liberty/usr/servers/default/javacore* /opt/WebSphere/Liberty/usr/servers/default/heapdump*\"")
    c.expect('\$ ',timeout=None)
    c.sendline("sudo docker exec "+connect["containerId"]+" /opt/WebSphere/Liberty/bin/server javadump default --include=heap")
    c.expect('Server default dump complete in (/opt/WebSphere/Liberty/usr/servers/default/javacore.*?)\.\r\nServer default dump complete in (/opt/WebSphere/Liberty/usr/servers/default/heapdump.*?)\.\r\n-sh-4.2\$ ',timeout=None)
    # c.sendline("sudo docker exec "+connect["containerId"]+" /opt/WebSphere/Liberty/bin/server javadump default")
    #c.expect('Server default dump complete in (/opt/WebSphere/Liberty/usr/servers/default/javacore.*?)\.\r\nServer default dump complete in (/opt/WebSphere/Liberty/usr/servers/default/heapdump.*?)\.\r\n-sh-4.2\$ ',timeout=None)
    # c.expect('Server default dump complete in (/opt/WebSphere/Liberty/usr/servers/default/javacore.*?)\.\r\n-sh-4.2\$ ',timeout=None)
    javacore=c.match.group(1)
    dumpfile=c.match.group(2)
    c.sendline('sudo docker cp '+connect["containerId"]+':'+javacore+' /tmp/'+appName+'_'+connect["containerId"]+'_'+javacore.split('/')[-1])
    c.expect('\$ ')
    c.sendline('sudo docker cp '+connect["containerId"]+':'+dumpfile+' /tmp/'+appName+'_'+connect["containerId"]+'_'+dumpfile.split('/')[-1])
    c.expect('\$ ')
    c.sendline('sudo chmod 777 /tmp/*')
    c.expect('\$ ')
    c.sendline('logout')
    time.sleep(3)
    c.close()
    # return [appName+'_'+connect["containerId"]+'_'+javacore.split('/')[-1]]
    return [appName+'_'+connect["containerId"]+'_'+javacore.split('/')[-1],appName+'_'+connect["containerId"]+'_'+dumpfile.split('/')[-1]]

def fetchDump(files,hostname):
    cmd="sftp "+username+"@"+hostname
    child = pexpect.spawn(cmd)
    child.logfile = sys.stdout
    index=child.expect(['password: ','\(yes/no\)\? '])
    if index == 0:
        child.sendline(password)
    elif index == 1:
        child.sendline('yes')
        child.expect('password: ')
        child.sendline(password)
    child.expect('sftp> ')
    for f in files:
        child.sendline ('get /tmp/'+f)
        child.expect('sftp> ',timeout=None)
    child.sendline ('exit')
    time.sleep(3)
    child.close()

def getHostAndContainerId():
    result=[]

    headers={'Accept':'application/json','X-Query-Key': api_key}
    query="SELECT count(*) from ProcessSample where containerLabel_MESOS_TASK_ID  like  '"+tenantApp+"%' facet hostname, containerId  since 1 minute ago"
    data = {"nrql": query }
    response = requests.get(api_url,params=data,headers=headers)
    if(response.ok):
        jData = json.loads(response.content)
        for elem in jData["facets"]:
            result.append({"hostname":elem["name"][0],"containerId":elem["name"][1][:12]})
    return result


username=None
password=None
api_url=None
api_key=None

with open('IDCdump.yml', 'r') as f:
    config = yaml.load(f)
    username=config["LDAP"]["username"]
    password=config["LDAP"]["password"]
    api_url=config["New_Relic"]["api_url"]
    api_key=config["New_Relic"]["api_key"]

tenantApp=sys.argv[1]
target=getHostAndContainerId()

for t in target:
    print t["hostname"],t["containerId"]
    if "crs-app" in tenantApp:
        files=dumpLibertyCommand(t,"crs")
        fetchDump(files,t["hostname"])
    elif "search-app-slave" in tenantApp:
        files=dumpLibertyCommand(t,"srch")
        fetchDump(files,t["hostname"])
    elif "ts-app" in tenantApp:
        files=dumpTWAS(t,"ts")
        # print files
        fetchDump(files,t["hostname"])

