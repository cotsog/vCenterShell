from timeit import default_timer as timer
import qualipy.scripts.cloudshell_scripts_helpers as helpers
from pyVmomi import vim
from qualipy.api.cloudshell_api import *
from vCenterShell.commands.BaseCommand import BaseCommand
from vCenterShell.pycommon.common_name_utils import generate_unique_name


class DeployFromTemplateCommand(BaseCommand):
    """ Command to Create a VM from a template """

    def __init__(self, pv_service, cs_retriever_service, resource_connection_details_retriever):
        """
        :param pvService:   pyVmomiService Instance
        """
        self.pv_service = pv_service
        self.cs_retriever_service = cs_retriever_service
        self.resource_connection_details_retriever = resource_connection_details_retriever

    def deploy_from_template(self, data_holder):
        data_holder.connection_details
        data_holder.template_model
        data_holder.datastore_name
        data_holder.vm_cluster_model
        data_holder.power_on

        # connect
        si = self.pv_service.connect(data_holder.connection_details.host,
                                     data_holder.connection_details.username,
                                     data_holder.connection_details.password,
                                     data_holder.connection_details.port)
        content = si.RetrieveContent()

        start = timer()
        template = self.pv_service.get_obj(content, [vim.VirtualMachine], data_holder.template_model.template_name)
        end = timer()
        print "Template search took {0} seconds".format(end - start)

        if not template:
            raise ValueError("template with name '{0}' not found".format(data_holder.template_model.template_name))

        # generate unique name
        vm_name = generate_unique_name(data_holder.template_model.template_name)

        vm = self.pv_service.clone_vm(
            content=content,
            si=si,
            template=template,
            vm_name=vm_name,
            datacenter_name=None,
            vm_folder=data_holder.template_model.vm_folder,
            datastore_name=data_holder.datastore_name,
            cluster_name=data_holder.vm_cluster_model.cluster_name,
            resource_pool=data_holder.vm_cluster_model.resource_pool,
            power_on=data_holder.power_on)

        result = DeployResult(vm_name, vm.summary.config.instanceUuid)

        # disconnect
        self.pv_service.disconnect(si)

        return result

    def get_data_for_deployment(self):
        """ execute the command """
        resource_att = helpers.get_resource_context_details()

        # get vCenter resource name, template name, template folder
        template_model = self.cs_retriever_service.getVCenterTemplateAttributeData(resource_att)
        print "Template: {0}, Folder: {1}, vCenter: {2}".format(template_model.template_name, template_model.vm_folder, template_model.vCenter_resource_name)

        # get power state of the cloned VM
        power_on = self.cs_retriever_service.getPowerStateAttributeData(resource_att)
        print "Power On: {0}".format(power_on)

        # get cluster and resource pool
        vm_cluster_model = self.cs_retriever_service.getVMClusterAttributeData(resource_att)
        print "Cluster: {0}, Resource Pool: {1}".format(vm_cluster_model.cluster_name, vm_cluster_model.resource_pool)

        # get datastore
        datastore_name = self.cs_retriever_service.getVMStorageAttributeData(resource_att)
        print "Datastore: {0}".format(datastore_name)

        connection_details = self.resource_connection_details_retriever.get_connection_details(
                template_model.vCenter_resource_name)
        print "Connecting to: {0}, As: {1}, Pwd: {2}, Port: {3}".format(connection_details.host,
                                                                        connection_details.username,
                                                                        connection_details.password,
                                                                        connection_details.port)

        return DataHolder(resource_att,
                          connection_details,
                          template_model,
                          datastore_name,
                          vm_cluster_model,
                          power_on)

    def create_resource_for_deployed_vm(self, data_holder, deploy_result):
        reservation_id = helpers.get_reservation_context_details().id
        session = helpers.get_api_session()
        session.CreateResource("Virtual Machine", "Virtual Machine", deploy_result.vm_name, deploy_result.vm_name)
        session.AddResourcesToReservation(reservation_id, [deploy_result.vm_name])
        session.SetAttributesValues(
                    [ResourceAttributesUpdateRequest(deploy_result.vm_name,
                    [AttributeNameValue("vCenter Inventory Path", data_holder.template_model.vCenter_resource_name + "/" + data_holder.template_model.vm_folder),
                        AttributeNameValue("UUID", deploy_result.uuid),
                        AttributeNameValue("vCenter Template", data_holder.resource_att.attributes["vCenter Template"])])])

    def execute(self):
        data_holder = self.get_data_for_deployment()
        deploy_result = self.deploy_from_template(data_holder)
        self.create_resource_for_deployed_vm(data_holder, deploy_result)


class DataHolder(object):
    def __init__(self, resource_att, connection_details, template_model, datastore_name, vm_cluster_model, power_on):
        self.resource_att = resource_att
        self.connection_details = connection_details
        self.template_model = template_model
        self.datastore_name = datastore_name
        self.vm_cluster_model = vm_cluster_model
        self.power_on = power_on


class DeployResult(object):
    def __init__(self, vm_name, uuid):
        self.vm_name = vm_name
        self.uuid = uuid









