'''
Please add your name: Fabrice Ingabire
Please add your matric number: F598DF
'''

import os
import sys
import atexit
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.node import RemoteController

X = .8
Y = .5

net = None

class TreeTopo(Topo):		
    def __init__(self):
		# Initialize topology
            Topo.__init__(self)
            self.linksInfo = []
            self.links_dict = dict()

            # self.build()
            # self.add_links()
    
    def getContents(self, contents):
        hosts = contents[0]
        switch = contents[1]
        links = contents[2]
        linksInfo = contents[3:]
        return hosts, switch, links, linksInfo

    def build(self):
        # Read file contents
        f = open(sys.argv[1],"r")
        contents = f.read().split()
        host, switch, link, linksInfo = self.getContents(contents)
        self.linksInfo = linksInfo
        print("Hosts: " + host)
        print("switch: " + switch)
        print("links: " + link)
        print("linksInfo: " + str(linksInfo))
        # Add switch
        for x in range(1, int(switch) + 1):
            sconfig = {'dpid': "%016x" % x}
            self.addSwitch('s%d' % x, **sconfig)
        
        # Add hosts
        for y in range(1, int(host) + 1):
            ip = '10.0.0.%d/8' % y
            self.addHost('h%d' % y, ip=ip)

        # Add Links
        for x in range(int(link)):
            info = linksInfo[x].split(',')
            host = info[0]
            switch = info[1]
            bandwidth = int(info[2])
            self.addLink(host, switch, bw=bandwidth)
             

    # the function to add links 
    def add_links(self):
         for i in range(0, len(self.linksInfo)):
            node1, node2, bw = self.linksInfo[i].split(",")
            self.addLink(node1, node2, bw=int(bw))
            if node1 not in self.links_dict:
                self.links_dict[node1] = {}
            if node2 not in self.links_dict:
                self.links_dict[node2] = {}

            self.links_dict[node1][node2] = int(bw)
            self.links_dict[node2][node1] = int(bw)

	# You can write other functions as you need.

	# Add hosts
    # > self.addHost('h%d' % [HOST NUMBER])

	# Add switches
    # > sconfig = {'dpid': "%016x" % [SWITCH NUMBER]}
    # > self.addSwitch('s%d' % [SWITCH NUMBER], **sconfig)

	# Add links
	# > self.addLink([HOST1], [HOST2])

# function to create QoS Queues 
def create_queues(bw, switch, port):

    eth = '%s-eth%s' % (switch, port)

    os.system('sudo ovs-vsctl -- set Port %s qos=@newqos \
               -- --id=@newqos create QoS type=linux-htb other-config:max-rate=%i queues=0=@q0,1=@q1,2=@q2 \
               -- --id=@q0 create queue other-config:max-rate=%i other-config:min-rate=%i \
               -- --id=@q1 create queue other-config:min-rate=%i \
               -- --id=@q2 create queue other-config:max-rate=%i'(eth, bw, bw, bw, X * bw, Y * bw))
    
def assignQueues(topo):
    for link in topo.links(sort=True, withKeys=False, withInfo=True):
        # get link stats
        host, switch, info = link
        port_1 = info['port1']
        port_2 = info['port2']

        node_1 = info['node1']
        node_2 = info['node2']
        # get the bandwidth between two nodes 
        bw = topo.links_dict[node_1][node_2]
        # bw = topo.linksInfo[node_1][node_2]
        bw = bw * 10^6
        print('%s@Port%i is connected with bandwith of %i to %s@Port%i' %(node_1, port_1, bw, node_2, port_2))
        create_queues(bw, node_1, port_1)
        create_queues(bw, node_2, port_2)
    

def startNetwork():
    info('** Creating the tree network\n')
    topo = TreeTopo()
    controllerIP = sys.argv[2]

    global net
    net = Mininet(topo=topo, 
                  link = TCLink,
                  controller=lambda name: RemoteController(name, ip=controllerIP),
                  listenPort=6633, 
                  autoSetMacs=True)

    info('** Starting the network\n')
    net.start()

    # create qos queues for each link
    assignQueues(topo)

    info('** Running CLI\n')
    CLI(net)

def stopNetwork():
    if net is not None:
        net.stop()
        # Remove QoS and Queues
        os.system('sudo ovs-vsctl --all destroy Qos')
        os.system('sudo ovs-vsctl --all destroy Queue')


if __name__ == '__main__':
    # Force cleanup on exit by registering a cleanup function
    atexit.register(stopNetwork)


    # Tell mininet to print useful information
    setLogLevel('info')
    startNetwork()