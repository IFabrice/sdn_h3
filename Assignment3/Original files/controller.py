'''
Please add your name: Fabrice Ingabire
Please add your matric number: F598DF
'''

import sys
import os
#Sfrom sets import Set

from pox.core import core

import pox.openflow.libopenflow_01 as of
import pox.openflow.discovery
import pox.openflow.spanning_forest
import unittest

from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.addresses import IPAddr, EthAddr

log = core.getLogger()

class Controller(EventMixin):
    def __init__(self):
        self.listenTo(core.openflow)
        core.openflow_discovery.addListeners(self)
        self.FW_PRIORITY = 40
        self.mac_to_port = {}
        self.DEFAULT_PRIORITY = 10
        self.TCP_PROTOCOL = 6
        self.premium_bw = 800000
        self.default_bw = 500000
        self.priority_queue_id = 1
        self.default_queue_id = 0

        # get policies from the file
        
        self.fw_policies, self.premium_ip = self.get_policies()

        
    # You can write other functions as you need.
    
    # code to get all the policies
    def get_policies():
        f = open(sys.argv[1],"r")
        policies = f.read().split()
        fw_rules_num = policies[0]
        prem_rules_num = policies[1]

        fw_rules = policies[2:2+fw_rules_num]
        prem_rules = policies[3 + fw_rules_num:]

        unittest.assertEquals(len(prem_rules), prem_rules_num)

        return fw_rules, prem_rules


    def _handle_PacketIn (self, event):    
    	
        # install entries to the route table
        def install_enqueue(event, packet, outport, q_id):

            msg = of.ofp_flow_mod()
            msg.data = event.ofp
            msg.priority = self.DEFAULT_PRIORITY
            
            msg.match = of.ofp_match()
            msg.match.dl_dst = event.parsed.dst
            msg.match.dl_type = 0x800
            ######

            msg.match = of.ofp_match()
            # link layer
            msg.match.dl_dst = packet.dst
            msg.match.dl_type = 0x800
            # network layer 
            msg.match.nw_dst = packet.payload.dstip
     
            msg.actions.append(of.ofp_action_enqueue(port=outport, queue_id=q_id))
            event.connection.send(msg)


    	# Check the packet and decide how to route the packet
        def forward(message = None):

            # get packet data
            packet = event.parsed
            dpid = event.dpid
            src = packet.src
            dst = packet.dst

            # update mac to port dictionary to map the src mac to src port
            self.mac_to_port[dpid][src] = event.port

            # Flood if we don't have mac to port in the dictionary
            if dst not in self.mac_to_port[dpid]:
                flood()
                return
            

            outport = self.mac_to_port[dpid][dst]

            dstip = packet.payload.dstip

            # set the queue id (q_id) accordingly if the dstip is in premium list
            q_id = self.default_queue_id
            if dstip in self.premium_ip:
                q_id = self.premium_ip
            
            install_enqueue(event, packet, outport, q_id)


        # When it knows nothing about the destination, flood but don't install the rule
        def flood (message = None):
            # define your message here
            fl_msg = of.ofp_packet_out()   
            fl_msg.data = event.ofp
            fl_msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
            event.connection.send(fl_msg)

            # ofp_action_output: forwarding packets out of a physical or virtual port
            # OFPP_FLOOD: output all openflow ports expect the input port and those with 
            #    flooding disabled via the OFPPC_NO_FLOOD port config bit
            # msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
        
        forward()

    def _handle_ConnectionUp(self, event):
        dpid = dpid_to_str(event.dpid)
        log.debug("Switch %s has come up.", dpid)
        
        # Send the firewall policies to the switch
        def sendFirewallPolicy(connection, policy):
            fw_msg = of.ofp_flow_mod()
            split_policy = policy.split(",")

            fw_msg.priority = self.FW_PRIORITY
            fw_msg.match.nw_proto = self.TCP_PROTOCOL

            if len(split_policy) == 2:
                fw_msg.match.nw_dst = split_policy[0]
                fw_msg.match.tp_dst = split_policy[1]

            elif len(split_policy) == 3:
                fw_msg.match.nw_src = split_policy[0]
                fw_msg.match.nw_dst = split_policy[1]
                fw_msg.match.tp_dst = split_policy[2]
        

            # OFPP_NONE: outputting to nowhere
            fw_msg.actions.append(of.ofp_action_output(port = of.OFPP_NONE))

            connection.send(fw_msg)

        for i in self.fw_policies:
            sendFirewallPolicy(event.connection, i)

        # configure queues in the switch

        # def queue_configuration():

        #     # configure default queue
        #     config_default_msg = of.ofp_queue_prop_min_rate_experimenter()
        #     config_default_msg.properties.append(of.ofp_queue_prop_max_rate_experimenter())
        #     config_default_msg.properties[0].rate = self.default_bw

        #     msg = of.ofp_queue_mod()
        #     msg.queue_id = self.default_queue_id
        #     msg.properties.append(config_default_msg)

        #     event.connection.send(msg)

        #     # configure priority queue
        #     config_priority_msg = of.ofp_queue_prop_min_rate_experimenter()
        #     config_priority_msg.properties.append(of.ofp_queue_prop_max_rate_experimenter())
        #     config_priority_msg.properties[0].rate = self.premium_bw
        

        #     prem_msg = of.ofp_queue_mod()
        #     prem_msg.queue_id = self.priority_queue_id
        #     prem_msg.properties.append(config_priority_msg)

        #     event.connection.send(prem_msg)
        
        # queue_configuration()


 

def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_forest.launch()

    # Starting the controller module
    core.registerNew(Controller)
