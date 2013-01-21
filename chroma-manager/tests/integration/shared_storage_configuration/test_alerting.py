

import time
from testconfig import config
from tests.integration.core.chroma_integration_testcase import ChromaIntegrationTestCase


# Updating the status is a (very) asynchronous operation
# 10 second periodic update from the agent, then the state change goes
# into a queue serviced at some point in the future (fractions of a second
# on an idle system, but not bounded)
UPDATE_DELAY = 20


class TestEvents(ChromaIntegrationTestCase):
    def test_reboot_event(self):
        """Test that when a host is restarted, a single corresponding event is generated"""

        # Add one host
        self.add_hosts([config['lustre_servers'][0]['address']])

        # Record the start time for later querying of events since
        # NB using a time from chroma-manager so as not to depend
        # on the test runner's clock
        host = self.get_list("/api/host/")[0]
        start_time = host['state_modified_at']

        # Reboot
        self.remote_operations.kill_server(host['fqdn'])
        self.remote_operations.await_server_boot(host['fqdn'])

        time.sleep(UPDATE_DELAY)

        events = self.get_list("/api/event/", {'created_at__gte': start_time})

        reboot_events = [e for e in events if e['message'].find("restarted") != -1]
        self.assertEqual(len(reboot_events), 1, events)


class TestAlerting(ChromaIntegrationTestCase):
    def test_alerts(self):
        fs_id = self.create_filesystem_simple()

        fs = self.get_by_uri("/api/filesystem/%s/" % fs_id)
        host = self.get_list("/api/host/")[0]

        alerts = self.get_list("/api/alert/", {'active': True, 'dismissed': False})
        self.assertListEqual(alerts, [])

        mgt = fs['mgt']

        # Check the alert is raised when the target unexpectedly stops
        self.remote_operations.stop_target(host['fqdn'], mgt['ha_label'])
        time.sleep(UPDATE_DELAY)
        self.assertHasAlert(mgt['resource_uri'])
        self.assertState(mgt['resource_uri'], 'unmounted')

        # Check the alert is cleared when restarting the target
        self.remote_operations.start_target(host['fqdn'], mgt['ha_label'])

        time.sleep(UPDATE_DELAY)
        self.assertNoAlerts(mgt['resource_uri'])

        # Check that no alert is raised when intentionally stopping the target
        self.set_state(mgt['resource_uri'], 'unmounted')
        self.assertNoAlerts(mgt['resource_uri'])

        # Stop the filesystem so that we can play with the host
        self.set_state(fs['resource_uri'], 'stopped')

        # Check that an alert is raised when lnet unexpectedly goes down
        host = self.get_by_uri(host['resource_uri'])
        self.assertEqual(host['state'], 'lnet_up')
        self.remote_operations.stop_lnet(host['fqdn'])
        time.sleep(UPDATE_DELAY)
        self.assertHasAlert(host['resource_uri'])
        self.assertState(host['resource_uri'], 'lnet_down')

        # Check that alert is dropped when lnet is brought back up
        self.set_state(host['resource_uri'], 'lnet_up')
        self.assertNoAlerts(host['resource_uri'])

        # Check that no alert is raised when intentionally stopping lnet
        self.set_state(host['resource_uri'], 'lnet_down')
        self.assertNoAlerts(host['resource_uri'])

        # Raise all the alerts we can
        self.set_state("/api/filesystem/%s/" % fs_id, 'available')
        for target in self.get_list("/api/target/"):
            self.remote_operations.stop_target(host['fqdn'], target['ha_label'])
        self.remote_operations.stop_lnet(host['fqdn'])
        time.sleep(UPDATE_DELAY)
        self.assertEqual(len(self.get_list('/api/alert/', {'active': True})), 4)

        # Remove everything
        self.graceful_teardown(self.chroma_manager)

        # Check that all the alerts are gone too
        self.assertListEqual(self.get_list('/api/alert/', {'active': True}), [])
