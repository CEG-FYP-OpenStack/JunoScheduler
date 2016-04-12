import MySQLdb

class InstanceManager(object):
	"""docstring for InstanceManager"""

	def __init__(self):
		super(InstanceManager, self).__init__()

	def node_details(self):
		node_details_array = []
		db = MySQLdb.connect("localhost","root","password","nova")
		cursor = db.cursor()
		cursor.execute("select free_disk_gb,free_ram_mb,vcpus,vcpus_used,id,local_gb,memory_mb,hypervisor_hostname from compute_nodes")

		data = cursor.fetchall()
		for row in data:
			node_details_dict = {}
			free_disk = row[0]
			free_ram = row[1]
			free_vcpus = row[2] - row[3]
			total_disk = row[5]
			total_ram = row[6]
			total_vcpus = row[2]
			nodename = row[7]
			hostname = row[7]
			uuid = row[4]
			
			node_details_dict['nodename'] = nodename
			node_details_dict['free_disk'] = free_disk
			node_details_dict['free_ram'] = free_ram
			node_details_dict['free_vcpus'] = free_vcpus
			node_details_dict['total_disk'] = total_disk
			node_details_dict['total_ram'] = total_ram
			node_details_dict['total_vcpus'] = total_vcpus
			node_details_dict['hostname'] = hostname
			node_details_array.append(node_details_dict)

		return node_details_array

	def feasible_nodes(self, vm):
		nodes = []

		db = MySQLdb.connect("localhost","root","password","nova")
		cursor = db.cursor()
		query_string = 'select id,hypervisor_hostname from compute_nodes where memory_mb >= %s and vcpus >= %s and local_gb >= %s'
		cursor.execute(query_string,(str(vm['ram']),str(vm['vcpus']),str(vm['disk'])))

		data = cursor.fetchall()

		for row in data:
			node_dict = {}
			hostname = row[1]
			uuid = row[0]

			node_dict['hostname'] = hostname
			node_dict['uuid'] = uuid
			nodes.append(node_dict)

		return nodes
	
	def vm_list(self,hostname):
		vm_list = []
		
		db = MySQLdb.connect("localhost","root","password","nova")
		cursor = db.cursor()
		query_string = 'select display_name,uuid,memory_mb,vcpus,root_gb from instances where host=%s and vm_state=%s '
		cursor.execute(query_string,(str(vm['hostname']),'active'))

		data = cursor.fetchall()

		for row in data:
			vm_data = {}
			uuid = row[1]
			display_name = row[0]
			ram = row[2]
			vcpus = row[3]
			disk = row[4]

			vm_data['ram'] = ram
			vm_data['vcpus'] = vcpus
			vm_data['disk'] = disk
			vm_data['uuid'] = uuid
			vm_data['name'] = display_name

			vm_list.append(vm_data)
		return vm_list

	def live_migrate(self,migration_list):
		for vm in migration_list:
			vm_id = str(vm[0]['uuid'])
			vm_name = str(vm[0]['name'])
			hostname = str(vm[1])
			subprocess.Popen("/opt/stack/nova/nova/scheduler/./nova_server_migration.sh %s %s" % (vm_id,hostname), shell=True)
			LOG.debug("Migrating VM %(vm_name)s to %(node_name)s..", { 'vm_name': vm_name,'node_name': hostname })