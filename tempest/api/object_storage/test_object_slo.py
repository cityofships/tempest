# Copyright 2013 NTT Corporation
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

from oslo_serialization import jsonutils as json

from oslo_utils.secretutils import md5
from tempest.api.object_storage import base
from tempest.common import utils
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators

# Each segment, except for the final one, must be at least 1 megabyte
MIN_SEGMENT_SIZE = 1024 * 1024


class ObjectSloTest(base.BaseObjectTest):
    """Test static large object"""

    def setUp(self):
        super(ObjectSloTest, self).setUp()
        self.container_name = self.create_container()
        self.objects = []

    def tearDown(self):
        self.delete_containers()
        super(ObjectSloTest, self).tearDown()

    def _create_object(self, container_name, object_name, data, params=None):
        resp, _ = self.object_client.create_object(container_name,
                                                   object_name,
                                                   data,
                                                   params)
        self.objects.append(object_name)

        return resp

    def _create_manifest(self):
        # Create a manifest file for SLO uploading
        object_name = data_utils.rand_name(name='TestObject')
        object_name_base_1 = object_name + '_01'
        object_name_base_2 = object_name + '_02'
        data_size = MIN_SEGMENT_SIZE
        self.content = data_utils.random_bytes(data_size)
        self._create_object(self.container_name,
                            object_name_base_1,
                            self.content)
        self._create_object(self.container_name,
                            object_name_base_2,
                            self.content)

        path_object_1 = '/%s/%s' % (self.container_name,
                                    object_name_base_1)
        path_object_2 = '/%s/%s' % (self.container_name,
                                    object_name_base_2)
        data_manifest = [{'path': path_object_1,
                          'etag': md5(self.content,
                                      usedforsecurity=False).hexdigest(),
                          'size_bytes': data_size},
                         {'path': path_object_2,
                          'etag': md5(self.content,
                                      usedforsecurity=False).hexdigest(),
                          'size_bytes': data_size}]

        return json.dumps(data_manifest)

    def _create_large_object(self):
        # Create a large object for preparation of testing various SLO
        # features
        manifest = self._create_manifest()

        params = {'multipart-manifest': 'put'}
        object_name = data_utils.rand_name(name='TestObject')
        self._create_object(self.container_name,
                            object_name,
                            manifest,
                            params)
        return object_name

    def _assertHeadersSLO(self, resp, method):
        # When sending GET or HEAD requests to SLO the response contains
        # 'X-Static-Large-Object' header
        if method in ('GET', 'HEAD'):
            self.assertIn('x-static-large-object', resp)
            self.assertEqual(resp['x-static-large-object'], 'True')

        # Etag value of a large object is enclosed in double-quotations.
        # After etag quotes are checked they are removed and the response is
        # checked if all common headers are present and well formatted
        self.assertTrue(resp['etag'].startswith('\"'))
        self.assertTrue(resp['etag'].endswith('\"'))
        resp['etag'] = resp['etag'].strip('"')
        self.assertHeaders(resp, 'Object', method)

    @decorators.idempotent_id('2c3f24a6-36e8-4711-9aa2-800ee1fc7b5b')
    @utils.requires_ext(extension='slo', service='object')
    def test_upload_manifest(self):
        """Test creating static large object from multipart manifest"""
        manifest = self._create_manifest()

        params = {'multipart-manifest': 'put'}
        object_name = data_utils.rand_name(name='TestObject')
        resp = self._create_object(self.container_name,
                                   object_name,
                                   manifest,
                                   params)

        self._assertHeadersSLO(resp, 'PUT')

    @decorators.idempotent_id('e69ad766-e1aa-44a2-bdd2-bf62c09c1456')
    @utils.requires_ext(extension='slo', service='object')
    def test_list_large_object_metadata(self):
        """Test listing static large object metadata

        List static large object metadata using multipart manifest
        """
        object_name = self._create_large_object()

        resp, _ = self.object_client.list_object_metadata(
            self.container_name,
            object_name)

        self._assertHeadersSLO(resp, 'HEAD')

    @decorators.idempotent_id('49bc49bc-dd1b-4c0f-904e-d9f10b830ee8')
    @utils.requires_ext(extension='slo', service='object')
    def test_retrieve_large_object(self):
        """Test listing static large object using multipart manifest"""
        object_name = self._create_large_object()

        resp, body = self.object_client.get_object(
            self.container_name,
            object_name)

        self._assertHeadersSLO(resp, 'GET')

        sum_data = self.content + self.content
        self.assertEqual(body, sum_data)

    @decorators.idempotent_id('87b6dfa1-abe9-404d-8bf0-6c3751e6aa77')
    @utils.requires_ext(extension='slo', service='object')
    def test_delete_large_object(self):
        """Test deleting static large object using multipart manifest"""
        object_name = self._create_large_object()

        params_del = {'multipart-manifest': 'delete'}
        resp, _ = self.object_client.delete_object(
            self.container_name,
            object_name,
            params=params_del)

        self.assertHeaders(resp, 'Object', 'DELETE')

        resp, _ = self.container_client.list_container_objects(
            self.container_name)
        self.assertEqual(int(resp['x-container-object-count']), 0)
