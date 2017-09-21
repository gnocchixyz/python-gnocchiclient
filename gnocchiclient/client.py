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
import sys

from keystoneauth1 import adapter
from keystoneauth1 import exceptions as k_exc

from gnocchiclient import exceptions


def Client(version, *args, **kwargs):
    module = 'gnocchiclient.v%s.client' % version
    __import__(module)
    client_class = getattr(sys.modules[module], 'Client')
    return client_class(*args, **kwargs)


class SessionClient(adapter.Adapter):
    def request(self, url, method, **kwargs):
        kwargs.setdefault('headers', kwargs.get('headers', {}))
        # NOTE(sileht): The standard call raises errors from
        # keystoneauth, where we need to raise the gnocchiclient errors.
        raise_exc = kwargs.pop('raise_exc', True)

        try:
            resp = super(SessionClient, self).request(url,
                                                      method,
                                                      raise_exc=False,
                                                      **kwargs)
        except k_exc.connection.ConnectFailure as e:
            raise exceptions.ConnectionFailure(
                message=str(e), url=url, method=method)
        except k_exc.connection.UnknownConnectionError as e:
            raise exceptions.UnknownConnectionError(
                message=str(e), url=url, method=method)
        except k_exc.connection.ConnectTimeout as e:
            raise exceptions.ConnectionTimeout(
                message=str(e), url=url, method=method)
        except k_exc.SSLError as e:
            raise exceptions.SSLError(message=str(e), url=url, method=method)

        if raise_exc and resp.status_code >= 400:
            raise exceptions.from_response(resp, method)
        return resp
