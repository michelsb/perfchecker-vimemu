#!/usr/bin/python3
import time
import copy
import collector_agent
from lib.osmclient.client import Client

class CollectorManager():
    def __init__(self):
        self.agent = collector_agent.CollectorAgent()       
        self.new_results = {}
        self.old_results = {}
        self.diff_time = 0.0
        self.firstTime = True
        ref_file = open("parameters.txt", "r")
        for line in ref_file:
            field = line.split(':')[0].split()[0]
            if field == "nbi_host_ip":
                self.nbi_host_ip = line.split(':')[1].split()[0]
        self.osmclient = Client(host=self.nbi_host_ip)
        self.hostname = "vim-emu"

    def locate_elem_list (self, list, value):
        for x in list:
            if x['name'] == value:
                return x
        return None

    def diff_int_stats(self,old_stats,new_stats):
        new_stats['rx_dropped'] = round(((new_stats['rx_dropped'] - old_stats['rx_dropped'])/100)/self.diff_time,1)
        new_stats['rx_packets'] = round(((new_stats['rx_packets'] - old_stats['rx_packets'])/100)/self.diff_time,1)
        new_stats['rx_bytes'] = round(((new_stats['rx_bytes'] - old_stats['rx_bytes'])/1000)/self.diff_time,1)
        new_stats['tx_dropped'] = round(((new_stats['tx_dropped'] - old_stats['tx_dropped'])/100)/self.diff_time,1)
        new_stats['tx_packets'] = round(((new_stats['tx_packets'] - old_stats['tx_packets'])/100)/self.diff_time,1)
        new_stats['tx_bytes'] = round(((new_stats['tx_bytes'] - old_stats['tx_bytes'])/1000)/self.diff_time,1)

    def diff_queue_stats(self,old_stats,new_stats):
        new_stats['processed_packets'] = round(((new_stats['processed_packets'] - old_stats['processed_packets'])/100)/self.diff_time,1)
        new_stats['dropped_packets'] = round(((new_stats['dropped_packets'] - old_stats['dropped_packets'])/100)/self.diff_time,1)

    def diff_elem_list_stats(self, list_old_stats, list_new_stats, type):
        for elem_new_stats in list_new_stats:
            elem_old_stats = self.locate_elem_list(list_old_stats, elem_new_stats['name'])
            if (elem_old_stats is not None):
                if type == 1:
                    self.diff_int_stats(elem_old_stats, elem_new_stats)
                elif type == 2:
                    self.diff_queue_stats(elem_old_stats, elem_new_stats)
                else:
                    return None

    def calculate_metrics(self):
        old_server_stats = self.old_results
        new_server_stats = copy.deepcopy(self.new_results)      
        
        if (old_server_stats is not None):
            if (new_server_stats['timestamp'] > old_server_stats['timestamp']):                    
                self.diff_time = round((new_server_stats['timestamp'] - old_server_stats['timestamp']),1)
                new_server_stats['timestamp'] = new_server_stats['timestamp'] * 1000
                self.diff_elem_list_stats(old_server_stats["pifs"], new_server_stats["pifs"], 1)
                #self.diff_elem_list_stats(old_server_stats["tunifs"], new_server_stats["tunifs"], 1)
                self.diff_elem_list_stats(old_server_stats["dc_brs"], new_server_stats["dc_brs"], 1)
                self.diff_elem_list_stats(old_server_stats["vm_vifs"], new_server_stats["vm_vifs"], 1)
                self.diff_elem_list_stats(old_server_stats["other_brs"], new_server_stats["other_brs"], 1)
                self.diff_elem_list_stats(old_server_stats["other_vifs"], new_server_stats["other_vifs"], 1)
                self.diff_elem_list_stats(old_server_stats["cpu_back_queue"], new_server_stats["cpu_back_queue"], 2)
            else:
                return None

        return new_server_stats 

    def get_stats_from_server(self):
        server_entry = {'name':self.hostname,'timestamp': 0.0,'cpu_load':0.0,'mem_load':0.0,
                        'pifs':[],'cpu_back_queue':[]}

        # Get remote data from server
        remote_stats = self.agent.get_stats()
        server_entry['timestamp'] = remote_stats['timestamp']
        server_entry['cpu_load'] = remote_stats['cpu_load']
        server_entry['mem_load'] = remote_stats['mem_load']
        server_entry['pifs'] = remote_stats['pifs']
        server_entry['cpu_back_queue'] = remote_stats['cpu_back_queue']

        server_entry['dc_brs'] = remote_stats['dc_brs']
        server_entry['vm_vifs'] = remote_stats['vm_vifs']
        server_entry['other_brs'] = remote_stats['other_brs']
        server_entry['other_vifs'] = remote_stats['other_vifs']

        nfv_services = self.osmclient.ns.list(filter="operational-status=running")
        #vdu_list = {} 
        for ns in nfv_services:
            #if (ns is not None) and (type(ns) is not str):
            if isinstance(ns,dict):
                flt = "nsr-id-ref="+ns["id"]
                vnfs = self.osmclient.vnf.list(filter=flt)
                for vnf in vnfs:
                    for vdu in vnf["vdur"]:
                        for vm_vif in server_entry['vm_vifs']:
                            prefix_size = len(vm_vif["dc_name"])+1
                            vm_name = vm_vif["vm_name"][prefix_size:]
                            if vm_name == vdu["name"]:
                                vm_vif["ns_name"] = ns["name"]
                                vm_vif["ns_id"] = ns["id"]
                                vm_vif["vnf_id"] = vnf["id"]
            else:
                self.osmclient = Client(host=self.nbi_host_ip)
                break

        print("Stats from server " + self.hostname + " captured...")

        self.new_results = server_entry

        return True

    def get_stats(self):
        self.new_results = {'servers': []}
        self.get_stats_from_server()
    
    def get_metrics_from_server(self):
        response = {}
        self.get_stats()
        response = self.calculate_metrics()
        self.old_results = copy.deepcopy(self.new_results)        
        return response

    def connect(self):                
        self.get_stats()
        self.old_results = copy.deepcopy(self.new_results) 

    def start_manager(self):
        if self.firstTime:
            self.connect()
            time.sleep(2)
            self.get_metrics_from_server()
            self.firstTime = False

#if __name__ == '__main__':
#    manager = CollectorManager()
#    manager.start_manager()
#    time.sleep(2)
#    print(manager.get_metrics_from_server())


#    try:
#        print 'Use Control-C to exit'
#        manager = MiningManager()
#        manager.start_manager()
#        print manager.collect()
#    except KeyboardInterrupt:
#        print 'Exiting'
