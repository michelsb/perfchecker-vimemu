#!/usr/bin/python3
import os
import time
import re


class CollectorAgent():
    def __init__(self):
        self.hostname = os.popen("hostname").read()  # Get the hostname
        self.phy_interfaces = ['eth0', 'eth1']
        #self.tun_interfaces = ['fs1-eth1','root-eth0']
        self.results = dict()
       

    def get_hardware_resources(self):
        cpu_data = os.popen("top -b -n1 -p 1 | grep 'Cpu' | tail -1").read().split(" ")
        cpu_idle = float(cpu_data[cpu_data.index("id,")-1])
        cpu_load = 100 - cpu_idle
        mem_load = (float(os.popen('free -m | fgrep "Mem"').read().split()[2]) / float(os.popen('free -m | fgrep "Mem"').read().split()[1])) * 100
        self.results['cpu_load'] = round(cpu_load,1)
        self.results['mem_load'] = round(mem_load,1)

    def get_pifs_stats(self):
        self.results['pifs'] = []
        for interface in self.phy_interfaces:
            pif_entry = {'name':interface}
            rx_dropped = os.popen("cat /sys/class/net/" + interface + "/statistics/rx_dropped").read()
            rx_packets = os.popen("cat /sys/class/net/" + interface + "/statistics/rx_packets").read()
            rx_bytes = os.popen("cat /sys/class/net/" + interface + "/statistics/rx_bytes").read()
            tx_dropped = os.popen("cat /sys/class/net/" + interface + "/statistics/tx_dropped").read()
            tx_packets = os.popen("cat /sys/class/net/" + interface + "/statistics/tx_packets").read()
            tx_bytes = os.popen("cat /sys/class/net/" + interface + "/statistics/tx_bytes").read()
            pif_entry['rx_dropped'] = float(rx_dropped)
            pif_entry['rx_packets'] = float(rx_packets)
            pif_entry['rx_bytes'] = float(rx_bytes)
            pif_entry['tx_dropped'] = float(tx_dropped)
            pif_entry['tx_packets'] = float(tx_packets)
            pif_entry['tx_bytes'] = float(tx_bytes)
            self.results['pifs'].append(pif_entry)

    def cpu_back_queue_stats(self):
        self.results['cpu_back_queue'] = []
        processed_packets_per_core = os.popen("cat /proc/net/softnet_stat | awk '{print $1}'").read().split("\n")[:-1]
        dropped_packets_per_core = os.popen("cat /proc/net/softnet_stat | awk '{print $2}'").read().split("\n")[:-1]
        numCores = len(processed_packets_per_core)
        for x in range(0, numCores):
            queue_entry = {'name':x}
            queue_entry['processed_packets'] = int(processed_packets_per_core[x], 16)
            queue_entry['dropped_packets'] = int(dropped_packets_per_core[x], 16)
            self.results['cpu_back_queue'].append(queue_entry)

    def get_ovs_if_stats(self, interface):
        data = os.popen("ovs-vsctl get Interface " + interface + " statistics").read()
        mapped = {}
        pair_re = re.compile('(\w+)=(\d+)')
        mapped.update(pair_re.findall(data))
        rx_dropped = mapped['rx_dropped']
        rx_packets = mapped['rx_packets']
        rx_bytes = mapped['rx_bytes']
        tx_dropped = mapped['tx_dropped']
        tx_packets = mapped['tx_packets']
        tx_bytes = mapped['tx_bytes']
        if_entry = {}
        if_entry['rx_dropped'] = float(rx_dropped)
        if_entry['rx_packets'] = float(rx_packets)
        if_entry['rx_bytes'] = float(rx_bytes)
        if_entry['tx_dropped'] = float(tx_dropped)
        if_entry['tx_packets'] = float(tx_packets)
        if_entry['tx_bytes'] = float(tx_bytes)
        return if_entry

    def get_vifs_stats_vimemu(self):

        # [line.replace(" ","")[1:-1].split("|") for line in commands.getoutput("vim-emu datacenter list").split('\n') if "-+-" not in line and "=+=" not in line]
        # [line.replace(" ","")[1:-1].split("|") for line in commands.getoutput("vim-emu compute list").split('\n') if "-+-" not in line and "=+=" not in line]

        datacenter_list = [line.replace(" ","")[1:-1].split("|") for line in os.popen("vim-emu datacenter list").read().split('\n') if "-+-" not in line and "=+=" not in line][1:-1]
        compute_list = [line.replace(" ","")[1:-1].split("|") for line in os.popen("vim-emu compute list").read().split('\n') if "-+-" not in line and "=+=" not in line][1:-1]

        br_list = os.popen("ovs-vsctl list-br").read().split("\n")[:-1]

        #self.results['vifs'] = []
        self.results['dc_brs'] = []
        self.results['vnf_vifs'] = []
        self.results['other_brs'] = []
        self.results['other_vifs'] = []

        for br in br_list:
            br_entry = {"br_name":br}
            br_stats = self.get_ovs_if_stats(br)
            for elem in br_stats:
                br_entry[elem] = br_stats[elem]
            is_dc = False
            for dc in datacenter_list:
                if br_entry["br_name"] == dc[2]:
                    br_entry["dc_name"] = dc[0]
                    self.results['dc_brs'].append(br_entry)
                    is_dc = True
            if not is_dc:
                self.results['other_brs'].append(br_entry)


            port_list = os.popen("ovs-vsctl list-ports " + br).read().split("\n")[:-1]
            for port in port_list:
                port_entry = {"port_name":port}
                port_stats = self.get_ovs_if_stats(port)
                for elem in port_stats:
                    port_entry[elem] = port_stats[elem]
                is_vm = False
                for vm in compute_list:
                    vm_ifs_list = vm[3].split(",")
                    dc_ifs_list = vm[4].split(",")
                    for index in range(0,len(dc_ifs_list)):
                        if dc_ifs_list[index] == port:
                            port_entry["vm_name"] = vm[1]
                            port_entry["vm_port_name"] = vm_ifs_list[index]  
                            self.results['vnf_vifs'].append(port_entry)
                            is_vm = True
                if not is_vm:
                    self.results['other_vifs'].append(port_entry)

        # for br in br_list:
        #     br_entry = {"br_name":br,"br_stats":{},"ports":[]}
        #     br_entry["br_stats"] = self.get_ovs_if_stats(br)
        #     for dc in datacenter_list:
        #         if br_entry["br_name"] == dc[2]:
        #             br_entry["dc_name"] = dc[0]
        #     port_list = commands.getoutput("ovs-vsctl list-ports " + br).split("\n")
        #     for port in port_list:
        #         port_entry = {"port_name":port,"port_stats":{}}
        #         port_entry["port_stats"] = self.get_ovs_if_stats(port)
        #         for vm in compute_list:
        #             vm_ifs_list = vm[3].split(",")
        #             dc_ifs_list = vm[4].split(",")
        #             for index in range(0,len(dc_ifs_list)):
        #                 if dc_ifs_list[index] == port:
        #                     port_entry["vm_name"] = vm[1]
        #                     port_entry["vm_port_name"] = vm_ifs_list[index]  
        #         br_entry["ports"].append(port_entry)
        #     self.results['vifs'].append(br_entry)

    def get_stats(self):
        self.results = {'timestamp': time.time()}
        self.get_hardware_resources()
        self.get_pifs_stats()
        self.cpu_back_queue_stats()
        self.get_vifs_stats_vimemu()
        return self.results

    #def start_agent_service(self):
    #    self.create_server()
    #    self.server.register_function(self.get_stats, 'get_stats')
    #    self.server.serve_forever()

if __name__ == '__main__':
	agent = CollectorAgent()
	print(agent.get_stats())

    # Run the server's main loop
    #try:
    #    print 'Use Control-C to exit'
    #    agent = MiningAgent()
        #print agent.get_stats()
   #     agent.start_agent_service()
   # except KeyboardInterrupt:
   #     print 'Exiting'

