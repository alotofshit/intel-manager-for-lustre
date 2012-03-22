
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================


"""The resource manager is the home of the global view of the resources populated from
all plugins.  StoragePlugin instances have their own local caches of resources, which
they use to periodically update this central store.

Concurrency:
    This code is written for multi-threaded use within a single process.
    It is not safe to have multiple processes running plugins at this stage.
    We serialize operations from different plugins using a big lock, and
    we use the autocommit decorator on persistence functions because
    otherwise we would have to explicitly commit at the start of
    each one to see changes from other threads.

WARNING:
    There is a globl instance of ResourceManager initialized in this module, and
    its initialization does a significant amount of DB activity.  Don't import
    this module unless you're really going to use it.
"""

from chroma_core.lib.storage_plugin.log import storage_plugin_log as log
from chroma_core.lib.storage_plugin.resource import ScannableId, GlobalId
from chroma_core.lib.util import all_subclasses

from chroma_core.models import ManagedHost, ManagedTarget
from chroma_core.models import Lun, LunNode

from django.db import transaction

from collections import defaultdict
import threading


class PluginSession(object):
    def __init__(self, scannable_id, update_period):
        self.local_id_to_global_id = {}
        self.scannable_id = scannable_id
        self.update_period = update_period


class EdgeIndex(object):
    def __init__(self):
        # Define: Edges go 'from' child 'to' parent
        # Map of 'from' to (from, to)
        self._parent_from_edge = defaultdict(set)
        # Map of 'to' to (from, to)
        self._parent_to_edge = defaultdict(set)

    def get_parents(self, child):
        return [e[1] for e in self._parent_from_edge[child]]

    def get_children(self, parent):
        return [e[0] for e in self._parent_to_edge[parent]]

    def add_parent(self, child, parent):
        edge = (child, parent)
        self._parent_from_edge[child].add(edge)
        self._parent_to_edge[parent].add(edge)

    def remove_parent(self, child, parent):
        edge = (child, parent)
        self._parent_from_edge[child].remove(edge)
        self._parent_to_edge[parent].remove(edge)

    def remove_node(self, node):
        edges = set()
        edges = edges | self._parent_from_edge[node]
        edges = edges | self._parent_to_edge[node]
        for e in edges:
            for k, v in self._parent_from_edge.items():
                v.remove(e)
            for k, v in self._parent_to_edge.items():
                v.remove(e)
        del self._parent_to_edge[node]
        del self._parent_from_edge[node]

    def populate(self):
        from chroma_core.models import StorageResourceRecord
        from django.db.models import Q
        for srr in StorageResourceRecord.objects.filter(~Q(parents = None)).values('id', 'parents'):
            child = srr['id']
            parent = srr['parents']
            self.add_parent(child, parent)


