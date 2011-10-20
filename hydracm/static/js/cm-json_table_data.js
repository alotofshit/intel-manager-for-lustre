/******************************************************************/
//Function name - LoadFSList_FSList()
//Param - none
//Return - none
//Used in - File System list (lustre_fs_configuration.html)
/******************************************************************/

function LoadFSList_FSList()
{
  $.get("/api/listfilesystems/").success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      var response = data.response;
      var fsName;
      var i=1;
      var action = "<a href='#'>Start<img src='/static/images/start.png' height=12 width=12 title='Start'/></a> | <a href='#'>Configuration<img src='/static/images/configuration.png' height=15 width=15 title='Configuration Param'/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
      $.each(response, function(resKey, resValue)
      {
		  fsName = "<a href='#' onclick=LoadEditFSScreen('" + resValue.fsname + "')>" + resValue.fsname + "</a>";
//        fsName = "<a href='/hydracm/editfs?fsname=" + resValue.fsname + "'>" +resValue.fsname + "</a>";
        i++;
        $('#example').dataTable().fnAddData ([
          fsName,
          resValue.mgsname,
          resValue.mdsname,
          resValue.noofoss,
          resValue.noofost,
          resValue.kbytesused,
          resValue.kbytesfree,
          action
        ]); 
      });
    }
  })
  .error(function(event)
  {
  })
  .complete(function(event) 
  {
  });
}
/******************************************************************/
//Function name - LoadMGT_EditFS()
//Param - none
//Return - none
//Used in - Edit FS (edit_fs.html)
/******************************************************************/

