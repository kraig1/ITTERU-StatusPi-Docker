from __future__ import absolute_import
from __future__ import print_function
import json, time, os, datetime, re
import socketio, eventlet, redis

import gevent 
import subprocess

from threading import Timer

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

from easysnmp import Session

from pyVim.connect import SmartConnect, Disconnect

import atexit, getpass, ssl

eventlet.monkey_patch()

global nodes
global status
global Debug

Debug = False
status = {}
redis_url = os.getenv('REDIS_URL', 'redis://')
sio = SocketIO(message_queue=redis_url)

if Debug: 
    print(redis_url)


status['running'] = True

network_status = {
        'code': 3,
        'message': "Please wait while the ZLT system starts up",
        'nodes': {}
}

vm_status = {
        'code': 3,
        'message': "Please wait while the ZLT system starts up",
        'vms': {}
}

environment_status = {
        'code': 3,
        'message': "Please wait while the ZLT system starts up",
        'sensors': {}
}

# import services from config file
with open('services.json') as data_file:
    nodes = json.load(data_file)

def poweroff():
    os.system("sudo shutdown now -h")
    print("System is now shutting down")

def webserver():
    app = Flask(__name__)
    socketio = SocketIO(app, message_queue=redis_url)

    @app.route('/static/<path:path>')
    def send_js(path):
        return send_from_directory('static', path)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/shutdown/<sec>')
    def shutdown(sec):
        if status['running']:
            shutdowntime = int(sec)
            t = Timer(shutdowntime -5, poweroff)
            socketio.emit('shutdown', shutdowntime, namespace='/zlt')
            t.start()
            status['running'] = False
            return "Shutting down.. in " + str(shutdowntime)
        else:
            return "Shutdown already in progress!"

    @socketio.on('connect', namespace='/zlt')
    def test_connect():
        print("Client is connected to Socket IO")

    @socketio.on('disconnect', namespace='/zlt')
    def test_disconnect():
        print(('Client disconnected', request.sid))

    socketio.run(app, host='0.0.0.0', port=8080, debug=Debug)

def check_ping(host):
    if Debug:
        print(("Pinging host "  + host))

    node_status = int(subprocess.call(['ping', '-c', '1', '-W', '1', host],
    stdout=open('/dev/null', 'w'), stderr=open('/dev/null', 'w')))
    if(node_status == 0):
        return { "code" : 0, "message" : "Online", "class": "success" }
    elif(node_status == 1):
        return { "code" : 1, "message" : "No Response", "class": "warning" }
    elif(node_status == 2):
        return { "code" : 2, "message" : "Error", "class": "primary" }
    else:
        return { "code" : 3, "message" : "Unknown", "class": "default" }


def poll_nodes(nodes, sio):
    while status['running']:
        eventlet.sleep(5)
        if Debug:
            print("Starting ping check")

        code = 0
        message = "All nodes online"
        for key, thenodes in nodes.items():
            for node in thenodes:
                node_status = check_ping(node['ip_address'])
                if(node_status['code'] > code):
                    code = node_status['code']
                    message = node_status['message'] + ' from ' + node['hostname']
                network_status['nodes'][node['hostname']]  = node_status
        network_status['code'] = code
        network_status['message'] = message
        sio.emit('network_status', network_status, namespace='/zlt')

def ups_status(sio):
    while status['running']:
        eventlet.sleep(10)
        global environment_status
    #    sio = SocketIO(message_queue='redis://')
        if Debug:
            print(("Connecting to SNMP on UPS at " + nodes['ups'][0]['ip_address']))
        environment_status['code'] = 0
        environment_status['message'] = 'UPS OK'

        try:
            session = Session(hostname=nodes['ups'][0]['ip_address'], community=nodes['ups'][0]['snmp_community'], version=int(nodes['ups'][0]['snmp_version']))
            environment_status['sensors']['runtime'] = str(datetime.timedelta(seconds=int(session.get('1.3.6.1.4.1.534.1.2.1.0').value)))[:-3]
            environment_status['sensors']['temp'] = session.get('1.3.6.1.4.1.534.1.6.1.0').value + ' &deg;C'
            environment_status['sensors']['humidity'] = session.get('1.3.6.1.4.1.534.1.6.6.0').value + '%'
            environment_status['sensors']['capacity'] = session.get('1.3.6.1.4.1.534.1.2.4.0').value + '%'
            environment_status['sensors']['load'] = session.get('1.3.6.1.4.1.534.1.4.6.0').value + "W"

            # Check if we are running on battery
            if(int(session.get('1.3.6.1.2.1.33.1.2.2.0').value) != 0):
                environment_status['code'] = 1
                environment_status['message'] = "UPS on Battery!"
                environment_status['sensors']['on_battery'] = "BAT"
            else:
                environment_status['sensors']['on_battery']  = "AC"

        except:

            environment_status['code'] = 2
            environment_status['message'] = 'Cannot connect to UPS'

        if Debug:
            print(environment_status)

        sio.emit('environment_status', environment_status, namespace='/zlt')

def check_vms(sio):
    while status['running']:
        eventlet.sleep(10)
        global vm_status
        try:
            si = SmartConnect(host=nodes['vmware-server'][0]['ip_address'],
                         user=nodes['vmware-server'][0]['username'],
                         pwd=nodes['vmware-server'][0]['password'],
                         sslContext=ssl._create_unverified_context())

            content = si.RetrieveContent()
            for child in content.rootFolder.childEntity:
              if hasattr(child, 'vmFolder'):
                 datacenter = child
                 vmFolder = datacenter.vmFolder
                 vmList = vmFolder.childEntity
                 error = 0
                 regexp = re.compile(r'^RC-')
                 for vm in vmList:
                     thisVm = {}
                     thisVm['status'] = str(vm.summary.overallStatus)
                     thisVm['power'] = str(vm.summary.runtime.powerState)
                     if regexp.search(vm.summary.config.name):
                         vm_status['vms'][str(vm.summary.config.name).replace(' ','-')] = thisVm

                     if(vm.summary.overallStatus != 'green'):
                         error = error +1

            if(error):
                vm_status['code'] = 1
                vm_status['message'] = 'There is an error with one or more VMs'
            else:
                vm_status['code'] = 0
                vm_status['message'] = "Connected to ESX server"
        except:
            vm_status['code'] = 2
            vm_status['message'] = 'Cannot connect to ESX server'

        if Debug:
            print(vm_status)

        sio.emit('vm_status', vm_status, namespace='/zlt')


if __name__ == '__main__':
    try:
        eventlet.spawn(poll_nodes, nodes=nodes, sio=sio)
        eventlet.spawn(ups_status, sio)
        eventlet.spawn(check_vms, sio)
        eventlet.spawn(webserver())
    except KeyboardInterrupt:
        status['running'] = False
        print ("Shutdown requested...exiting")
    finally:
        print("bye")
