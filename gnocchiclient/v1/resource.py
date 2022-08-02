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

import ujson

from gnocchiclient import utils
from gnocchiclient.v1 import base


class ResourceManager(base.Manager):
    url = "v1/resource/"

    def list(self, resource_type="generic", details=False, history=False,
             limit=None, marker=None, sorts=None):
        """List resources.

        :param resource_type: Type of the resource
        :type resource_type: str
        :param details: Show all attributes of resources
        :type details: bool
        :param history: Show the history of resources
        :type history: bool
        :param limit: maximum number of resources to return
        :type limit: int
        :param marker: the last item of the previous page; we return the next
                       results after this value.
        :type marker: str
        :param sorts: list of resource attributes to order by. (example
                      ["user_id:desc-nullslast", "project_id:asc"]
        :type sorts: list of str
        """
        params = utils.build_pagination_options(
            details, history, limit, marker, sorts)
        resources = []
        page_url = "%s%s?%s" % (self.url, resource_type,
                                utils.dict_to_querystring(params))
        while page_url:
            page = self._get(page_url)
            resources.extend(page.json())
            if limit is None or len(resources) < limit:
                page_url = page.links.get("next", {'url': None})['url']
            else:
                break
        return resources

    def get(self, resource_type, resource_id, history=False):
        """Get a resource.

        :param resource_type: Type of the resource
        :type resource_type: str
        :param resource_id: ID of the resource
        :type resource_id: str
        :param history: Show the history of the resource
        :type history: bool
        """
        history = "/history" if history else ""
        url = self.url + "%s/%s%s" % (resource_type, resource_id, history)
        return self._get(url).json()

    def history(self, resource_type, resource_id, details=False,
                limit=None, marker=None, sorts=None):
        """Get a resource.

        :param resource_type: Type of the resource
        :type resource_type: str
        :param resource_id: ID of the resource
        :type resource_id: str
        :param details: Show all attributes of resources
        :type details: bool
        :param limit: maximum number of resources to return
        :type limit: int
        :param marker: the last item of the previous page; we returns the next
                       results after this value.
        :type marker: str
        :param sorts: list of resource attributes to order by. (example
                      ["user_id:desc-nullslast", "project_id:asc"]
        :type sorts: list of str
        """
        params = utils.build_pagination_options(details, False, limit, marker,
                                                sorts)
        url = "%s%s/%s/history?%s" % (self.url, resource_type, resource_id,
                                      utils.dict_to_querystring(params))
        return self._get(url).json()

    def create(self, resource_type, resource):
        """Create a resource.

        :param resource_type: Type of the resource
        :type resource_type: str
        :param resource: Attribute of the resource
        :type resource: dict
        """
        return self._post(
            self.url + resource_type,
            headers={'Content-Type': "application/json"},
            data=ujson.dumps(resource)).json()

    def update(self, resource_type, resource_id, resource):
        """Update a resource.

        :param resource_type: Type of the resource
        :type resource_type: str
        :param resource_id: ID of the resource
        :type resource_id: str
        :param resource: Attribute of the resource
        :type resource: dict
        """
        return self._patch(
            self.url + resource_type + "/" + resource_id,
            headers={'Content-Type': "application/json"},
            data=ujson.dumps(resource)).json()

    def delete(self, resource_id):
        """Delete a resource.

        :param resource_id: ID of the resource
        :type resource_id: str
        """
        self._delete(self.url + "generic/" + resource_id,
                     headers={"Accept": None})

    def batch_delete(self, query, resource_type="generic"):
        """Delete a batch of resources based on attribute values.

        :param resource_type: Type of the resource
        :type resource_type: str
        """
        if isinstance(query, dict):
            return self._delete(
                self.url + resource_type + "/",
                headers={'Content-Type': "application/json"},
                data=ujson.dumps(query)).json()
        return self._delete(
            self.url + resource_type + "/?filter=" + query,
            headers={'Content-Type': "application/json"}).json()

    def search(self, resource_type="generic", query=None, details=False,
               history=False, limit=None, marker=None, sorts=None):
        """List resources.

        :param resource_type: Type of the resource
        :type resource_type: str
        :param query: The query dictionary
        :type query: dict
        :param details: Show all attributes of resources
        :type details: bool
        :param history: Show the history of resources
        :type history: bool
        :param limit: maximum number of resources to return
        :type limit: int
        :param marker: the last item of the previous page; we returns the next
                       results after this value.
        :type marker: str
        :param sorts: list of resource attributes to order by. (example
                      ["user_id:desc-nullslast", "project_id:asc"]
        :type sorts: list of str

        See Gnocchi REST API documentation for the format
        of *query dictionary*
        http://gnocchi.osci.io/rest.html#searching-for-resources
        """
        query = query or {}
        params = utils.build_pagination_options(
            details, history, limit, marker, sorts)
        url = "v1/search/resource/%s?%%s" % resource_type
        resources = []

        if isinstance(query, dict):
            page_url = url % utils.dict_to_querystring(params)
            data = ujson.dumps(query)
        else:
            params['filter'] = query
            page_url = url % utils.dict_to_querystring(params)
            data = None

        while page_url:
            page = self._post(
                page_url, headers={'Content-Type': "application/json"},
                data=data)
            resources.extend(page.json())
            if limit is None or len(resources) < limit:
                page_url = page.links.get("next", {'url': None})['url']
            else:
                break
        return resources
