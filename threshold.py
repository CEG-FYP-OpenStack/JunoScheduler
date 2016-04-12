# import time, threading
from __future__ import division
from nova.openstack.common import log as logging
import MySQLdb
import subprocess

LOG = logging.getLogger(__name__)


class ThresholdManager():
	"""docstring for ThresholdManager"""

	on_demand_high = 0
	on_demand_low = 0
	spot = 0	

	def __init__(self):
		self.update_attributes()

	def get_vcpus_data(self):
		db = MySQLdb.connect("localhost","root","password","nova")
		cursor = db.cursor()
		cursor.execute("select vcpus,vcpus_used from compute_nodes")
		data = cursor.fetchall()
		vcpus = 0
		vcpus_used = 0
		for row in data:
			vcpus += row[0]
			vcpus_used += row[1]	
		LOG.debug('Virtual CPUs %(vcpus)s',{'vcpus': vcpus})
		LOG.debug('Virtual CPUs Used %(vcpus_used)s', {'vcpus_used': vcpus_used})
		db.close()
		return [vcpus, vcpus_used]

	def get_ram_data(self):
		db = MySQLdb.connect("localhost", "root", "password", "nova")
		cursor = db.cursor()
		cursor.execute("select memory_mb,memory_mb_used from compute_nodes")
		data = cursor.fetchall()
		total_ram = 0
		total_ram_used = 0

		for row in data:
			total_ram += row[0]
			total_ram_used = row[1]
		LOG.debug('Ram %(ram)s', {'ram': total_ram})
		LOG.debug('Ram used %(ram_used)s', {'ram_used': total_ram_used})
		db.close()
		return [total_ram, total_ram_used]

	def get_server_data(self):
		db = MySQLdb.connect("localhost","root","password","nova")
		cursor = db.cursor()
		cursor.execute("select id from instance_types where name='tiny.spot'")
		data = cursor.fetchall()
		spot_instance_id = 0

		for row in data:
			spot_instance_id = row[0]

		spot_instances_data = []
		cursor.execute("select display_name,id,uuid,vm_state,instance_type_id from instances where instance_type_id='8' and vm_state='active'")
		data = cursor.fetchall()

		for row in data:
			instance_data = {}
			instance_data['name'] = row[0]
			instance_data['id'] = row[1]
			instance_data['uuid'] = row[2]
			instance_data['vm_state'] = row[3]
			spot_instances_data.append(instance_data)

		return spot_instances_data

	def get_ondemand_low_data(self):
		on_demand_low_data = []
		db = MySQLdb.connect("localhost","root","password","nova")
		cursor = db.cursor()
		cursor.execute("select display_name,id,uuid,vm_state,instance_type_id from instances where instance_type_id='7' and vm_state='active'")
		data = cursor.fetchall()

		for row in data:
			instance_data = {}
			instance_data['name'] = row[0]
			instance_data['id'] = row[1]
			instance_data['uuid'] = row[2]
			instance_data['vm_state'] = row[3]
			on_demand_low_data.append(instance_data)

		return on_demand_low_data

	def get_paused_on_demand_servers(self):
		on_demand_low_data = []
		db = MySQLdb.connect("localhost","root","password","nova")
		cursor = db.cursor()
		cursor.execute("select display_name,id,uuid,vm_state,instance_type_id from instances where instance_type_id='7' and vm_state='paused'")
		data = cursor.fetchall()

		for row in data:
			instance_data = {}
			instance_data['name'] = row[0]
			instance_data['id'] = row[1]
			instance_data['uuid'] = row[2]
			instance_data['vm_state'] = row[3]
			on_demand_low_data.append(instance_data)

		return on_demand_low_data

	def update_attributes(self):
		vcpus_data = self.get_vcpus_data()
		ram_data = self.get_ram_data()
		LOG.debug('VCPUS %(vcpus)s', {'vcpus': vcpus_data})
		vcpu_usage = vcpus_data[1]/vcpus_data[0]*100
		ram_usage = ram_data[1]/ram_data[0]*100

		total_usage = (vcpu_usage+ram_usage)/2
		LOG.debug('Total Usage %(total_usage)s', {'total_usage': total_usage})

		if total_usage < 25:
			ThresholdManager.on_demand_high = 1
			ThresholdManager.on_demand_low = 1
			ThresholdManager.spot = 1
			on_demand_low_paused_servers = self.get_paused_on_demand_servers()
			LOG.debug('Server data Paused %(on_pause)s', {'on_pause': on_demand_low_paused_servers})
			for i in on_demand_low_paused_servers:
				if i['vm_state'] == 'paused':
					server_name = i['uuid']
					subprocess.Popen("/opt/stack/nova/nova/scheduler/./nova_unpause_server.sh %s" % (str(server_name)), shell=True)
					LOG.debug("Unpausing %(unpaused_server)s", {'unpaused_server':i['name']})
		elif total_usage >=25 and total_usage < 44:
			ThresholdManager.on_demand_high = 1
			ThresholdManager.on_demand_low = 1
			ThresholdManager.spot = 0
			on_demand_low_paused_servers = self.get_paused_on_demand_servers()
			LOG.debug('Server data Paused %(on_pause)s', {'on_pause': on_demand_low_paused_servers})
			for i in on_demand_low_paused_servers:
				if i['vm_state'] == 'paused':
					server_name = i['uuid']
					subprocess.Popen("/opt/stack/nova/nova/scheduler/./nova_unpause_server.sh %s" % (str(server_name)), shell=True)
					LOG.debug("Unpausing %(unpaused_server)s", {'unpaused_server':i['name']})

		elif total_usage >=45:
			ThresholdManager.on_demand_high = 1
			ThresholdManager.on_demand_low = 0
			ThresholdManager.spot = 0
			servers_data = self.get_server_data()
			LOG.debug('Servers Data %(servers_data)s', {'servers_data': servers_data})
			for i in servers_data:
			 	if i['vm_state'] == 'active':
			 		server_name = i['uuid']
			 		subprocess.Popen("/opt/stack/nova/nova/scheduler/./nova_delete_server.sh %s" % (str(server_name)), shell=True)
			 		LOG.debug('Deleted Server %(name)s',{'name': i['name']})

			on_demand_low_servers = self.get_ondemand_low_data()
			LOG.debug('On Deman Low server Data %(on_d_l)s', {'on_d_l': on_demand_low_servers})
			for i in on_demand_low_servers:
				if i['vm_state'] == 'active':
					server_name = i['uuid']
					subprocess.Popen("/opt/stack/nova/nova/scheduler/./nova_pause_server.sh %s" % (str(server_name)), shell=True)
					LOG.debug('Pausing Server %(name)s', {'name': i['name']})

	def get_attributes(self):
		attributes = {}
		if ThresholdManager.on_demand_high == 1:
			attributes['on_demand_high'] = 1
		if ThresholdManager.on_demand_low == 1:
			attributes['on_demand_low'] = 1
		if ThresholdManager.spot == 1:
			attributes['spot'] = 1
		return attributes