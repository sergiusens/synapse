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

import email.mime.multipart
import email.utils
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from twisted.internet import defer

from synapse.api.errors import StoreError
from synapse.push import mailer
from synapse.types import UserID
from synapse.util import stringutils
from synapse.util.logcontext import make_deferred_yieldable

logger = logging.getLogger(__name__)


class AccountValidityHandler(object):
    def __init__(self, hs):
        self.hs = hs
        self.store = self.hs.get_datastore()
        self.sendmail = self.hs.get_sendmail()

        self._account_validity = self.hs.config.account_validity
        self._app_name = self.hs.config.email_app_name

        try:
            self._subject = self.hs.config.renew_email_subject % {
                "app": self._app_name,
            }
        except TypeError:
            self._subject = self.hs.config.renew_email_subject

        try:
            self._from_string = self.hs.config.email_notif_from % {
                "app": self._app_name,
            }
        except TypeError:
            self._from_string = self.hs.config.email_notif_from

        self._raw_from = email.utils.parseaddr(self._from_string)[1]

        self._template_html, self._template_text = mailer.load_jinja2_templates(
            config=self.hs.config,
            template_html_name=self.hs.config.email_expiry_template_html,
            template_text_name=self.hs.config.email_expiry_template_text,
        )

    @defer.inlineCallbacks
    def send_refresh_email(self, user, expiration_ts):
        addresses = yield self._get_email_addresses_for_user(user)

        try:
            user_display_name = yield self.store.get_profile_displayname(
                UserID.from_string(user).localpart
            )
            if user_display_name is None:
                user_display_name = user
        except StoreError:
            user_display_name = user

        refresh_string = yield self._get_refresh_string(user)
        url = "%s_matrix/client/unstable/account_validity/refresh?token=%s" % (
            self.hs.config.public_baseurl,
            refresh_string,
        )

        template_vars = {
            "display_name": user_display_name,
            "expiration_ts": expiration_ts,
            "url": url,
        }

        html_text = self._template_html.render(**template_vars)
        html_part = MIMEText(html_text, "html", "utf8")

        plain_text = self._template_text.render(**template_vars)
        text_part = MIMEText(plain_text, "plain", "utf8")

        for address in addresses:
            raw_to = email.utils.parseaddr(address)[1]

            multipart_msg = MIMEMultipart('alternative')
            multipart_msg['Subject'] = self._subject
            multipart_msg['From'] = self._from_string
            multipart_msg['To'] = address
            multipart_msg['Date'] = email.utils.formatdate()
            multipart_msg['Message-ID'] = email.utils.make_msgid()
            multipart_msg.attach(text_part)
            multipart_msg.attach(html_part)

            yield make_deferred_yieldable(self.sendmail(
                self.hs.config.email_smtp_host,
                self._raw_from, raw_to, multipart_msg.as_string().encode('utf8'),
                reactor=self.hs.get_reactor(),
                port=self.hs.config.email_smtp_port,
                requireAuthentication=self.hs.config.email_smtp_user is not None,
                username=self.hs.config.email_smtp_user,
                password=self.hs.config.email_smtp_pass,
                requireTransportSecurity=self.hs.config.require_transport_security
            ))

    @defer.inlineCallbacks
    def _get_email_addresses_for_user(self, user):
        threepids = yield self.store.user_get_threepids(user)

        addresses = []
        for threepid in threepids:
            if threepid["medium"] == "email":
                addresses.append(threepid["address"])

        defer.returnValue(addresses)

    @defer.inlineCallbacks
    def _get_refresh_string(self, user):
        attempts = 0
        while attempts < 5:
            try:
                refresh_string = stringutils.random_string(32)
                yield self.store.set_refresh_string_for_user(user, refresh_string)
                defer.returnValue(refresh_string)
            except StoreError:
                attempts += 1
        raise StoreError(500, "Couldn't generate a unique string as refresh string.")
