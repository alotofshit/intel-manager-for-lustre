# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

# django-piston handlers imports.
from django.conf.urls.defaults import *
from piston.resource import Resource

# Hydra server imports
from monitorapi import (ListFileSystems,
                        GetFileSystem,
                        GetVolumes,
                        GetClients,
                        GetServers,
                        GetEventsByFilter,
                        GetLatestEvents,
                        GetAlerts,
                        GetJobs,
                        GetLogs,
                        GetFSVolumeDetails)

from configureapi import (FormatFileSystem,
                          StopFileSystem,
                          StartFileSystem,
                          AddHost,  
                          TestHost,
                          RemoveHost,
                          GetLuns,
                          CreateFilesystem,
                          CreateMGS,
                          CreateOSS,
                          CreateMDS,
                          SetLNetStatus)

#Once R3D starts getting correct data  replace fakestatsmetricapi with statmetricapi
from fakestatsmetricapi import(GetFSTargetStats_fake,
                           GetFSServerStats_fake,
                           GetServerStats_fake,
                           GetTargetStats_fake,
                           GetFSClientsStats_fake,
                           GetFSOSTHeatMap)  

from statsmetricapi import(GetFSTargetStats,
                           GetFSServerStats,
                           GetFSMGSStats,
                           GetServerStats,
                           GetTargetStats,
                           GetFSClientsStats)

from audit import HydraAudit

# Cross Site Referance related class 
class CsrfExemptResource(Resource):
    """A Custom Resource that is csrf exempt"""
    def __init__(self, handler, authentication=None):
        super(CsrfExemptResource, self).__init__(handler, authentication)
        self.csrf_exempt = getattr(self.handler, 'csrf_exempt', True)

# django-piston resource mapping.

#Monitor namspace APIs
list_filesystems = CsrfExemptResource(ListFileSystems)
get_filesystem = CsrfExemptResource(GetFileSystem)
list_servers = CsrfExemptResource(GetServers)
get_clients = CsrfExemptResource(GetClients)
get_volumes = CsrfExemptResource(GetVolumes)
get_fs_vol_details = CsrfExemptResource(GetFSVolumeDetails)
get_luns = CsrfExemptResource(GetLuns)

#Configure namespace APIs
format_filesystem = CsrfExemptResource(FormatFileSystem)
stop_filesystem = CsrfExemptResource(StopFileSystem)
start_filesystem = CsrfExemptResource(StartFileSystem)
create_filesystem = CsrfExemptResource(CreateFilesystem)
create_mgs = CsrfExemptResource(CreateMGS)
create_oss = CsrfExemptResource(CreateOSS)
create_mds = CsrfExemptResource(CreateMDS)
add_host = CsrfExemptResource(AddHost)
remove_host = CsrfExemptResource(RemoveHost)
test_host = CsrfExemptResource(TestHost)
set_lnet_status = CsrfExemptResource(SetLNetStatus)

#Audit namespace APIs
list_audit = CsrfExemptResource(HydraAudit)
clear_audit = CsrfExemptResource(HydraAudit)

# Real stats metrics APIs
get_fs_stats_for_targets_fake = CsrfExemptResource(GetFSTargetStats_fake)
get_fs_stats_for_server_fake = CsrfExemptResource(GetFSServerStats_fake)
get_stats_for_server_fake = CsrfExemptResource(GetServerStats_fake)
get_stats_for_targets_fake = CsrfExemptResource(GetTargetStats_fake)
get_fs_stats_for_client_fake = CsrfExemptResource(GetFSClientsStats_fake)
get_fs_ost_heatmap = CsrfExemptResource(GetFSOSTHeatMap)


get_fs_stats_for_targets = CsrfExemptResource(GetFSTargetStats)
get_fs_stats_for_server = CsrfExemptResource(GetFSServerStats)
get_fs_stats_for_mgs = CsrfExemptResource(GetFSMGSStats)
get_stats_for_server = CsrfExemptResource(GetServerStats)
get_fs_stats_for_client = CsrfExemptResource(GetFSClientsStats)
get_stats_for_targets = CsrfExemptResource(GetTargetStats)

#Liveinfo related APIs
get_events_by_filter = CsrfExemptResource(GetEventsByFilter)
get_latest_events = CsrfExemptResource(GetLatestEvents)
get_alerts = CsrfExemptResource(GetAlerts)
get_jobs = CsrfExemptResource(GetJobs)
get_logs = CsrfExemptResource(GetLogs)

# hydra api urls definitions.
urlpatterns = patterns('',
    (r'^listfilesystems/$', list_filesystems),
    (r'^getfilesystem/$',get_filesystem),
    (r'^getvolumes/$',get_volumes),
    (r'^getvolumesdetails/$',get_fs_vol_details),
    (r'^listservers/$',list_servers),
    (r'^getclients/$',get_clients),
    (r'^get_luns/$',get_luns),
    
    (r'^listaudit/$',list_audit),
    (r'^clearaudit/$',clear_audit),
    
    (r'^formatfilesystem/$',format_filesystem), 
    (r'^stopfilesystem/$',stop_filesystem), 
    (r'^startfilesystem/$',start_filesystem),
    (r'^createfs/$',create_filesystem),
    (r'^createmgt/$',create_mgs),
    (r'^createost/$',create_oss),
    (r'^createmdt/$',create_mds),
    (r'^testhost/$',test_host),
    (r'^addhost/$',add_host),
    (r'^removehost/$',remove_host),
    (r'^setlnetstate/$',set_lnet_status),

    (r'^get_fs_stats_for_targets/$',get_fs_stats_for_targets_fake),
    (r'^get_fs_stats_for_server/$',get_fs_stats_for_server_fake),
    (r'^get_stats_for_server/$',get_stats_for_server_fake),
    (r'^get_stats_for_targets/$',get_stats_for_targets_fake),
    (r'^get_fs_stats_for_client/$',get_fs_stats_for_client_fake),
    (r'^get_fs_ost_heatmap/$',get_fs_ost_heatmap),

    (r'^getfsstatsfortargets/$',get_fs_stats_for_targets),
    (r'^getfsstatsforserver/$',get_fs_stats_for_server),
    (r'^getfsstatsformgs/$',get_fs_stats_for_mgs ),
    (r'^getstatsforserver/$',get_stats_for_server ),
    (r'^getstatsfortargets/$',get_stats_for_targets),
    (r'^getfsstatsforclient/$',get_fs_stats_for_client),
 
    (r'^geteventsbyfilter/$',get_events_by_filter),
    (r'^getlatestevents/$',get_latest_events),
    (r'^getalerts/$',get_alerts),
    (r'^getjobs/$',get_jobs),
    (r'^getlogs/$',get_logs),
   )
