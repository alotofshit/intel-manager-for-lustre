#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


from django.core.handlers.wsgi import WSGIHandler
import gevent.wsgi

from chroma_core.services.http_agent.host_state import HostStateCollection, HostStatePoller
from chroma_core.services.http_agent.queues import HostQueueCollection, AmqpRxForwarder, AmqpTxForwarder
from chroma_core.services.http_agent.sessions import SessionCollection, AgentSessionRpc
from chroma_core.services import ChromaService, ServiceThread, log_register
from chroma_agent_comms.views import MessageView

from settings import HTTP_AGENT_PORT


log = log_register(__name__)


# TODO: get a firm picture of whether upgrades from 1.0.x will be done -- if so then
# a script is needed to set up an existing SSH-based system with certificates.

# TODO: interesting tests:
# * All permutations of startup order (with some meaningful delay between startups) of service, http_agent, agent
# * Restarting each component in the chain and checking the system recovers to a sensible state
# * The above for each of the different sets of message handling logic on the service side (plugin_runner, job_scheduler, one of lustre/logs)
# * For all services, check they terminate with SIGTERM in a timely manner (including when they are
#   doing something).  Check this in dev mode and in production (init scripts/supervisor) mode.
# * Run through some error-less scenarios and grep the logs for WARN and ERROR
# * Modify some client and server certificates slightly and check they are rejected (i.e.
#   check that we're really verifying the signatures and not just believing certificates)
#
# * remove a host and then try connecting with that host's old certificate
# * For all the calls to security_log, reproduce the situation and check they hit
#
# * check that service stop and start on the agent works
# * check that after adding and removing a host, no chroma-agent or chroma-agent-daemon services are running


# TODO: on the agent side, check that we still have a nice way to get a dump of the
# device detection JSON output *and* the corresponding outputs from the wrapped commands


class Service(ChromaService):
    def reset_session(self, fqdn, plugin, session_id):
        return self.sessions.reset_session(fqdn, plugin, session_id)

    def remove_host(self, fqdn):
        self.sessions.remove_host(fqdn)
        self.queues.remove_host(fqdn)
        self.hosts.remove_host(fqdn)

        # TODO: ensure there are no GETs left in progress after this completes
        # TODO: drain plugin_rx_queue so that anything we will send to AMQP has been sent before this returns

    def __init__(self):
        super(Service, self).__init__()

        self.queues = HostQueueCollection()
        self.sessions = SessionCollection(self.queues)
        self.hosts = HostStateCollection()

    def run(self):
        self.amqp_tx_forwarder = AmqpTxForwarder(self.queues)
        self.amqp_rx_forwarder = AmqpRxForwarder(self.queues)

        # This thread listens to an AMQP queue and appends incoming messages
        # to queues for retransmission to agents
        tx_svc_thread = ServiceThread(self.amqp_tx_forwarder)
        # This thread listens to local queues and appends received messages
        # to an AMQP queue
        rx_svc_thread = ServiceThread(self.amqp_rx_forwarder)
        rx_svc_thread.start()
        tx_svc_thread.start()

        # This thread services session management RPCs, so that other
        # services can explicitly request a session reset
        session_rpc_thread = ServiceThread(AgentSessionRpc(self))
        session_rpc_thread.start()

        # Hook up the request handler
        MessageView.queues = self.queues
        MessageView.sessions = self.sessions
        MessageView.hosts = self.hosts

        # The thread for generating HostOfflineAlerts
        host_checker_thread = ServiceThread(HostStatePoller(self.hosts))
        host_checker_thread.start()

        # The main thread serves incoming requests to exchanges messages
        # with agents, until it is interrupted (gevent handles signals for us)
        self.server = gevent.wsgi.WSGIServer(('', HTTP_AGENT_PORT), WSGIHandler())
        self.server.serve_forever()

        session_rpc_thread.stop()
        tx_svc_thread.stop()
        rx_svc_thread.stop()
        host_checker_thread.stop()
        session_rpc_thread.join()
        tx_svc_thread.join()
        tx_svc_thread.join()
        host_checker_thread.join()

    def stop(self):
        self.server.stop()