function LoadMGT_EditFS(fsname)
{
  var action="--";
  $.post("/api/getvolumesdetails/",{filesystem:fsname}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      var response = data.response;
      $.each(response, function(resKey, resValue)
      {
        if(resValue.targetkind == "MGS")
        {
          if(resValue.targetstatus == "STARTED")
          {
            action = "<a href='#'>Stop<img src='/static/images/stop.png' title='Stop' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
          }
          else
          {
            action = "<a href='#'>Start<img src='/static/images/start.png' title='Start' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
          }
          $('#example').dataTable().fnAddData ([
            resValue.targetdevice,
            resValue.targetname,
            resValue.hostname,
            resValue.failover,
            action
          ]);
        }
      });
    }
  })
  .error(function(event)
  { 
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - LoadMDT_EditFS()
//Param - none
//Return - none
//Used in - Edit FS (edit_fs.html)
/******************************************************************/

function LoadMDT_EditFS(fsname)
{
  var action="--";
  $.post("/api/getvolumesdetails/",{filesystem:fsname}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      var response = data.response;
      $.each(response, function(resKey, resValue)
      {
        if(resValue.targetkind == "MDT")
        {
          if(resValue.targetstatus == "STARTED")
          {
            action = "<a href='#'>Stop<img src='/static/images/stop.png' title='Stop' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
          }
          else
          {
            action= "<a href='#'>Start<img src='/static/images/start.png'title='Start' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
          }
          $('#mdt').dataTable().fnAddData ([
            resValue.targetdevice,
            resValue.targetname,
            resValue.hostname,
            resValue.failover,
            action
          ]);
        }
      });
    }
  })
  .error(function(event)
  {
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - LoadOST_EditFS()
//Param - none
//Return - none
//Used in - Edit FS (edit_fs.html)
/******************************************************************/

function LoadOST_EditFS(fsname)
{
  var action = "--";
  $.post("/api/getvolumesdetails/",{filesystem:fsname}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      var response = data.response;
      $.each(response, function(resKey, resValue)
      {
        if(resValue.targetkind == "OST")
        {
          if(resValue.targetstatus == "STARTED")
          {
            action = "<a href='#'>Stop<img src='/static/images/stop.png' title='Stop' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>"; 
          }
          else
          {
            action = "<a href='#'>Start<img src='/static/images/start.png'title='Start' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
          }
          $('#ost').dataTable().fnAddData ([
            resValue.targetdevice,
            resValue.targetname,
            resValue.hostname,
            resValue.failover,
            action
          ]);
        }
      });
    }
  })
  .error(function(event)
  {
 // Display of appropriate error message
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - LoadExistingMGT_EditFS()
//Param - none
//Return - none
//Used in - Edit FS (edit_fs.html)
/******************************************************************/

function LoadExistingMGT_EditFS()
{
  $('#popup-existing-mgt').dataTable().fnClearTable();
  var btnRadio = "<input type='radio' name='existing_mgt' />";
  $.post("/api/getvolumesdetails/",{filesystem:""}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      var response = data.response;
      var updatedTargetMnt="";
      $.each(response, function(resKey, resValue)
      {
        if(resValue.targetkind == "MGS")
        {
          if(updatedTargetMnt != resValue.targetmount)
          {
            $('#popup-existing-mgt').dataTable().fnAddData ([
              btnRadio,
              resValue.targetmount,
              resValue.targetname,
              resValue.hostname,
              resValue.failover
            ]);
          }
          updatedTargetMnt = resValue.targetmount;
        }
      });
    }
  })
  .error(function(event)
  {
  // Display of appropriate error message
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - CreateNewMGT_EditFS()
//Param - none
//Return - none
//Used in - Edit FS (edit_fs.html)
/******************************************************************/

function CreateNewMGT_EditFS()
{
  $('#popup-new-mgt').dataTable().fnClearTable();
  LoadUsableVolumeList($('#popup-new-mgt'), function(vol_info) {return "<input type='radio' name='mgt'/>"});
}

/******************************************************************/
//Function name - CreateNewMDT_EditFS()
//Param - none
//Return - none
//Used in - Edit FS (edit_fs.html)
/******************************************************************/

function CreateNewMDT_EditFS()
{
  $('#popup-new-mdt').dataTable().fnClearTable();
  LoadUsableVolumeList($('#popup-new-mdt'), function(vol_info) {return "<input type='radio' name='mdt'/>"});
}

/******************************************************************/
//Function name - CreateOST_EditFS()
//Param - none
//Return - none
//Used in - Edit FS (edit_fs.html)
/******************************************************************/

function CreateOST_EditFS()
{
  $('#popup-new-ost').dataTable().fnClearTable();
  LoadUsableVolumeList($('#popup-new-ost'), function(vol_info) {return "<input type='checkbox' name='" + vol_info.id + "'/>"});
}

/******************************************************************/
//Function name - LoadUsableVolumeList()
//Param - container for data table, select widget
//Return - none
//Used in - none
/******************************************************************/

function LoadUsableVolumeList(datatable_container, select_widget_fn)
{
  $.post("/api/get_luns/", {'category': 'usable'}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      $.each(data.response, function(resKey, volume_info)
      {
        var primaryHostname = "---"
        var failoverHostname = "---"
        $.each(volume_info.available_hosts, function(host_id, host_info) 
        {
          if (host_info.primary) 
          {
            primaryHostname = host_info.label
          }
          else if (host_info.use) 
          {
            failoverHostname = host_info.label
          }
        });
        datatable_container.dataTable().fnAddData ([
          select_widget_fn(volume_info),
          volume_info.name,
          volume_info.size,
          volume_info.kind,
          volume_info.status,
          primaryHostname,
          failoverHostname,
        ]); 
      });
    }
  })
  .error(function(event)
  {
  // Display of appropriate error message
  })
}

/******************************************************************/
//Function name - LoadUnused_VolumeConf()
//Param - none
//Return - none
//Used in - Volume Configuration (volume_configuration.html)
/******************************************************************/

function LoadUnused_VolumeConf()
{
  $.get("/api/get_luns/", {'category': 'unused'}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      $.each(data.response, function(resKey, resValue)
      {
        var blank_option = "<option value='-1'>---</option>";
        var blank_select = "<select disabled='disabled'>" + blank_option + "</select>"
        var primarySelect;
        var failoverSelect;
        var host_count = 0
        $.each(resValue.available_hosts, function(host_id, host_info) 
        {
          host_count += 1;
        });
        if (host_count == 0) 
        {
          primarySelect = blank_select
          failoverSelect = blank_select
        }
        else if (host_count == 1) 
        {
          $.each(resValue.available_hosts, function(host_id, host_info) 
          {
            primarySelect = "<select disabled='disabled'><option value='" + host_id + "'>" + host_info.label + "</option></select>";
          });
        failoverSelect = blank_select
        } 
        else 
        {
          primarySelect = "<select>";
          failoverSelect = "<select>";
          primarySelect += blank_option
          failoverSelect += blank_option
          $.each(resValue.available_hosts, function(host_id, host_info)
          {
            if (host_info.primary) 
            {
              primarySelect += "<option value='" + host_id + "' selected='selected'>" + host_info.label + "</option>";
              failoverSelect += "<option value='" + host_id + "'>" + host_info.label + "</option>";
            }
            else if (host_info.use) 
            {
              primarySelect += "<option value='" + host_id + "'>" + host_info.label + "</option>";
              failoverSelect += "<option value='" + host_id + "' selected='selected'>" + host_info.label + "</option>";
            } 
            else 
            {
              primarySelect += "<option value='" + host_id + "'>" + host_info.label + "</option>";
              failoverSelect += "<option value='" + host_id + "' selected='selected'>" + host_info.label + "</option>";
            }
          });
          failoverSelect += "</select>";
          primarySelect += "</select>";
        }
        $('#volume_configuration').dataTable().fnAddData ([
          resValue.name,
          primarySelect,
          failoverSelect,
          resValue.size,
          resValue.status
        ]); 
      });
    }
  })
  .error(function(event) 
  {
 // Display of appropriate error message
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - CreateMGT_MGTConf()
//Param - none
//Return - none
//Used in - MGT Configuration (new_mgt.html)
/******************************************************************/

function CreateMGT_MGTConf()
{
  var i=1;
  var checkboxCount = 0;
  $('#mgtConfig_btnNewMGT').attr('disabled', 'disabled');
  $.get("/api/get_luns/", {'category': 'unused'}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      $.each(data.response, function(resKey, resValue)
      {
        var blank_option = "<option value='-1'>---</option>";
        var blank_select = "<select disabled='disabled'>" + blank_option + "</select>"
        var primarySelect;
        var failoverSelect;
        var host_count = 0
        $.each(resValue.available_hosts, function(host_id, host_info) 
        {
          host_count += 1;
        });
        if (host_count == 0) 
        {
          primarySelect = blank_select
          failoverSelect = blank_select
        }
        else if (host_count == 1) 
        {
          $.each(resValue.available_hosts, function(host_id, host_info) 
          {
            primarySelect = "<select disabled='disabled'><option value='" + host_id + "'>" + host_info.label + "</option></select>";
          });
          failoverSelect = blank_select
        } 
        else 
        {
          primarySelect = "<select>";
          failoverSelect = "<select>";
          primarySelect += blank_option
          failoverSelect += blank_option
          $.each(resValue.available_hosts, function(host_id, host_info)
          {
            if (host_info.primary) 
            {
              primarySelect += "<option value='" + host_id + "' selected='selected'>" + host_info.label + "</option>";
              failoverSelect += "<option value='" + host_id + "'>" + host_info.label + "</option>";
            }
            else if (host_info.use) 
            {
              primarySelect += "<option value='" + host_id + "'>" + host_info.label + "</option>";
              failoverSelect += "<option value='" + host_id + "' selected='selected'>" + host_info.label + "</option>";
            }
            else 
            {
              primarySelect += "<option value='" + host_id + "'>" + host_info.label + "</option>";
              failoverSelect += "<option value='" + host_id + "' selected='selected'>" + host_info.label + "</option>";
            }
          });
          failoverSelect += "</select>";
          primarySelect += "</select>";
        }
        $('#popup-new-ost').dataTable().fnAddData ([
          "<input type='checkbox' id='" + i+ "'/>",
          resValue.name,
          primarySelect,
          failoverSelect,
          resValue.size,
          resValue.status
        ]); 
        $('#'+i).live('click', function() {
        if($(this).attr('checked'))
        {
          checkboxCount++;
          $('#mgtConfig_btnNewMGT').removeAttr('disabled');
        }
        else
        {
          checkboxCount--;
        }
        if(checkboxCount==0)
        {
          $('#mgtConfig_btnNewMGT').attr('disabled', 'disabled');
        }
      });
      i++;
    });
  }
  })
  .error(function(event) 
  {
  // Display of appropriate error message
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - LoadMGTConfiguration_MGTConf()
//Param - none
//Return - none
//Used in - MGT Configuration (new_mgt.html)
/******************************************************************/

function LoadMGTConfiguration_MGTConf()
{
  $.post("/api/getvolumesdetails/",{filesystem:""}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      var response = data.response;
      var targetpath="";
      var fsname="";
      var val_targetstatus;
      var val_targetmount;
      var val_hostname;
      var val_failover;
      var updated=0;
      var action ="--";
      if(data.response!="")
      {
        $.each(response, function(resKey, resValue)
        {
          if(resValue.targetkind == "MGS")
          {
            if(targetpath!=resValue.targetmount && targetpath!="")
            {
              //fsname = resValue.fsname;
              if(resValue.targetstatus == "STARTED")
              {
                action = "<a href='#'>Stop<img src='/static/images/stop.png' title='Stop' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
              }
              else
              {
                action = "<a href='#'>Start<img src='/static/images/start.png'title='Start' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
              }
              $('#mgt_configuration').dataTable().fnAddData ([
                fsname,
                resValue.targetdevice,
                resValue.hostname,
                resValue.failover,
                action
              ]);
              fsname="";
              updated=1;
            }
            else
            {
              if (fsname!="")
              {
                fsname = fsname +"," + resValue.fsname;
              }
              else
              {
                fsname = resValue.fsname;
              }
              val_targetstatus=resValue.targetstatus;
              val_targetmount=resValue.targetdevice;
              val_hostname=resValue.hostname;
              val_failover=resValue.failover;
              updated=0;
            }
            targetpath = resValue.targetmount;
          }
        });
        if(updated==0)
        {
          if(val_targetstatus == "STARTED")
          {
            action ="<a href='#'>Stop<img src='/static/images/stop.png' title='Stop' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
          }
          else
          {
            action = "<a href='#'>Start<img src='/static/images/start.png' title='Start' height=15 width=15/></a> | <a href='#'>Remove<img src='/static/images/remove.png' height=15 width=15 title='Remove'/></a>";
          }
          $('#mgt_configuration').dataTable().fnAddData ([
            fsname,
            val_targetmount,
            val_hostname,
            val_failover,
            action
          ]);
        }
      }
    }
  })
  .error(function(event)
  {
  // Display of appropriate error message
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - LoadVolumeConf_VolumeConfig()
//Param - none
//Return - none
//Used in - Volume Configuration (volume_configuration.html)
/******************************************************************/

function LoadVolumeConf_VolumeConfig()
{
  $.post("/api/get_luns/",{"category": "usable"}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      var response = data.response;
      var primaryServer;
      $.each(response, function(resKey, resValue)
      {
        primaryServer = "<select>";
        $.each(resValue.available_hosts, function(resFailoverKey, resFailoverValue)
        {
          if(resFailoverValue.label==undefined)
          {
            primaryServer = primaryServer + "<option value='volvo'>&nbsp;&nbsp;None&nbsp;&nbsp;</option>";
          }
          else
          {
            primaryServer = primaryServer + "<option value='volvo'>" + resFailoverValue.label + "</option>";
          }
          primaryServer = primaryServer + "</select>";
        });
        $('#volume_configuration').dataTable().fnAddData ([
          resValue.name,
          primaryServer,
          "",
          resValue.status,
          resValue.size
        ]); 
      });
    }
  })
  .error(function(event)
  {
  // Display of appropriate error message
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - LoadServerConf_ServerConfig()
//Param - none
//Return - none
//Used in - Server Configuration (server_configuration.html)
/******************************************************************/

function LoadServerConf_ServerConfig()
{
  $.post("/api/listservers/",{"filesystem": ""}).success(function(data, textStatus, jqXHR)
  {
    if(data.success)
    {
      var response = data.response;
      var lnet_status_mesg;
      var lnet_status;
      $.each(response, function(resKey, resValue)
      {
        lnet_status = resValue.lnet_status;
        if(lnet_status == "lnet_up")
        {
          lnet_status_mesg = "<a href='#'>Stop<img src='/static/images/stop.png' title='Stop Lnet' height=15 width=15 onclick='Lnet_Operations(" + resValue.id +",&apos;lnet_down&apos;)'/></a> | <a href='#'>Remove<img src='/static/images/remove.png' title='Remove' height=15 width=15 id='"+ resValue.id +"' onclick='RemoveHost_ServerConfig(" + resValue.id + ")' /></a> | <a href='#'>Unload<img src='/static/images/unload.png' title='Unload Lnet' height=15 width=15onclick='Lnet_Operations(" + resValue.id +",&apos;lnet_unload&apos;)'/></a> | <a href='#'>Configuration<img src='/static/images/configuration.png' title='Configuration' height=15 width=15/></a>";
        }
        else if(resValue.lnet_status == "lnet_down")
        {
          lnet_status_mesg = "<a href='#'>Start<img src='/static/images/start.png' title='Start Lnet' height=15 width=15 onclick='Lnet_Operations(" + resValue.id +",&apos;lnet_up&apos;)'/></a> | <a href='#'>Remove<img src='/static/images/remove.png' title='Remove' height=15 width=15 id='"+ resValue.id +"' onclick='RemoveHost_ServerConfig(" + resValue.id + ")' /></a> | <a href='#'>Unload<img src='/static/images/unload.png' title='Unload Lnet' height=15 width=15onclick='Lnet_Operations(" + resValue.id +",&apos;lnet_unload&apos;)'/></a> | <a href='#'>Configuration<img src='/static/images/configuration.png' title='Configuration' height=15 width=15/></a>"; 
        }
        else if(resValue.lnet_status == "lnet_unloaded")
        {
          lnet_status_mesg = "<a href='#'>Start<img src='/static/images/start.png' title='Start Lnet' height=15 width=15onclick='Lnet_Operations(" + resValue.id +",&apos;lnet_up&apos;)'/></a> | <a href='#'>Remove<img src='/static/images/remove.png' title='Remove' height=15 width=15 id='"+ resValue.id +"' onclick='RemoveHost_ServerConfig(" + resValue.id + ")' /></a> | &nbsp;&nbsp;<a href='#'>Load<img src='/static/images/load.png' title='Load Lnet' height=15 width=15onclick='Lnet_Operations(" + resValue.id +",&apos;lnet_load&apos;)'/></a>&nbsp;&nbsp; | <a href='#'>Configuration<img src='/static/images/configuration.png' title='Configuration' height=15 width=15/></a>";  
        }
        $('#server_configuration').dataTable().fnAddData ([
          resValue.host_address,
          resValue.failnode,
          resValue.status,
          lnet_status,
          lnet_status_mesg
        ]);
      });
    }
  })
  .error(function(event)
  {
  // Display of appropriate error message
  })
  .complete(function(event) 
  {
  });
}

/******************************************************************/
//Function name - LoadFSData_EditFS()
//Param - none
//Return - none
//Used in - Edit FS (edit_fs.html)
/******************************************************************/

function LoadFSData_EditFS()
{
  var fsname = $('#fs').val();
  $('#fsname').attr('value',fsname);
  if(fsname!="none")
  {
    $.post("/api/getfilesystem/",{"filesystem":fsname}).success(function(data, textStatus, jqXHR)
    {
      if(data.success)
      {
        var response = data.response;
        var lnet_status_mesg;
        $.each(response, function(resKey, resValue)
        {
          $('#total_capacity').html(resValue.kbytesused);
          $('#total_free').html(resValue.kbytesfree);
          $('#mdt_file_used').html(resValue.mdtfileused);
          $('#mdt_file_free').html(resValue.mdtfilesfree);
          $('#total_oss').html(resValue.noofoss);
          $('#total_ost').html(resValue.noofost);
        });
      }
    })
    .error(function(event)
    {
    // Display of appropriate error message
    })
    .complete(function(event) 
    {
    });
  }
}