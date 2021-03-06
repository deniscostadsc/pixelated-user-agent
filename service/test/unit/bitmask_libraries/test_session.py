#
# Copyright (c) 2014 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.

from mock import patch
from mock import MagicMock
from twisted.internet import defer
from pixelated.bitmask_libraries.session import LeapSession, SessionCache
from test_abstract_leap import AbstractLeapTest
from leap.common.events.catalog import KEYMANAGER_FINISHED_KEY_GENERATION


class SessionTest(AbstractLeapTest):

    def setUp(self):
        super(SessionTest, self).setUp()
        self.smtp_mock = MagicMock()

    @patch('pixelated.bitmask_libraries.session.register')
    @patch('pixelated.bitmask_libraries.session.IMAPAccount')
    @defer.inlineCallbacks
    def test_background_jobs_are_started_during_initial_sync(self, *unused):
        mailFetcherMock = MagicMock()
        with patch('pixelated.bitmask_libraries.session.reactor.callFromThread', new=_execute_func) as _:
            with patch.object(LeapSession, '_create_incoming_mail_fetcher', return_value=mailFetcherMock) as _:
                session = self._create_session()
                yield session.initial_sync()
                mailFetcherMock.startService.assert_called_once()

    @patch('pixelated.bitmask_libraries.session.register')
    @patch('pixelated.bitmask_libraries.session.unregister')
    @patch('pixelated.bitmask_libraries.session.IMAPAccount')
    @defer.inlineCallbacks
    def test_that_close_stops_background_jobs(self, *unused):
        with patch('pixelated.bitmask_libraries.session.reactor.callFromThread', new=_execute_func) as _:
            with patch('pixelated.bitmask_libraries.session.LeapSession._create_incoming_mail_fetcher') as mail_fetcher_mock:
                session = self._create_session()
                yield session.initial_sync()
                session.close()
                mail_fetcher_mock.stopService.assert_called_once()

    def test_that_sync_deferes_to_soledad(self):
        with patch('pixelated.bitmask_libraries.session.reactor.callFromThread', new=_execute_func) as _:
            with patch('pixelated.bitmask_libraries.session.LeapSession._create_incoming_mail_fetcher') as mail_fetcher_mock:
                session = self._create_session()
                yield session.sync()
                self.soledad_session.sync.assert_called_once()

    def test_session_registers_to_generated_keys(self):
        email = 'someone@somedomain.tld'
        self.provider.address_for.return_value = email
        with patch('pixelated.bitmask_libraries.session.register') as register_mock:
            session = self._create_session()

            register_mock.assert_called_once_with(KEYMANAGER_FINISHED_KEY_GENERATION, session._set_fresh_account, uid=email)

    @patch('pixelated.bitmask_libraries.session.register')
    def test_close_unregisters_from_generate_keys_events(self, _):
        email = 'someone@somedomain.tld'
        self.provider.address_for.return_value = email
        session = self._create_session()

        with patch('pixelated.bitmask_libraries.session.unregister') as unregister_mock:
            session.close()

            unregister_mock.assert_called_once_with(KEYMANAGER_FINISHED_KEY_GENERATION, uid=email)

    @patch('pixelated.bitmask_libraries.session.register')
    def test_close_stops_soledad(self, _):
        email = 'someone@somedomain.tld'
        self.provider.address_for.return_value = email
        session = self._create_session()

        with patch('pixelated.bitmask_libraries.session.unregister') as unregister_mock:
            session.close()

        self.soledad_session.close.assert_called_once_with()

    @patch('pixelated.bitmask_libraries.session.register')
    def test_close_removes_session_from_cache(self, _):
        email = 'someone@somedomain.tld'
        self.provider.address_for.return_value = email
        session = self._create_session()

        key = SessionCache.session_key(self.provider, self.auth.username)
        SessionCache.remember_session(key, session)

        self.assertEqual(session, SessionCache.lookup_session(key))

        with patch('pixelated.bitmask_libraries.session.unregister') as unregister_mock:
            session.close()

        self.assertIsNone(SessionCache.lookup_session(key))

    @patch('pixelated.bitmask_libraries.session.register')
    def test_close_ends_account_session(self, _):
        account_mock = MagicMock()
        email = 'someone@somedomain.tld'
        self.provider.address_for.return_value = email
        session = self._create_session()
        session.account = account_mock

        with patch('pixelated.bitmask_libraries.session.unregister') as unregister_mock:
            session.close()

        account_mock.end_session.assert_called_once_with()

    @patch('pixelated.bitmask_libraries.session.register')
    def test_session_fresh_is_initially_false(self, _):
        session = self._create_session()

        self.assertFalse(session.fresh_account)

    @patch('pixelated.bitmask_libraries.session.register')
    def test_session_sets_status_to_fresh_on_key_generation_event(self, _):
        session = self._create_session()
        self.provider.address_for.return_value = 'someone@somedomain.tld'

        session._set_fresh_account(None, 'someone@somedomain.tld')

        self.assertTrue(session.fresh_account)

    @patch('pixelated.bitmask_libraries.session.register')
    def test_session_does_not_set_status_fresh_for_unkown_emails(self, _):
        session = self._create_session()
        self.provider.address_for.return_value = 'someone@somedomain.tld'

        session._set_fresh_account(None, 'another_email@somedomain.tld')

        self.assertFalse(session.fresh_account)

    @patch('pixelated.bitmask_libraries.session.register')
    @patch('pixelated.bitmask_libraries.session.unregister')
    @patch('pixelated.bitmask_libraries.session.IMAPAccount')
    @defer.inlineCallbacks
    def test_session_initial_sync_only_triggered_once(self, *unused):
        mailFetcherMock = MagicMock()
        with patch('pixelated.bitmask_libraries.session.reactor.callFromThread', new=_execute_func) as _:
            with patch.object(LeapSession, '_create_incoming_mail_fetcher', return_value=mailFetcherMock) as _:
                session = self._create_session()
                session._has_been_synced = True
                yield session.initial_sync()
                self.assertFalse(mailFetcherMock.startService.called)

    def _create_session(self):
        return LeapSession(self.provider, self.auth, self.mail_store, self.soledad_session, self.nicknym, self.smtp_mock)


def _execute_func(func):
    func()