class SubscriberIndex(object):
    def __init__(self):
        # Map (field_name, field_value) to list of resource global id
        self._subscribe_value_to_id = defaultdict(set)
        self._provide_value_to_id = defaultdict(set)

        # List of (provider, Provide object)
        self._all_subscriptions = []
        # FIXME: pass this in instead?
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        from chroma_core.lib.storage_plugin import relations

        subscriptions = {}

        for id, klass in storage_plugin_manager.resource_class_id_to_class.items():
            for relation in klass._relations:
                if isinstance(relation, relations.Provide):
                    subscription = relations.Subscribe(klass, relation.attributes)
                    relation.provide_to._relations.append(subscription)
                    for sc in all_subclasses(relation.provide_to):
                        sc._relations.append(subscription)

        for id, klass in storage_plugin_manager.resource_class_id_to_class.items():
            klass._subscriptions = []
            for relation in klass._relations:
                if isinstance(relation, relations.Subscribe):
                    subscriptions[relation.key] = relation
                    klass._subscriptions.append(relation)

        self._all_subscriptions = subscriptions.values()

    def what_provides(self, resource):
        """What provides things that this resource subscribes to?"""
        result = set()
        for subscription in resource._subscriptions:
            result |= self._provide_value_to_id[(subscription.key, subscription.val(resource))]
        return result

    def what_subscribes(self, resource):
        """What subscribes to this resources?"""
        result = set()
        for subscription in self._all_subscriptions:
            if isinstance(resource, subscription.subscribe_to):
                result |= self._subscribe_value_to_id[(subscription.key, subscription.val(resource))]
        return result

    def add_provider(self, resource_id, key, value):
        self._provide_value_to_id[(key, value)].add(resource_id)

    def remove_provider(self, resource_id, key, value):
        self._provide_value_to_id[(key, value)].remove(resource_id)

    def add_subscriber(self, resource_id, key, value):
        self._subscribe_value_to_id[(key, value)].add(resource_id)

    def remove_subscriber(self, resource_id, key, value):
        self._subscribe_value_to_id[(key, value)].remove(resource_id)

    def add_resource(self, resource_id, resource = None):
        if not resource:
            from chroma_core.models import StorageResourceRecord
            resource = StorageResourceRecord.objects.get(pk = resource_id).to_resource()

        for subscription in self._all_subscriptions:
            if isinstance(resource, subscription.subscribe_to):
                self.add_provider(resource_id, subscription.key, subscription.val(resource))
        for subscription in resource._subscriptions:
            self.add_subscriber(resource_id, subscription.key, subscription.val(resource))

    def remove_resource(self, resource_id, resource = None):
        log.debug("SubscriberIndex.remove_resource %s" % resource_id)
        if not resource:
            from chroma_core.models import StorageResourceRecord
            resource = StorageResourceRecord.objects.get(pk = resource_id).to_resource()

        for subscription in self._all_subscriptions:
            if isinstance(resource, subscription.subscribe_to):
                log.debug("SubscriberIndex.remove provider %s" % subscription.key)
                self.remove_provider(resource_id, subscription.key, subscription.val(resource))
        for subscription in resource._subscriptions:
            log.debug("SubscriberIndex.remove subscriber %s" % subscription.key)
            self.remove_subscriber(resource_id, subscription.key, subscription.val(resource))

    def populate(self):
        from chroma_core.models import StorageResourceRecord
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        for resource_class_id, resource_class in storage_plugin_manager.get_all_resources():
            for subscription in self._all_subscriptions:
                if issubclass(resource_class, subscription.subscribe_to):
                    records = StorageResourceRecord.objects.filter(
                            resource_class = resource_class_id)
                    for r in records:
                        resource = r.to_resource()
                        self.add_provider(r.id, subscription.key, subscription.val(resource))

            for subscription in resource_class._subscriptions:
                records = StorageResourceRecord.objects.filter(
                        resource_class = resource_class_id)
                for r in records:
                    resource = r.to_resource()
                    self.add_subscriber(r.id, subscription.key, subscription.val(resource))


