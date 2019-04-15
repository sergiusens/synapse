# -*- coding: utf-8 -*-
# Copyright 2019 New Vector Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from twisted.internet import defer

from ._base import client_v2_patterns
from synapse.api.errors import (
    SynapseError,
    Codes,
)
from synapse.handlers.account_validity import AccountValidityHandler
from synapse.http.servlet import RestServlet

logger = logging.getLogger(__name__)


class AccountValidityServlet(RestServlet):
    PATTERNS = client_v2_patterns("/account_validity/renew")

    def __init__(self, hs):
        """
        Args:
            hs (synapse.server.HomeServer): server
        """
        super(RegisterRestServlet, self).__init__()

        self.hs = hs
        self.account_activity_handler = AccountValidityHandler(hs)

    @defer.inlineCallbacks
    def on_GET(self, request):
        if b"token" not in request.args:
            raise SynapseError(400, "Missing renewal token")
        renewal_token = request.args[b"token"][0]

        yield self.account_activity_handler.renew_account(renewal_token)

def register_servlets(http_server):
    AccountValidityServlet().register(http_server)
