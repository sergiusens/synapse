/* Copyright 2019 New Vector Ltd
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

-- Track what users are in public rooms.
CREATE TABLE IF NOT EXISTS account_validity (
    user_id TEXT PRIMARY KEY,
    expiration_ts_ms BIGINT NOT NULL,
    sent_email BOOLEAN NOT NULL,
    refresh_string TEXT
);

CREATE INDEX account_validity_sent_email_idx ON account_validity(sent_email, expiration_ts_ms)
CREATE UNIQUE INDEX account_validity_refresh_string_idx ON account_validity(refresh_string)
