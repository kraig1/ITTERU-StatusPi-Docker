$(document).ready(function() {

    namespace = '/zlt';

    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + namespace);

    var status_colour = function(code){
      if(code == 0)
        return "jumbotron-success";
      if(code == 1)
        return "jumbotron-warning";
      if(code == 2)
        return "jumbotron-error";
      return "";
    }

    var status_icon = function(code){
      if(code == 0)
        return "fa-check";
      if(code == 1)
        return "fa-exclamation-circle blink";
      if(code == 2)
        return "fa-exclamation-triangle blink";

      return "fa-circle-notch fa-pulse";
    }

    var vm_label = function(status){
      if(status == 'poweredOn')
        return "success";
      return "danger";
    }

  socket.on('network_status', function(msg) {
    //console.log(msg);

    // Network section   //
    $('#overview-network div').attr('class', 'jumbotron ' + status_colour(msg.code));
    $('#overview-network div h1 > i').removeClass();
    $('#overview-network div h1 > i').addClass("fa pull-right " + status_icon(msg.code));
    $('#overview-network div p').html(msg.message);

    // Details table
    for(var node in msg.nodes) {

      if($('#network-status-table tr#row-' + node).val() != undefined) {
        $('#network-status-table tr#row-' + node + ' span.label').html(msg.nodes[node].message);
        $('#network-status-table tr#row-' + node + ' span.label').attr('class', 'label label-' + msg.nodes[node].class);
      } else {
        var $tr = $('<tr id="row-' + node +'">').append(
            $('<th class="service">').text(node),
            $('<td class="status">'),
            $('<span class="label label-'+ msg.nodes[node].class + '">').text(msg.nodes[node].message),
        ).appendTo('#network-status-table tbody');
      }
    }

  });

  socket.on('environment_status', function(msg) {
    // console.log(msg);

    $('#overview-environment .detail').removeClass('hidden');

    // Environment section   //
    $('#overview-environment div:first').attr('class', 'jumbotron ' + status_colour(msg.code));
    $('#overview-environment div h1 > i').removeClass();
    $('#overview-environment div h1 > i').addClass("fa pull-right " + status_icon(msg.code));
    $('#overview-environment div p').html(msg.message);


    $('#temp span').html(msg.sensors.temp);
    $('#humidity span').html(msg.sensors.humidity);
    $('#runtime span').html(msg.sensors.runtime);
    $('#battery_capacity span').html(msg.sensors.capacity);
    $('#battery_status span').html(msg.sensors.on_battery);
    $('#load span').html(msg.sensors.load);

  });

  socket.on('vm_status', function(msg) {
    console.log(msg);
    $('#overview-vms div').attr('class', 'jumbotron ' + status_colour(msg.code));
    $('#overview-vms div h1 > i').removeClass();
    $('#overview-vms div h1 > i').addClass("fa pull-right " + status_icon(msg.code));
    $('#overview-vms div p').html(msg.message);

    for(var vm in msg.vms) {

      if($('#vm-status-table tr#row-' + vm).val() != undefined) {
        $('#vm-status-table tr#row-' + vm + ' span').html((msg.vms[vm].power == 'poweredOn' ? "Powered On" : "Powered Off"));
        $('#vm-status-table tr#row-' + vm + ' span').removeClass();
        $('#vm-status-table tr#row-' + vm + ' span').addClass('label label-' + vm_label(msg.vms[vm].power));
      } else {
        var $tr = $('<tr id="row-' + vm +'">').append(
            $('<th class="service">').text(vm),
            $('<td class="status">'),
            $('<span class="label label-'+ vm_label(msg.vms[vm].power) + '">').text(msg.vms[vm].power == 'poweredOn' ? "Powered On" : "Powered Off"),
        ).appendTo('#vm-status-table tbody');
      }
    }

  })

  socket.on('shutdown', function(msg) {
    console.log("got shutdown command");
    $('#shutdown').removeClass('hidden');
    $('#status').addClass('hidden');
    $('.navbar').addClass('hidden');

    timer = msg;
    setInterval(function() {
      timer = timer -1;
      var minutes = Math.floor(timer / 60);
      var seconds = timer - minutes *60;
      var pad = function(num) {
        return (num > 9) ? num : 0 + num.toString();
      }
      $('span.countdown').html(pad(minutes) + ":" +  pad(seconds));

    }, 1000);

  })

});
