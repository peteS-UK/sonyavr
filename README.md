# Home Assistant to Sony AVR STR-DN1040


[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)


This custom component implements a media player entity and a remote entity  for Home Assistant to allow for integration with Sony AVR-STR receivers.  It's tested with the STR-DN1040.  It may work with other similar generation Sony AVRs, but this is untested at present.

The integration is a Local Push integration - i.e. it subscribes to notification of changes to the AVR, so doesn't need to periodically poll for its state.

## Network Standby
The integration requires Network Standby to be available and enabled on the AVR.  Please make sure Network Standby is enabled befoer installing the integration.

## Installation

The preferred installation approach is via Home Assistant Community Store - aka [HACS](https://hacs.xyz/).  The repo is installable as a [Custom Repo](https://hacs.xyz/docs/faq/custom_repositories) via HACS.

If you want to download the integration manually, create a new folder called sonyavr under your custom_components folder in your config folder.  If the custom_components folder doesn't exist, create it first.  Once created, download the files and folders from the [github repo](https://github.com/peteS-UK/sonyavr/tree/main/custom_components/sonyavr) into this new sonyavr folder.

Once downloaded either via HACS or manually, restart your Home Assistant server.

## Configuration

Configuration is done through the Home Assistant UI.  Once you're installed the integration, go into your Integrations (under Settings, Devices & Services), select Add Integration, and choose the SONY AVR integration.

This will display the configuration page.  

### Manual Entry
You need to enter the details of your processor manually - IP address, name and model.

When you select Submit, the configuration will setup the components in Home Assistant.  It will create one device, one entity and a service.

## Device & Entities
A device will be created with the name given during setup..


### Media Player entity
A media player entity will be created with a default entity_id of media_player.sonyavr.  


You can control power state, volume, muting, source and sound mode from the media player.  You can also use this entity from any card for media player.

## Sony AVR. Send Command

The integration provides a service which allows you to send commands to the AVR.  This service provides you with a dropdown list of all of the available commands.


### Media Player State

The integration tracks the the state of the volume on the AVR and creates and maintains an attribute on the media_player.sonyavr entity.  This is the volume as displayed on the AVR, rather than the percentage volume which Home Assistant provides.

## References

The integration is based on work done at https://gist.github.com/IceEyz/c55d36614d58c006ad698afbb98b7099, which itself was derived from https://github.com/aschaeffer/sony-av-indicator.
