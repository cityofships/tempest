# Copyright 2013 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempest.api.identity import base
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc


class ServicesTestJSON(base.BaseIdentityV3AdminTest):
    """Test keystone services"""

    def _del_service(self, service_id):
        # Used for deleting the services created in this class
        self.services_client.delete_service(service_id)
        # Checking whether service is deleted successfully
        self.assertRaises(lib_exc.NotFound, self.services_client.show_service,
                          service_id)

    @decorators.attr(type='smoke')
    @decorators.idempotent_id('5193aad5-bcb7-411d-85b0-b3b61b96ef06')
    def test_create_update_get_service(self):
        """Test creating, updating and getting of keystone service"""
        # Creating a Service
        name = data_utils.rand_name('service')
        serv_type = data_utils.rand_name('type')
        desc = data_utils.rand_name('description')
        create_service = self.services_client.create_service(
            type=serv_type, name=name, description=desc)['service']
        self.addCleanup(self._del_service, create_service['id'])
        self.assertIsNotNone(create_service['id'])

        # Verifying response body of create service
        expected_data = {'name': name, 'type': serv_type, 'description': desc}
        self.assertLessEqual(expected_data.items(), create_service.items())

        # Update description
        s_id = create_service['id']
        resp1_desc = create_service['description']
        s_desc2 = data_utils.rand_name('desc2')
        update_service = self.services_client.update_service(
            s_id, description=s_desc2)['service']
        resp2_desc = update_service['description']

        self.assertNotEqual(resp1_desc, resp2_desc)

        # Get service
        fetched_service = self.services_client.show_service(s_id)['service']
        resp3_desc = fetched_service['description']

        self.assertEqual(resp2_desc, resp3_desc)
        self.assertLessEqual(update_service.items(), fetched_service.items())

    @decorators.idempotent_id('d1dcb1a1-2b6b-4da8-bbb8-5532ef6e8269')
    def test_create_service_without_description(self):
        """Create a keystone service only with name and type"""
        name = data_utils.rand_name('service')
        serv_type = data_utils.rand_name('type')
        service = self.services_client.create_service(
            type=serv_type, name=name)['service']
        self.addCleanup(self.services_client.delete_service, service['id'])
        expected_data = {'name': name, 'type': serv_type}
        self.assertLessEqual(expected_data.items(), service.items())

    @decorators.idempotent_id('e55908e8-360e-439e-8719-c3230a3e179e')
    def test_list_services(self):
        """Create, List, Verify and Delete Keystone Services"""
        service_ids = list()
        service_types = list()
        for _ in range(3):
            name = data_utils.rand_name(self.__class__.__name__ + '-Service')
            serv_type = data_utils.rand_name(self.__class__.__name__ + '-Type')
            create_service = self.services_client.create_service(
                type=serv_type, name=name)['service']
            self.addCleanup(self.services_client.delete_service,
                            create_service['id'])
            service_ids.append(create_service['id'])
            service_types.append(serv_type)

        # List and Verify Services
        services = self.services_client.list_services()['services']
        fetched_ids = [service['id'] for service in services]
        found = [s for s in fetched_ids if s in service_ids]
        self.assertEqual(len(found), len(service_ids))

        # Check that filtering by service type works.
        for serv_type in service_types:
            fetched_services = self.services_client.list_services(
                type=serv_type)['services']
            self.assertEqual(1, len(fetched_services))
            self.assertEqual(serv_type, fetched_services[0]['type'])