class ResourceManager(object):
    def __init__(self):
        self._sessions = {}
        self._instance_lock = threading.Lock()

        # Map of (resource_global_id, alert_class) to AlertState pk
        self._active_alerts = {}

        # In-memory bidirectional lookup table of resource parent-child relationships
        self._edges = EdgeIndex()
        self._edges.populate()

        # In-memory lookup table of 'provide' and 'subscribe' resource attributes
        self._subscriber_index = SubscriberIndex()
        self._subscriber_index.populate()

    def session_open(self,
            scannable_id,
            scannable_local_id,
            initial_resources,
            update_period):
        log.debug(">> session_open %s (%s resources)" % (scannable_id, len(initial_resources)))
        with self._instance_lock:
            if scannable_id in self._sessions:
                log.warning("Clearing out old session for scannable ID %s" % scannable_id)
                del self._sessions[scannable_id]

            session = PluginSession(scannable_id, update_period)
            #session.local_id_to_global_id[scannable_local_id] = scannable_id
            self._sessions[scannable_id] = session
            self._persist_new_resources(session, initial_resources)
            self._cull_lost_resources(session, initial_resources)

            # Special case for agent-reported resources: update Lun and LunNode
            # objects to interface with the world of Lustre
            # TODO: don't just do this at creation, do updates too
            self._persist_lun_updates(scannable_id)

            # Plugins are allowed to create VirtualMachine objects, indicating that
            # we should created a ManagedHost to go with it (e.g. discovering VMs)
            self._persist_created_hosts(session, scannable_id)

        log.debug("<< session_open %s" % scannable_id)

    def session_close(self, scannable_id):
        with self._instance_lock:
            try:
                del self._sessions[scannable_id]
            except KeyError:
                log.warning("Cannot remove session for %s, it does not exist" % scannable_id)

    @transaction.commit_on_success
    def _persist_created_hosts(self, session, scannable_id):
        log.debug("_persist_created_hosts")

        # FIXME: look up more efficiently (don't currently keep an in-memory record of the
        # class of each resource)
        def get_session_resources_of_type(session, klass):
            for record_pk in session.local_id_to_global_id.values():
                from chroma_core.models import StorageResourceRecord
                record = StorageResourceRecord.objects.get(pk = record_pk)
                resource = record.to_resource()
                if isinstance(resource, klass):
                    yield (record, resource)

        from chroma_core.lib.storage_plugin import builtin_resources
        for record, resource in get_session_resources_of_type(session, builtin_resources.VirtualMachine):
            if not resource.host_id:
                try:
                    host = ManagedHost.objects.get(address = resource.address)
                    log.info("Associated existing host with VirtualMachine resource: %s" % resource.address)
                    record.update_attribute('host_id', host.pk)
                except ManagedHost.DoesNotExist:
                    log.info("Creating host for new VirtualMachine resource: %s" % resource.address)
                    host, command = ManagedHost.create_from_string(resource.address)
                    record.update_attribute('host_id', host.pk)

                # NB any instances of this resource within the plugin session
                # that reported it won't see the change to host_id attribute, but that's
                # fine, they have no right to know.

    @transaction.commit_on_success
    def _persist_lun_updates(self, scannable_id):
        from chroma_core.lib.storage_plugin.query import ResourceQuery
        from chroma_core.lib.storage_plugin import builtin_resources
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager

        scannable_resource = ResourceQuery().get_resource(scannable_id)

        log.debug("%s %s %s" % (scannable_resource, storage_plugin_manager.get_plugin_resource_class('linux', 'PluginAgentResources')[0], isinstance(scannable_resource, storage_plugin_manager.get_plugin_resource_class('linux', 'PluginAgentResources')[0])))
        if not isinstance(scannable_resource, storage_plugin_manager.get_plugin_resource_class('linux', 'PluginAgentResources')[0]):
            return
        else:
            log.debug("_persist_lun_updates for scope record %s" % scannable_id)
            host = ManagedHost.objects.get(pk = scannable_resource.host_id)

        def lun_get_or_create(resource_id):
            try:
                return Lun.objects.get(storage_resource = resource_id)
            except Lun.DoesNotExist:
                # Determine whether a device is shareable by whether it has a SCSI
                # ancestor (e.g. an LV on a scsi device is shareable, an LV on an IDE
                # device is not)
                r = ResourceQuery().get_resource(resource_id)
                lun = Lun.objects.create(
                        size = r.size,
                        storage_resource_id = r._handle)
                log.info("Created Lun %s for LogicalDrive %s" % (lun.pk, resource_id))
                return lun

        # Get all DeviceNodes within this scope
        node_klass_ids = [storage_plugin_manager.get_resource_class_id(klass)
                for klass in all_subclasses(builtin_resources.DeviceNode)]
        node_resources = ResourceQuery().get_class_resources(node_klass_ids, storage_id_scope = scannable_id)

        # DeviceNodes elegible for use as a LunNode (leaves)
        usable_node_resources = [nr for nr in node_resources if not ResourceQuery().record_has_children(nr.id)]

        # DeviceNodes which are usable but don't have LunNode
        assigned_resource_ids = [ln['storage_resource_id'] for ln in LunNode.objects.filter(storage_resource__in = [n.id for n in node_resources]).values("id", "storage_resource_id")]
        unassigned_node_resources = [nr for nr in usable_node_resources if nr.id not in assigned_resource_ids]

        # LunNodes whose storage resource is within this scope
        scope_lun_nodes = LunNode.objects.filter(storage_resource__storage_id_scope = scannable_id)

        log.debug("%s %s %s %s" % (tuple([len(l) for l in [node_resources, usable_node_resources, unassigned_node_resources, scope_lun_nodes]])))

        def affinity_weights(lun):
            lun_nodes = LunNode.objects.filter(lun = lun)
            if lun_nodes.count() == 0:
                log.info("affinity_weights: Lun %d has no LunNodes" % lun.id)
                return False

            if ManagedTarget.objects.filter(lun = lun).count() > 0:
                log.info("affinity_weights: Lun %d in use" % lun.id)
                return False

            weights = {}
            for lun_node in lun_nodes:
                if not lun_node.storage_resource:
                    log.info("affinity_weights: no storage_resource for LunNode %s" % lun_node.id)
                    return False

                weight_resource_ids = ResourceQuery().record_find_ancestors(lun_node.storage_resource, builtin_resources.PathWeight)
                if len(weight_resource_ids) == 0:
                    log.info("affinity_weights: no PathWeights for LunNode %s" % lun_node.id)
                    return False

                from chroma_core.models import StorageResourceRecord
                attr_model_class = StorageResourceRecord.objects.get(id = weight_resource_ids[0]).resource_class.get_class().attr_model_class('weight')

                import json
                ancestor_weights = [json.loads(w['value']) for w in attr_model_class.objects.filter(
                    resource__in = weight_resource_ids, key = 'weight').values('value')]
                weight = reduce(lambda x, y: x + y, ancestor_weights)
                weights[lun_node] = weight

            log.info("affinity_weights: %s" % weights)

            sorted_lun_nodes = [lun_node for lun_node, weight in sorted(weights.items(), lambda x, y: cmp(x[1], y[1]))]
            sorted_lun_nodes.reverse()
            primary = sorted_lun_nodes[0]
            primary.primary = True
            primary.use = True
            primary.save()
            if len(sorted_lun_nodes) > 1:
                secondary = sorted_lun_nodes[1]
                secondary.use = True
                secondary.primary = False
                secondary.save()
            for lun_node in sorted_lun_nodes[2:]:
                lun_node.use = False
                lun_node.primary = False
                lun_node.save()

            return True

        def affinity_balance(lun):
            lun_nodes = LunNode.objects.filter(lun = lun)
            host_to_lun_nodes = defaultdict(list)
            for ln in lun_nodes:
                host_to_lun_nodes[ln.host].append(ln)

            host_to_primary_count = dict([(h, LunNode.objects.filter(host = h, primary = True).count()) for h in host_to_lun_nodes.keys()])

            fewest_primaries = [host for host, count in sorted(host_to_primary_count.items(), lambda x, y: cmp(x[1], y[1]))][0]
            primary_lun_node = host_to_lun_nodes[fewest_primaries][0]
            primary_lun_node.primary = True
            primary_lun_node.use = True
            primary_lun_node.save()
            log.info("affinity_balance: picked %s for %s primary" % (primary_lun_node.host, lun))
            log.info("htpc: %s" % host_to_primary_count)

            # Remove the primary host from consideration for the secondary mount
            del host_to_lun_nodes[primary_lun_node.host]

            if len(host_to_lun_nodes) > 0:
                host_to_lun_node_count = dict([(h, LunNode.objects.filter(host = h, use = True).count()) for h in host_to_lun_nodes.keys()])
                log.info("htlnc: %s" % host_to_lun_node_count)
                fewest_lun_nodes = [host for host, count in sorted(host_to_lun_node_count.items(), lambda x, y: cmp(x[1], y[1]))][0]
                secondary_lun_node = host_to_lun_nodes[fewest_lun_nodes][0]
                secondary_lun_node.primary = False
                secondary_lun_node.use = True
                secondary_lun_node.save()
                log.info("affinity_balance: picked %s for %s secondary" % (secondary_lun_node.host, lun))
            else:
                secondary_lun_node = None

            for lun_node in lun_nodes:
                if not lun_node in (primary_lun_node, secondary_lun_node):
                    lun_node.use = False
                    lun_node.primary = False
                    lun_node.save()

        # For all unattached DeviceNode resources, find or create LunNodes
        for node_record in unassigned_node_resources:
            logicaldrive_id = ResourceQuery().record_find_ancestor(node_record.pk, builtin_resources.LogicalDrive)
            if logicaldrive_id == None:
                # This is not an error: a plugin may report a device node from
                # an agent plugin before reporting the LogicalDrive from the controller.
                log.info("DeviceNode %s has no LogicalDrive ancestor" % node_record.pk)
                continue
            else:
                log.info("Setting up DeviceNode %s" % node_record.pk)
                node_resource = node_record.to_resource()

                lun = lun_get_or_create(logicaldrive_id)
                try:
                    lun_node = LunNode.objects.get(
                            host = host,
                            path = node_resource.path)
                except LunNode.DoesNotExist:
                    lun_node = LunNode.objects.create(
                        lun = lun,
                        host = host,
                        path = node_resource.path,
                        storage_resource_id = node_record.pk,
                        primary = False,
                        use = False)
                    log.info("Created LunNode %s for resource %s" % (lun_node.id, node_record.pk))
                    got_weights = affinity_weights(lun_node.lun)
                    if not got_weights:
                        affinity_balance(lun_node.lun)

        # For all LunNodes, if its storage resource was in this scope, and it
        # was not included in the set of usable DeviceNode resources, remove
        # the LunNode
        for lun_node in scope_lun_nodes:
            log.debug("lun node %s (%s) usable %s" % (lun_node.id, lun_node.storage_resource_id, lun_node.storage_resource_id in [nr.id for nr in usable_node_resources]))
            if not lun_node.storage_resource_id in [nr.id for nr in usable_node_resources]:
                self._try_removing_lun_node(lun_node)

        # TODO: Lun Stealing: there may be an existing Lun/LunNode setup for some ScsiDeviceNodes and ScsiVolumes
        # detected by Chroma, and a storage plugin adds in extra links to the device nodes that follow back
        # to a LogicalDrive provided by the plugin.  In this case there are two LogicalDrive ancestors of the
        # device nodes and we would like to have the Lun refer to the plugin-provided one rather than
        # the auto-generated one (to get the right name etc).
        # LogicalDrives within this scope
        #logical_drive_klass_ids = [storage_plugin_manager.get_resource_class_id(klass)
        #        for klass in all_subclasses(builtin_resources.LogicalDrive)]
        #logical_drive_resources = ResourceQuery().get_class_resources(logical_drive_klass_ids, storage_id_scope = scannable_id)

    def _try_removing_lun(self, lun):
        targets = ManagedTarget.objects.filter(lun = lun)
        nodes = LunNode.objects.filter(lun = lun)
        if targets.count() == 0 and nodes.count() == 0:
            log.warn("Removing Lun %s" % lun.id)
            lun.storage_resource = None
            lun.save()
            Lun.delete(lun.id)
            return True
        elif targets.count():
            log.warn("Leaving Lun %s, used by Target %s" % (lun.id, targets[0]))
        elif nodes.count():
            log.warn("Leaving Lun %s, used by %s nodes" % (lun.id, nodes.count()))

        return False

    def _try_removing_lun_node(self, lun_node):
        targets = ManagedTarget.objects.filter(managedtargetmount__block_device = lun_node)
        if targets.count() == 0:
            log.warn("Removing LunNode %s" % lun_node.id)
            lun_node.storage_resource = None
            lun_node.save()
            LunNode.delete(lun_node.id)
            self._try_removing_lun(lun_node.lun)
            return True
        else:
            log.warn("Leaving LunNode %s, used by Target %s" % (lun_node.id, targets[0]))

        return False

    def session_update_resource(self, scannable_id, local_resource_id, attrs):
        #with self._instance_lock:
        #    session = self._sessions[scannable_id]
        #    record_pk = session.local_id_to_global_id[local_resource_id]
        #    # TODO: implement
        pass

    def session_resource_add_parent(self, scannable_id, local_resource_id, local_parent_id):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            record_pk = session.local_id_to_global_id[local_resource_id]
            parent_pk = session.local_id_to_global_id[local_parent_id]
            self._edges.add_parent(record_pk, parent_pk)
            self._resource_modify_parent(record_pk, parent_pk, False)

    def session_resource_remove_parent(self, scannable_id, local_resource_id, local_parent_id):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            record_pk = session.local_id_to_global_id[local_resource_id]
            parent_pk = session.local_id_to_global_id[local_parent_id]
            self._edges.remove_parent(record_pk, parent_pk)
            self._resource_modify_parent(record_pk, parent_pk, True)
            # TODO: potentially orphaning resources, find and cull them

    def session_update_stats(self, scannable_id, local_resource_id, update_data):
        """Get global ID for a resource, look up the StoreageResourceStatistic for
           each stat in the update, and invoke its .metrics.update with the data"""
       # FIXME: definitely could be doing finer grained locking here as although
       # we need the coarse one for protecting local_id_to_global_id etc, the later
       # part of actually updating stats just needs to be locked on a per-statistic basis
        with self._instance_lock:
                session = self._sessions[scannable_id]
                record_pk = session.local_id_to_global_id[local_resource_id]
                self._persist_update_stats(record_pk, update_data)

    @transaction.autocommit
    def _persist_update_stats(self, record_pk, update_data):
        from chroma_core.models import StorageResourceRecord, StorageResourceStatistic
        record = StorageResourceRecord.objects.get(pk = record_pk)
        for stat_name, stat_data in update_data.items():
            stat_properties = record.get_statistic_properties(stat_name)
            try:
                stat_record = StorageResourceStatistic.objects.get(
                        storage_resource = record, name = stat_name)
                if stat_record.sample_period != stat_properties.sample_period:
                    log.warning("Plugin stat period for '%s' changed, expunging old statistics", stat_name)
                    stat_record.delete()
                    raise StorageResourceStatistic.DoesNotExist

            except StorageResourceStatistic.DoesNotExist:
                stat_record = StorageResourceStatistic.objects.create(
                        storage_resource = record, name = stat_name, sample_period = stat_properties.sample_period)
            from r3d.exceptions import BadUpdateString
            try:
                stat_record.update(stat_name, stat_properties, stat_data)
            except BadUpdateString:
                # FIXME: Initial insert usually fails because r3d isn't getting
                # its start time from the first insert time
                pass

    @transaction.autocommit
    def _resource_modify_parent(self, record_pk, parent_pk, remove):
        from chroma_core.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(pk = record_pk)
        if remove:
            record.parents.remove(parent_pk)
        else:
            record.parents.add(parent_pk)

    @transaction.autocommit
    def _resource_persist_update_attributes(self, record_pk, attrs):
        from chroma_core.models import StorageResourceRecord
        record = StorageResourceRecord.objects.get(record_pk)
        record.update_attributes(attrs)

    def session_add_resources(self, scannable_id, resources):
        """NB this is plural because new resources may be interdependent
        and if so they must be added in a blob so that we can hook up the
        parent relationships"""
        with self._instance_lock:
            self._persist_new_resources(self._sessions[scannable_id], resources)

    def session_remove_resources(self, scannable_id, resources):
        with self._instance_lock:
            # TODO: remove these resources (unless some other resources
            # are still referring to them)
            #self._edges.remove_node(
            pass

    def session_notify_alert(self, scannable_id, resource_local_id, active, alert_class, attribute):
        with self._instance_lock:
            session = self._sessions[scannable_id]
            record_pk = session.local_id_to_global_id[resource_local_id]
            if active:
                if not (record_pk, alert_class) in self._active_alerts:
                    alert_state = self._persist_alert(record_pk, active, alert_class, attribute)
                    self._persist_alert_propagate(alert_state)
                    self._active_alerts[(record_pk, alert_class)] = alert_state.pk
            else:
                alert_state = self._persist_alert(record_pk, active, alert_class, attribute)
                if alert_state:
                    self._persist_alert_unpropagate(alert_state)
                if (record_pk, alert_class) in self._active_alerts:
                    del self._active_alerts[(record_pk, alert_class)]

    def _get_descendents(self, record_global_pk):
        def collect_children(resource_id):
            result = set()
            child_record_ids = self._edges.get_children(resource_id)
            result = result | set(child_record_ids)
            for c in child_record_ids:
                result = result | collect_children(c)
            return result

        return list(collect_children(record_global_pk))

    # FIXME: the alert propagation and unpropagation should happen with the AlertState
    # raise/lower in a transaction.
    def _persist_alert_propagate(self, alert_state):
        from chroma_core.models import StorageAlertPropagated
        record_global_pk = alert_state.alert_item_id
        descendents = self._get_descendents(record_global_pk)
        for d in descendents:
            sap, created = StorageAlertPropagated.objects.get_or_create(
                    storage_resource_id = d,
                    alert_state = alert_state)

    def _persist_alert_unpropagate(self, alert_state):
        from chroma_core.models import StorageAlertPropagated
        StorageAlertPropagated.objects.filter(alert_state = alert_state).delete()

    # FIXME: Couple of issues here:
    # * The AlertState subclasses use Downcastable, they need to be in a transaction
    #   for creations.
    # * If we _persist_alert down, then lose power, we will forget all about the alert
    #   before we remove the PropagatedAlerts for it: actually need to do a two step
    #   removal where we check if there's something there, and if there is then we
    #   remove the propagated alerts, and then finally mark inactive the alert itself.
    @transaction.autocommit
    def _persist_alert(self, record_pk, active, alert_class, attribute):
        from chroma_core.models import StorageResourceRecord
        from chroma_core.models import StorageResourceAlert
        record = StorageResourceRecord.objects.get(pk = record_pk)
        alert_state = StorageResourceAlert.notify(record, active, alert_class=alert_class, attribute=attribute)
        return alert_state

    @transaction.autocommit
    def _cull_lost_resources(self, session, reported_resources):
        reported_global_ids = []
        for r in reported_resources:
            if isinstance(r.identifier, ScannableId):
                reported_global_ids.append(session.local_id_to_global_id[r._handle])

        from chroma_core.models import StorageResourceRecord
        from django.db.models import Q
        lost_resources = StorageResourceRecord.objects.filter(
                ~Q(pk__in = reported_global_ids),
                storage_id_scope = session.scannable_id)
        for r in lost_resources:
            self._cull_resource(r)

    def _cull_resource(self, resource_record):
        log.info("Culling resource '%s'" % resource_record.pk)
        from chroma_core.models import StorageResourceRecord, StorageResourceAttributeReference

        # Find resources which have a parent link to this resource
        for dependent in StorageResourceRecord.objects.filter(
                parents = resource_record):
            dependent.parents.remove(resource_record)

        # Find resources scoped to this resource
        for dependent in StorageResourceRecord.objects.filter(storage_id_scope = resource_record):
            self._cull_resource(dependent)

        # Find ResourceReference attributes on other objects
        # that refer to this one
        for attr in StorageResourceAttributeReference.objects.filter(value = resource_record):
            self._cull_resource(attr.resource)

        lun_nodes = LunNode.objects.filter(storage_resource = resource_record.pk)
        log.debug("%s lun_nodes depend on %s" % (lun_nodes.count(), resource_record.pk))
        for lun_node in lun_nodes:
            removed = self._try_removing_lun_node(lun_node)
            if not removed:
                log.warning("Could not remove LunNode %s, disconnecting from resource %s" % (lun_node.id, resource_record.id))
                lun_node.storage_resource = None
                lun_node.save()

        luns = Lun.objects.filter(storage_resource = resource_record.pk)
        log.debug("%s luns depend on %s" % (luns.count(), resource_record.pk))
        for lun in luns:
            removed = self._try_removing_lun(lun)
            if not removed:
                log.warning("Could not remove Lun %s, disconnecting from resource %s" % (lun.id, resource_record.id))
                lun.storage_resource = None
                lun.save()

        self._subscriber_index.remove_resource(resource_record.pk)
        resource_record.delete()

    def global_remove_resource(self, resource_id):
        with self._instance_lock:
            log.debug("global_remove_resource: %s" % resource_id)
            # Ensure that no open sessions are holding a reference to this ID
            from chroma_core.models import StorageResourceRecord
            try:
                record = StorageResourceRecord.objects.get(pk = resource_id)
            except StorageResourceRecord.DoesNotExist:
                log.error("ResourceManager received invalid request to remove non-existent resource %s" % resource_id)
                return

            resource = record.to_resource()
            from chroma_core.lib.storage_plugin.resource import ScannableResource
            if isinstance(resource, ScannableResource):
                scoped_resources = StorageResourceRecord.objects.filter(
                    storage_id_scope = resource_id)
                for r in scoped_resources:
                    self._cull_resource(r)

            self._cull_resource(record)

            # TODO: deal with GlobalId resources that get left behind, like SCSI IDs,
            # LVM VGs and LVs.  Could look for islands of GlobalId resources with no
            # relationships to ScannableResources, but that could falsely remove some
            # things still existing: e.g. what if a host was just only reporting LVM
            # things?  they wouldn't have any parents.  Probably the more robust way to
            # do this is to track which scannables have had sessions which reported
            # a given GlobalId resource, and treat that like a reference count

    def _persist_new_resource(self, session, resource):
        from chroma_core.models import StorageResourceRecord

        if resource._handle_global:
            # Bit of a weird one: this covers the case where a plugin sessoin
            # was given a root resource that had some ResourceReference attributes
            # that pointed to resources from a different plugin
            return

        if resource._handle in session.local_id_to_global_id:
            return

        if isinstance(resource.identifier, ScannableId):
            scope_id = session.scannable_id
        elif isinstance(resource.identifier, GlobalId):
            scope_id = None
        else:
            raise NotImplementedError

        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        resource_class, resource_class_id = storage_plugin_manager.get_plugin_resource_class(
                resource.__class__.__module__,
                resource.__class__.__name__)

        # Find any ResourceReference attributes and persist them first so that
        # we know their global IDs for serializing this one
        for key, value in resource._storage_dict.items():
            # Special case for ResourceReference attributes, because the resource
            # object passed from the plugin won't have a global ID for the referenced
            # resource -- we have to do the lookup inside ResourceManager
            attribute_obj = resource_class.get_attribute_properties(key)
            from chroma_core.lib.storage_plugin import attributes
            if isinstance(attribute_obj, attributes.ResourceReference):
                if value:
                    referenced_resource = value
                    if not referenced_resource._handle_global:
                        if not referenced_resource._handle in session.local_id_to_global_id:
                            self._persist_new_resource(session, referenced_resource)
                            assert referenced_resource._handle in session.local_id_to_global_id

        id_tuple = resource.id_tuple()
        cleaned_id_items = []
        for t in id_tuple:
            from chroma_core.lib.storage_plugin.resource import StorageResource
            if isinstance(t, StorageResource):
                cleaned_id_items.append(session.local_id_to_global_id[t._handle])
            else:
                cleaned_id_items.append(t)
        import json
        id_str = json.dumps(tuple(cleaned_id_items))

        record, created = StorageResourceRecord.objects.get_or_create(
                resource_class_id = resource_class_id,
                storage_id_str = id_str,
                storage_id_scope_id = scope_id)
        if created:
            from chroma_core.models import StorageResourceLearnEvent
            import logging
            # Record a user-visible event
            StorageResourceLearnEvent(severity = logging.INFO, storage_resource = record).save()

            # IMPORTANT: THIS TOTALLY RELIES ON SERIALIZATION OF ALL CREATION OPERATIONS
            # IN A SINGLE PROCESS INSTANCE OF THIS CLASS

            # This is a new resource which provides a field, see if any existing
            # resources would like to subscribe to it
            subscribers = self._subscriber_index.what_subscribes(resource)
            # Make myself a parent of anything that subscribes to me
            for s in subscribers:
                log.info("Linked up me %s as parent of %s" % (record.pk, s))
                self._edges.add_parent(s, record.pk)
                s_record = StorageResourceRecord.objects.get(pk = s)
                s_record.parents.add(record.pk)

            # This is a new resource which subscribes to a field, see if any existing
            # resource can provide it
            providers = self._subscriber_index.what_provides(resource)
            # Make my providers my parents
            for p in providers:
                log.info("Linked up %s as parent of me, %s" % (p, record.pk))
                self._edges.add_parent(record.pk, p)
                record.parents.add(p)

            # Add the new record to the index so that future records and resolve their
            # provide/subscribe relationships with respect to it
            self._subscriber_index.add_resource(record.pk, resource)

        session.local_id_to_global_id[resource._handle] = record.pk
        self._resource_persist_attributes(session, resource, record)

        if created:
            log.debug("persist_new_resource[%s] %s %s %s" % (session.scannable_id, created, record.pk, resource._handle))
        return record

    # Use commit on success to avoid situations where a resource record
    # lands in the DB without its attribute records.
    # FIXME: there are cases where _persist_new_resource gets called outside
    # of _persist_new_resources, make sure it's wrapped in a transaction too
    @transaction.commit_on_success
    def _persist_new_resources(self, session, resources):
        for r in resources:
            self._persist_new_resource(session, r)

        # Do a separate pass for parents so that we will have already
        # built the full local-to-global map
        for r in resources:
            resource_global_id = session.local_id_to_global_id[r._handle]

            # Update self._edges
            for p in r._parents:
                parent_global_id = session.local_id_to_global_id[p._handle]
                self._edges.add_parent(resource_global_id, parent_global_id)

            # Update the database
            # FIXME: shouldn't need to SELECT the record to set up its relationships
            from chroma_core.models import StorageResourceRecord
            record = StorageResourceRecord.objects.get(pk = resource_global_id)
            self._resource_persist_parents(r, session, record)

    @transaction.autocommit
    def _resource_persist_attributes(self, session, resource, record):
        from chroma_core.lib.storage_plugin.manager import storage_plugin_manager
        resource_class = storage_plugin_manager.get_resource_class_by_id(record.resource_class_id)

        attrs = {}
        # Special case for ResourceReference attributes, because the resource
        # object passed from the plugin won't have a global ID for the referenced
        # resource -- we have to do the lookup inside ResourceManager
        for key, value in resource._storage_dict.items():
            attribute_obj = resource_class.get_attribute_properties(key)
            from chroma_core.lib.storage_plugin import attributes
            if isinstance(attribute_obj, attributes.ResourceReference):
                if value and not value._handle_global:
                    attrs[key] = session.local_id_to_global_id[value._handle]
                elif value and value._handle_global:
                    attrs[key] = value._handle
                else:
                    attrs[key] = value
            else:
                attrs[key] = value

        record.update_attributes(attrs)

    @transaction.autocommit
    def _resource_persist_parents(self, resource, session, record):
        new_parent_pks = [session.local_id_to_global_id[p._handle] for p in resource._parents]
        existing_parents = record.parents.all()

        # TODO: work out how to cull relationships
        # (can't just do it here because persist_parents is called with a LOCAL resource
        # which may not have all the parents)
        #for ep in existing_parents:
        #    if not ep.pk in new_parent_pks:
        #        record.parents.remove(ep)

        existing_parent_handles = [ep.pk for ep in existing_parents]
        for pk in new_parent_pks:
            if not pk in existing_parent_handles:
                record.parents.add(pk)

resource_manager = ResourceManager()
