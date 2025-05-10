#!/usr/bin/env node

const readline = require('readline');
const canboatjs = require('@canboat/canboatjs')

const parser = new canboatjs.FromPgn()


// Store filters for NMEA messages
let activeFilters = [];

let simpleCan = new canboatjs.SimpleCan({
    canDevice: 'can0',
    preferredAddress: 66,
    disableDefaultTransmitPGNs: true,
    transmitPGNs: [126983, 126985],
    app: {
        on: function(eventName, eventData) {
            //console.log("on:" +eventName, eventData)

        },
        emit: function(eventName, eventData) {
            //console.log("emit:" +eventName, eventData)

            if ( eventName == 'nmea2000OutAvailable' )
                sendResponse({ event: 'on_bridge_ready', address: simpleCan.candevice.address });
        }
    },
   /* addressClaim: {
      "Unique Number": 139725,
      "Manufacturer Code": 'Fusion Electronics',
      "Device Function": 130,
      "Device Class": 'Entertainment',
      "Device Instance Lower": 0,
      "Device Instance Upper": 0,
      "System Instance": 0,
      "Industry Group": 'Marine'
    },*/
    productInfo: {
      "NMEA 2000 Version": 1300,
      "Product Code": 668,
      "Model ID": "Anchor Alarm",
      "Software Version Code": "1.0",
      "Model Version": "1.0",
      "Model Serial Code": "123456",
      "Certification Level": 0,
      "Load Equivalency": 1
    }
  }, function (data) {
    // a broadcast message or for us
    if ( data.pgn.dst == simpleCan.candevice.address || data.pgn.dst == 255 ) {

        // handle address claim and iso request
        if ( [59904, 60928].includes(data.pgn.pgn) ) {
            pgnData = parser.parse(data)
            if ( pgnData ) {
                simpleCan.candevice.n2kMessage(pgnData);
            }
        }

        if ( ! activeFilters.includes(data.pgn.pgn) )
            return; // we don't care about that message
    
        pgnData = parser.parse(data)
        //console.log("received message", data, pgnData)

        if ( pgnData ) {
            sendResponse({ event: 'on_NMEA_message', message: pgnData });
        }
    }

})
  
simpleCan.start()


// Setting up readline to communicate via stdin and stdout
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

// Utility function to send JSON responses to stdout
function sendResponse(response) {
  process.stdout.write(JSON.stringify(response) + '\n');
}

// Function to handle incoming commands
function handleCommand(command) {
  const { id, command: cmd, message, filter } = command;

  switch (cmd) {
    case 'sendPGN':
      if (message) {
        simpleCan.sendPGN(message); // Send the NMEA message to CAN bus
        sendResponse({ event: 'on_sendPGN', id, result: 0 });
      } else {
        sendResponse({ event: 'on_sendPGN', id, result: 1, error: 'Message is missing' });
      }
      break;

    case 'filterPGN':
      if (Array.isArray(filter)) {
        activeFilters = filter; // Update active filters
        sendResponse({ event: 'on_filterPGN', id, filters: activeFilters });
      } else {
        sendResponse({ event: 'on_filterPGN', id, result: 1, error: 'Invalid filter format' });
      }
      break;

    default:
      sendResponse({ event: 'error', id, error: `Unknown command: ${cmd}` });
      break;
  }
}


// Listen for commands via stdin
rl.on('line', (line) => {
  try {
    const command = JSON.parse(line);
    handleCommand(command);
  } catch (error) {
    sendResponse({ event: 'error', error: 'Invalid JSON input' });
  }
});




