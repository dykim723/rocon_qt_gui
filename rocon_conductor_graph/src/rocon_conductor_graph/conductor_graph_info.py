#!/usr/bin/env python
#


import rospy
import rosgraph
from rosgraph.impl.graph import Edge, EdgeList
import concert_msgs.msg as concert_msgs
from concert_msgs.msg import ConcertClients
from rocon_std_msgs.srv import GetPlatformInfo
from rocon_app_manager_msgs.srv import Status, Invite, StartApp, StopApp
from gateway_msgs.msg import ConnectionStatistics

import random
import copy
##############################################################################
# Graph
##############################################################################
class ConductorGraphInfo(object):
    def __init__(self):
        '''
        Creates the polling topics necessary for updating statistics
        about the running gateway-hub network.
        '''
        self._last_update = 0
        self._gateway_namespace = None
        self._concert_conductor_name = "concert_conductor"
        self.gateway_nodes = []  # Gateway nodes
        self.gateway_edges = []  # Gateway-Gateway edges
        self.bad_nodes = []  # Gateway nodes
        
        #Rubbish to clear out once rocon_gateway_graph is integrated
        self._event_callback=None
        self._period_callback=None
        self.is_first_update = False        

        rospy.Subscriber(concert_msgs.Strings.CONCERT_CLIENTS, ConcertClients, self.update_client_list)
        rospy.Subscriber(concert_msgs.Strings.CONCERT_CLIENT_CHANGES, ConcertClients, self._update_callback)
        
        self._client_info_list = {}
        self._pre_client_info_list = {}

    def _update_callback(self, data):
        if self._event_callback != None:
            self._event_callback()
        pass
            
    def update_client_list(self, data):
        print "[conductor_graph_info]: update_client_list"
        
        if self.is_first_update == False:
            if self._event_callback != None:
                self._event_callback()
            if self._period_callback != None:
                self._period_callback()
                
            self.is_first_update = True
                     
        #update dotgraph info
        self.gateway_nodes = []
        self.gateway_nodes.append(self._concert_conductor_name)
        self.gateway_edges = EdgeList()

        for k in data.clients:
            client_name = k.name            
            
            if self._client_info_list.has_key(client_name):
                self._client_info_list[client_name]["is_new"] = False
            else:
                self._client_info_list[client_name]={}
                self._client_info_list[client_name]["is_new"] = True
            self._client_info_list[client_name]["is_check"]=True
            
            self._client_info_list[client_name]["name"]=k.name
            self._client_info_list[client_name]["gateway_name"]=k.gateway_name
            self._client_info_list[client_name]["os"]=k.os
            self._client_info_list[client_name]["version"]=k.version
            self._client_info_list[client_name]["system"]=k.system
            self._client_info_list[client_name]["platform"]=k.platform
            self._client_info_list[client_name]["client_status"]=k.client_status
            self._client_info_list[client_name]["app_status"]=k.app_status
            
            self._client_info_list[client_name]["is_local_client"]=k.is_local_client
            self._client_info_list[client_name]["status"]=k.status
            
            self._client_info_list[client_name]["conn_stats"]=k.conn_stats
            self._client_info_list[client_name]["gateway_available"]=k.conn_stats.gateway_available
            self._client_info_list[client_name]["time_since_last_seen"]=k.conn_stats.time_since_last_seen
            self._client_info_list[client_name]["ping_latency_min"]=k.conn_stats.ping_latency_min
            self._client_info_list[client_name]["ping_latency_max"]=k.conn_stats.ping_latency_max
            self._client_info_list[client_name]["ping_latency_avg"]=k.conn_stats.ping_latency_avg
            self._client_info_list[client_name]["ping_latency_mdev"]=k.conn_stats.ping_latency_mdev
            
            self._client_info_list[client_name]["network_info_available"]=k.conn_stats.network_info_available
            self._client_info_list[client_name]["network_type"]=k.conn_stats.network_type
            self._client_info_list[client_name]["wireless_bitrate"]=k.conn_stats.wireless_bitrate
            self._client_info_list[client_name]["wireless_link_quality"]=k.conn_stats.wireless_link_quality
            self._client_info_list[client_name]["wireless_signal_level"]=k.conn_stats.wireless_signal_level
            self._client_info_list[client_name]["wireless_noise_level"]=k.conn_stats.wireless_noise_level
            
            self._client_info_list[client_name]["apps"]={}
            
            for l in k.apps: 
                app_name = l.name
                self._client_info_list[client_name]["apps"][app_name] = {}
                self._client_info_list[client_name]["apps"][app_name]['name'] = l.name
                self._client_info_list[client_name]["apps"][app_name]['display_name'] = l.display_name
                self._client_info_list[client_name]["apps"][app_name]['description'] = l.description
                self._client_info_list[client_name]["apps"][app_name]['platform'] = l.platform
                self._client_info_list[client_name]["apps"][app_name]['status'] = l.status

            #text info
            app_context = "<html>"
            app_context += "<p>-------------------------------------------</p>"
            app_context += "<p><b>name: </b>" +k.name+"</p>"
            app_context += "<p><b>gateway_name: </b>" +k.gateway_name+"</p>"
            app_context += "<p>-------------------------------------------</p>"
            app_context += "<p><b>os: </b>" +k.os+"</p>"
            app_context += "<p><b>version: </b>" +k.version+"</p>"
            app_context += "<p><b>system: </b>" +k.system+"</p>"
            app_context += "<p><b>platform: </b>" +k.platform+"</p>"
            app_context += "<p>-------------------------------------------</p>"
            app_context += "<p><b>client_status: </b>" +k.client_status+"</p>"
            app_context += "<p><b>app_status: </b>" +k.app_status+"</p>"
            for l in self._client_info_list[client_name]["apps"].values():
                app_context += "<p>-------------------------------------------</p>"
                app_context += "<p><b>app_name: </b>" +l['name']+"</p>"
                app_context += "<p><b>app_display_name: </b>" +l['display_name']+"</p>"
                app_context += "<p><b>app_description: </b>" +l['description']+"</p>"
                app_context += "<p><b>app_platform: </b>" +l['platform']+"</p>"
                app_context += "<p><b>app_status: </b>" +l['status']+"</p>"
            app_context +="</html>"
            self._client_info_list[client_name]["app_context"]=app_context
            #How to set the strength range???
            connection_strength = "very_strong"
            self._client_info_list[client_name]["connection_strength"]=connection_strength

            #graph info
            self.gateway_nodes.append(k.name)
            if k.conn_stats.network_type == ConnectionStatistics.WIRED:
                self.gateway_edges.add(Edge(self._concert_conductor_name,k.name,"wired"))
            elif k.conn_stats.network_type == ConnectionStatistics.WIRELESS: 
                self.gateway_edges.add(Edge(self._concert_conductor_name,k.name,"wireless"))

        #new node check
        for k in self._client_info_list.keys():
            if self._client_info_list[k]["is_check"] == True:
                self._client_info_list[k]["is_check"] = False
            else:
                del self._client_info_list[k]
        #update check
        if self._compare_client_info_list():
            pass
        else:
            self._event_callback()    
        self._pre_client_info_list = copy.deepcopy(self._client_info_list)
        #call period callback function
        if self._period_callback != None:
            self._period_callback()
                    
    def _reg_event_callback(self,func):
        self._event_callback = func
        pass
        
    def _reg_period_callback(self,func):
        self._period_callback = func
        pass

    def _compare_client_info_list(self):
        result=True
        pre=self._pre_client_info_list
        cur=self._client_info_list
        for k in cur.values():
            client_name = k["name"]
            if not pre.has_key(client_name):
                 continue
            if pre[client_name]["client_status"] != cur[client_name]["client_status"]:
                result=False
            elif pre[client_name]["app_status"] != cur[client_name]["app_status"]:
                result=False
        return result
        pass
        
    def set_random_connection_strength(self):
        connection_strength = random.randrange(1,6)
        if connection_strength == 1:
            return 'very_strong'
        elif connection_strength == 2:
            return 'strong'
        elif connection_strength == 3:
            return 'normal'
        elif connection_strength == 4:
            return 'weak'
        elif connection_strength == 5:
            return 'very_weak'
