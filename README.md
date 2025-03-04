# Home Assistant to Sony AVR STR-DN1040, STR_DA5800ES, STR-DN850, STR-DN1060 & Other AVRs


[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![maintained](https://img.shields.io/maintenance/yes/2025.svg)](#)
[![maintainer](https://img.shields.io/badge/maintainer-%20%40petes--UK-blue.svg)](#)
[![version](https://img.shields.io/github/v/release/peteS-UK/sonyavr)](#)

This custom component implements a media player entity and a remote entity  for Home Assistant to allow for integration with Sony AVR-STR receivers.  It's developed with the STR-DN1040 and has been tested with STR_DA5800ES, STR-DN1060 and STR-DN850.  

Online sources suggest similar commands may work with

| Year | AVR |
| --- | --- |
| 2016 | STR-ZA1100ES, STR-ZA2100ES, STR-ZA3100ES, STR-DN810ES, STR-DN1070 |
| 2015 | STR-DN1060, STR-ZA5000ES |
| 2014 | STR-ZA1000ES, STR-ZA2000ES, STR-ZA3000ES, STR-DN1050 |
| 2013 | STR-DN1040 |
| 2012 | STR-DA1800, STR-DA2800, STR-DA5800 |

but most of these are untested at present.  It's known not to work with STR-DN1030, which doesn't respond to the same commands or send feedback.  

For other AVRs, you may need to change the default port during configuration.  By default, the port is 33335, but some online sources suggest ports might be

| Port | AVR |
| --- | --- |
| 8080 | STR-DA1800 |
| 33336 | DN-1070 & CISv2 |
| 33335 | All Others |

The integration is a Local Push integration - i.e. it subscribes to notification of changes to the AVR, so doesn't need to periodically poll for its state.

## Network Standby
The integration requires Network Standby to be available and enabled on the AVR.  Please make sure Network Standby is enabled befoer installing the integration.

## Installation

The preferred installation approach is via Home Assistant Community Store - aka [HACS](https://hacs.xyz/).  

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=peteS-UK&repository=emotiva&category=integration)

If you want to download the integration manually, create a new folder called sonyavr under your custom_components folder in your config folder.  If the custom_components folder doesn't exist, create it first.  Once created, download the files and folders from the [github repo](https://github.com/peteS-UK/sonyavr/tree/main/custom_components/sonyavr) into this new sonyavr folder.

Once downloaded either via HACS or manually, restart your Home Assistant server.

## Configuration

Configuration is done through the Home Assistant UI.  Once you're installed the integration, go into your Integrations (under Settings, Devices & Services), select Add Integration, and choose the SONY AVR integration, or click the shortcut button below (requires My Homeassistant configured).

[![Add Integration to your Home Assistant
instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sonyavr)

This will display the configuration page.  

### Manual Entry
You need to enter the details of your processor manually - IP address, name, model and port.

When you select Submit, the configuration will setup the components in Home Assistant.  It will create one device, two entities and a service.

## Device & Entities
A device will be created with the name given during setup.

### Media Player entity
A media player entity will be created with a default entity_id of media_player.sonyavr.  

You can control power state, volume, muting, source and sound mode from the media player.  You can also use this entity from any card for media player.

### Remote entity
A remote entity will be created with a default entity_id of remote.sonyavr.

This entity only supports power on and off, and mute on and off functions.  It doesn't support sending commands directly, since the actual commands for the AVR are just byte strings.  Please use the Send Command service below.

### Sensor entity
A sensor entity will be created with a default entity_id of sensor.sonyavr_volume which shows the current volume of the AVR.

## Sony AVR. Send Command

The integration provides a service which allows you to send commands to the AVR.  This service provides you with a dropdown list of all of the available commands.


### Media Player State

The integration tracks the the state of the volume on the AVR and creates and maintains an attribute on the media_player.sonyavr entity.  This is the volume as displayed on the AVR, rather than the percentage volume which Home Assistant provides.

## References

The integration is based on work done at https://gist.github.com/IceEyz/c55d36614d58c006ad698afbb98b7099, which itself was derived from https://github.com/aschaeffer/sony-av-indicator.
