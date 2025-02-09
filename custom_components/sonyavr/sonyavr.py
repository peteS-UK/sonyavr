__author__ = "andreasschaeffer"
__author__ = "michaelkapuscik"
__author__ = "petersketch"

import socket

import logging

import binascii

import asyncio

import sys

from .const import (
    MAX_VOLUME,
    MIN_VOLUME,
    LOW_VOLUME,
    VOLUME_STEP,
    STR_DA5800ES_MAX_VOLUME,
    STR_DA5800ES_MIN_VOLUME,
    STR_DA5800ES_VOLUME_STEP,
    CONF_PING_INTERVAL,
)

from asyncping3 import ping


_LOGGER = logging.getLogger(__name__)

# logging.basicConfig(level = logging.DEBUG, format = "%(asctime)-15s [%(name)-5s] [%(levelname)-5s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# 80, 5000, 8008, 8009, 10000, 22222, 33335, 33336, 35275, 41824, 50001, 50002, 52323, 54400
TCP_PORT_1 = 33335
TCP_PORT_2 = 33336
BUFFER_SIZE = 1024


SOURCE_NAMES = [
    "bd",
    "dvd",
    "game",
    "satCaTV",
    "video1",
    "video2",
    "video3",
    "tv",
    "saCd",
    "fmTuner",
    "usb",
    "homeNetwork",
    "internetServices",
]
SOUND_FIELD_NAMES = [
    ["twoChannelStereo", "analogDirect", "multiStereo", "afd"],
    ["pl2Movie", "neo6Cinema", "hdDcs"],
    [
        "pl2Music",
        "neo6Music",
        "concertHallA",
        "concertHallB",
        "concertHallC",
        "jazzClub",
        "liveConcert",
        "stadium",
        "sports",
        "portableAudio",
    ],
]

# Byte 5 (0x00) seems to be the zone (not STR-DN-860, but maybe STR-DN-1060)
CMD_SOURCE_MAP = {
    "bd": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1B, 0x00]),
    "dvd": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1B, 0x00]),
    "game": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1C, 0x00]),
    "satCaTV": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x16, 0x00]),
    "video1": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x10, 0x00]),
    "video2": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x11, 0x00]),
    "video3": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x12, 0x00]),
    "tv": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x1A, 0x00]),
    "saCd": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x02, 0x00]),
    # "hdmi1":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x21, 0x00]),
    # "hdmi2":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x22, 0x00]),
    # "hdmi3":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x23, 0x00]),
    # "hdmi4":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x24, 0x00]),
    # "hdmi5":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x25, 0x00]),
    # "hdmi6":              bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x26, 0x00]),
    "fmTuner": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x2E, 0x00]),
    "amTuner": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x2F, 0x00]),
    # "shoutcast":          bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x32, 0x00]),
    "bluetooth": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x33, 0x00]),
    "usb": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x34, 0x00]),
    "homeNetwork": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x3D, 0x00]),
    "internetServices": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x3E, 0x00]),
    "screenMirroring": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0x40, 0x00]),
    "googleCast": bytearray([0x02, 0x04, 0xA0, 0x42, 0x00, 0xFF, 0x00]),
}

# Byte 5 (0x00) seems to be the zone (not STR-DN-860, but maybe STR-DN-1060)
CMD_MUTE = bytearray([0x02, 0x04, 0xA0, 0x53, 0x00, 0x01, 0x08])
CMD_UNMUTE = bytearray([0x02, 0x04, 0xA0, 0x53, 0x00, 0x00, 0x09])

# Byte 5 (0x00) seems to be the zone (not STR-DN-860, but maybe STR-DN-1060)
CMD_POWER_ON = bytearray([0x02, 0x04, 0xA0, 0x60, 0x00, 0x01, 0x00])
CMD_POWER_OFF = bytearray([0x02, 0x04, 0xA0, 0x60, 0x00, 0x00, 0x00])

CMD_HDMIOUT_ON = bytearray([0x02, 0x03, 0xA0, 0x45, 0x00, 0x00])
CMD_HDMIOUT_OFF = bytearray([0x02, 0x03, 0xA0, 0x45, 0x03, 0x00])

# Last byte seems to be zero (but was a checksum)
CMD_SOUND_FIELD_MAP = {
    "twoChannelStereo": bytearray([0x02, 0x03, 0xA3, 0x42, 0x00, 0x00]),
    "analogDirect": bytearray([0x02, 0x03, 0xA3, 0x42, 0x02, 0x00]),
    "multiStereo": bytearray([0x02, 0x03, 0xA3, 0x42, 0x27, 0x00]),
    "afd": bytearray([0x02, 0x03, 0xA3, 0x42, 0x21, 0x00]),
    "pl2Movie": bytearray([0x02, 0x03, 0xA3, 0x42, 0x23, 0x00]),
    "neo6Cinema": bytearray([0x02, 0x03, 0xA3, 0x42, 0x25, 0x00]),
    "hdDcs": bytearray([0x02, 0x03, 0xA3, 0x42, 0x33, 0x00]),
    "pl2Music": bytearray([0x02, 0x03, 0xA3, 0x42, 0x24, 0x00]),
    "neo6Music": bytearray([0x02, 0x03, 0xA3, 0x42, 0x26, 0x00]),
    "concertHallA": bytearray([0x02, 0x03, 0xA3, 0x42, 0x1E, 0x00]),
    "concertHallB": bytearray([0x02, 0x03, 0xA3, 0x42, 0x1F, 0x00]),
    "concertHallC": bytearray([0x02, 0x03, 0xA3, 0x42, 0x38, 0x00]),
    "jazzClub": bytearray([0x02, 0x03, 0xA3, 0x42, 0x16, 0x00]),
    "liveConcert": bytearray([0x02, 0x03, 0xA3, 0x42, 0x19, 0x00]),
    "stadium": bytearray([0x02, 0x03, 0xA3, 0x42, 0x1B, 0x00]),
    "sports": bytearray([0x02, 0x03, 0xA3, 0x42, 0x20, 0x00]),
    "portableAudio": bytearray([0x02, 0x03, 0xA3, 0x42, 0x30, 0x00]),
}

# not working ? only preset up and down are working currently
CMD_FMTUNER = [
    bytearray([0x02, 0x04, 0xA1, 0x42, 0x01, 0x01, 0x17]),
    bytearray([0x02, 0x04, 0xA1, 0x42, 0x01, 0x02, 0x16]),
    bytearray([0x02, 0x04, 0xA1, 0x42, 0x01, 0x03, 0x15]),
]

CMD_FMTUNER_PRESET_DOWN = bytearray([0x02, 0x02, 0xA1, 0x0C, 0x51, 0x00])
CMD_FMTUNER_PRESET_UP = bytearray([0x02, 0x02, 0xA1, 0x0B, 0x52, 0x00])

CMD_VOLUME_MIN = bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, 0x00, 0x00])
CMD_VOLUME_MAX = bytearray([0x02, 0x06, 0xA0, 0x52, 0x00, 0x03, 0x00, 0x4A, 0x00])
CMD_VOLUME_UP = bytearray([0x02, 0x03, 0xA0, 0x55, 0x00, 0x08])
CMD_VOLUME_DOWN = bytearray([0x02, 0x03, 0xA0, 0x56, 0x00, 0x07])

# three bytes follows:
# - hours
# - minutes
# - seconds
# if hours, minutes and seconds are 0xFF, the timer was set to OFF
FEEDBACK_TIMER_PREFIX = bytearray([0x02, 0x05, 0xA8, 0x90])
FEEDBACK_TIMER_SET = bytearray([0x00])
FEEDBACK_TIMER_UPDATE = bytearray([0x3B])
FEEDBACK_TIMER_OFF = bytearray([0xFF])

# "video" == Google Cast + Bluetooth
# two bytes follows:
# - power off / unmuted / muted
# - zero byte
# byte 5 normally 0x00, but seldom 0x03
# byte 7 maybe 0 or may copy byte6, so ignore 7
# source, power_on_mute_off, power_on_mute_on, power_off
# then repeat powers for 1060
FEEDBACK_SOURCE_MAP = {
    "bd": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x1B, 0x00]),
        bytearray([0x21, 0x00, 0x78]),
        bytearray([0x23, 0x00, 0x76]),
        bytearray([0x20, 0x00, 0x79]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "dvd": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x19, 0x00]),
        bytearray([0x21, 0x00, 0x7C]),
        bytearray([0x23, 0x00, 0x7A]),
        bytearray([0x20, 0x00, 0x7D]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "game": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x1C, 0x00]),
        bytearray([0x21, 0x00, 0x7C]),
        bytearray([0x23, 0x00, 0x74]),
        bytearray([0x20, 0x00, 0x77]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "satCaTV": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x16, 0x00]),
        bytearray([0x21, 0x00, 0x82]),
        bytearray([0x23, 0x00, 0x80]),
        bytearray([0x20, 0x00, 0x83]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "video1": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x10, 0x00]),
        bytearray([0x21, 0x00, 0x8E]),
        bytearray([0x23, 0x00, 0x8C]),
        bytearray([0x20, 0x00, 0x8F]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "video2": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x11, 0x00]),
        bytearray([0x21, 0x00, 0x8C]),
        bytearray([0x23, 0x00, 0x8A]),
        bytearray([0x20, 0x00, 0x8D]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "video3": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x12, 0x00]),
        bytearray([0x21, 0x00, 0x8A]),
        bytearray([0x23, 0x00, 0x88]),
        bytearray([0x20, 0x00, 0x8B]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "tv": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x1A, 0x00]),
        bytearray([0x21, 0x00, 0x92]),
        bytearray([0x23, 0x00, 0x90]),
        bytearray([0x20, 0x00, 0x93]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "saCd": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x02, 0x00]),
        bytearray([0x21, 0x00, 0xAA]),
        bytearray([0x23, 0x00, 0xA8]),
        bytearray([0x20, 0x00, 0xAB]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "fmTuner": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x2E, 0x00]),
        bytearray([0x21, 0x00, 0xAA]),
        bytearray([0x2B, 0x00, 0x48]),
        bytearray([0x28, 0x00, 0x4B]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "amTuner": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x2F, 0x00]),
        bytearray([0x21, 0x00, 0xAA]),
        bytearray([0x2B, 0x00, 0x46]),
        bytearray([0x28, 0x00, 0x49]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "bluetooth": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x33, 0x00]),
        bytearray([0x21, 0x00, 0xAA]),
        bytearray([0x23, 0x00, 0x46]),
        bytearray([0x20, 0x00, 0xAB]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "usb": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x34, 0x00]),
        bytearray([0x29, 0x00, 0x3E]),
        bytearray([0x2B, 0x00, 0x3C]),
        bytearray([0x28, 0x00, 0x3F]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "homeNetwork": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x3D, 0x00]),
        bytearray([0x29, 0x00, 0x2C]),
        bytearray([0x2B, 0x00, 0x2A]),
        bytearray([0x28, 0x00, 0x2D]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "internetServices": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0x3E, 0x00]),
        bytearray([0x21, 0x00, 0x32]),
        bytearray([0x2B, 0x00, 0x28]),
        bytearray([0x28, 0x00, 0x2B]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
    "googleCast": [
        bytearray([0x02, 0x07, 0xA8, 0x82, 0x00, 0xFF, 0x00]),
        bytearray([0x21, 0x00, 0xAA]),
        bytearray([0x23, 0x00, 0xA8]),
        bytearray([0x20, 0x00, 0xAB]),
        bytearray([0x00, 0x11, 0x00]),
        bytearray([0x00, 0x13, 0x00]),
        bytearray([0x00, 0x10, 0x00]),
    ],
}

FEEDBACK_SOUND_FIELD_MAP = {
    "twoChannelStereo": bytearray([0x02, 0x04, 0xAB, 0x82, 0x00, 0x00]),
    "analogDirect": bytearray([0x02, 0x04, 0xAB, 0x82, 0x02, 0x00]),
    "multiStereo": bytearray([0x02, 0x04, 0xAB, 0x82, 0x27, 0x00]),
    "afd": bytearray([0x02, 0x04, 0xAB, 0x82, 0x21, 0x00]),
    "pl2Movie": bytearray([0x02, 0x04, 0xAB, 0x82, 0x23, 0x00]),
    "neo6Cinema": bytearray([0x02, 0x04, 0xAB, 0x82, 0x25, 0x00]),
    "hdDcs": bytearray([0x02, 0x04, 0xAB, 0x82, 0x33, 0x00]),
    "pl2Music": bytearray([0x02, 0x04, 0xAB, 0x82, 0x24, 0x00]),
    "neo6Music": bytearray([0x02, 0x04, 0xAB, 0x82, 0x26, 0x00]),
    "concertHallA": bytearray([0x02, 0x04, 0xAB, 0x82, 0x1E, 0x00]),
    "concertHallB": bytearray([0x02, 0x04, 0xAB, 0x82, 0x1F, 0x00]),
    "concertHallC": bytearray([0x02, 0x04, 0xAB, 0x82, 0x38, 0x00]),
    "jazzClub": bytearray([0x02, 0x04, 0xAB, 0x82, 0x16, 0x00]),
    "liveConcert": bytearray([0x02, 0x04, 0xAB, 0x82, 0x19, 0x00]),
    "stadium": bytearray([0x02, 0x04, 0xAB, 0x82, 0x1B, 0x00]),
    "sports": bytearray([0x02, 0x04, 0xAB, 0x82, 0x20, 0x00]),
    "portableAudio": bytearray([0x02, 0x04, 0xAB, 0x82, 0x30, 0x00]),
}

FEEDBACK_PURE_DIRECT_ON = bytearray([0x02, 0x03, 0xAB, 0x98, 0x01])
FEEDBACK_PURE_DIRECT_OFF = bytearray([0x02, 0x03, 0xAB, 0x98, 0x00])

# one byte follows
FEEDBACK_SOUND_OPTIMIZER_PREFIX = bytearray([0x02, 0x04, 0xAB, 0x92, 0x48])
FEEDBACK_SOUND_OPTIMIZER_OFF = bytearray([0x00])
FEEDBACK_SOUND_OPTIMIZER_NORMAL = bytearray([0x01])
FEEDBACK_SOUND_OPTIMIZER_LOW = bytearray([0x02])

FEEDBACK_FMTUNER_PREFIX = bytearray([0x02, 0x07, 0xA9, 0x82, 0x80])
FEEDBACK_FMTUNER_STEREO = bytearray([0x00])
FEEDBACK_FMTUNER_MONO = bytearray([0x80])

FEEDBACK_VOLUME = bytearray([0x02, 0x06, 0xA8, 0x92, 0x00, 0x03, 0x00])
# Volume feedback for 1060
FEEDBACK_VOLUME_1 = bytearray([0x02, 0x06, 0xA8, 0x8B, 0x00, 0x03, 0x00])


FEEDBACK_AUTO_STANDBY_ON = bytearray([0x02, 0x03, 0xA8, 0xA4, 0xCC])
FEEDBACK_AUTO_STANDBY_OFF = bytearray([0x02, 0x03, 0xA8, 0xA4, 0x4C])

FEEDBACK_AUTO_PHASE_MATCHING_AUTO = bytearray([0x2, 0x4, 0xAB, 0x97, 0x48, 0x2])
FEEDBACK_AUTO_PHASE_MATCHING_OFF = bytearray([0x2, 0x4, 0xAB, 0x97, 0x48, 0x0])

SOURCE_MENU_MAP = {
    "bd": "Blueray",
    "dvd": "DVD",
    "game": "Game",
    "satCaTV": "Sat / Cable",
    "video1": "Video 1",
    "video2": "Video 2",
    "video3": "Video 3",
    "tv": "TV",
    "saCd": "CD",
    "fmTuner": "FM Tuner",
    "amTuner": "AM Tuner",
    # 	"bluetooth": "Bluetooth",
    "usb": "USB",
    "homeNetwork": "Home Network",
    "internetServices": "Internet Services",
    # 	"screenMirroring": "Screen Mirroring",
    # 	"googleCast": "Google Cast",
}

SOUND_FIELD_MENU_MAP = {
    "twoChannelStereo": "2 Channels",
    "analogDirect": "Analog Direct",
    "multiStereo": "Multi Stereo",
    "afd": "A.F.D.",
    "pl2Movie": "PL-II Movie",
    "neo6Cinema": "Neo 6: Cinema",
    "hdDcs": "HD DCS",
    "pl2Music": "PL-II Music",
    "neo6Music": "Neo 6: Music",
    "concertHallA": "Concert Hall A",
    "concertHallB": "Concert Hall B",
    "concertHallC": "Concert Hall C",
    "jazzClub": "Jazz Club",
    "liveConcert": "Live Concert",
    "stadium": "Stadium",
    "sports": "Sports",
    "portableAudio": "Portable Audio",
}

SOUND_OPTIMIZER_MENU_MAP = {"off": "Off", "normal": "Normal", "low": "Low"}

FM_TUNER_MENU_MAP = {
    "1": "FM4",
    "2": "FM4",
    "3": "",
    "4": "",
    "5": "",
    "6": "",
    "7": "",
    "8": "",
    "9": "",
    "10": "",
    "11": "",
    "12": "",
    "13": "",
    "14": "",
    "15": "",
    "16": "",
    "17": "",
    "18": "",
    "19": "",
    "20": "",
    "21": "",
    "22": "",
    "23": "",
    "24": "",
    "25": "",
    "26": "",
    "27": "",
    "28": "",
    "29": "",
    "30": "",
}


class StateService:
    initialized = False

    # logger = logging.getLogger("sonyavr.state")

    states = {
        "power": True,
        "hdmiout": True,
        "volume": LOW_VOLUME,
        "muted": False,
        "source": None,
        "sound_field": None,
        "pure_direct": False,
        "sound_optimizer": None,
        "timer": False,
        "timer_hours": 0,
        "timer_minutes": 0,
        "fmtuner": None,
        "fmtunerstereo": None,
        "fmtunerfreq": None,
        "auto_standby": True,
        "auto_phase_matching": True,
    }

    notifications = {
        "power": True,
        "hdmiout": True,
        "volume": False,
        "muted": True,
        "source": True,
        "sound_field": False,
        "pure_direct": True,
        "sound_optimizer": True,
        "timer": True,
        "fmtuner": True,
        "auto_standby": True,
        "auto_phase_matching": True,
    }

    def __getattr__(self, key):
        try:
            return self.states[key]
        except KeyError as key:
            raise AttributeError(key)

    def __setattr_(self, key, value):
        try:
            self.states[key] = value
        except KeyError as key:
            raise AttributeError(key)

    def update_power(self, power, state_only=False):
        if self.initialized:
            changed = power != self.power
            self.power = power
            if changed:
                _LOGGER.debug("Power state: %s" % power)

    def update_hdmiout(self, hdmiout, state_only=False):
        if self.initialized:
            changed = hdmiout != self.hdmiout
            self.hdmiout = hdmiout
            if changed:
                _LOGGER.debug("HDMI Out: %s" % hdmiout)

    def update_volume(self, vol):
        if self.initialized:
            if vol > self.volume:
                self.muted = False
            self.volume = vol
            _LOGGER.debug("Volume State Updated to %s" % vol)

    def update_muted(self, muted):
        if self.initialized:
            changed = muted != self.muted
            self.muted = muted
            if changed:
                if self.muted:
                    _LOGGER.debug("Muted")
                else:
                    _LOGGER.debug("Unmuted")

    def update_source(self, source, state_only=False):
        changed = source != self.source
        self.source = source
        if not state_only:
            self.update_power(True, True)
        if changed:
            _LOGGER.debug("Source: %s" % source)

    def update_sound_field(self, sound_field, state_only=False):
        changed = sound_field != self.sound_field
        self.sound_field = sound_field
        if changed:
            _LOGGER.debug("Sound field: %s" % sound_field)

    def update_pure_direct(self, pure_direct):
        if self.initialized:
            self.pure_direct = pure_direct
            _LOGGER.debug("Pure Direct: %s" % pure_direct)

    def update_sound_optimizer(self, sound_optimizer):
        if self.initialized:
            self.sound_optimizer = sound_optimizer
            _LOGGER.debug("Sound Optimizer: %s" % sound_optimizer)

    def update_timer(self, hours, minutes, seconds, set_timer, was_updated):
        self.timer = set_timer
        self.timer_hours = hours
        self.timer_minutes = minutes
        _LOGGER.debug(
            "Timer: %d:%d:%d Set: %s Updated: %s"
            % (hours, minutes, seconds, set_timer, was_updated)
        )

    def update_fmtuner(self, fmtuner, stereo, freq):
        if self.initialized:
            self.fmtuner = fmtuner
            self.fmtunerstereo = stereo
            self.fmtunerfreq = freq
            _LOGGER.debug("FM Tuner: %d (%3.2f MHz) Stereo: %s", fmtuner, freq, stereo)

    def update_auto_standby(self, auto_standby):
        if self.initialized:
            self.auto_standby = auto_standby
            _LOGGER.debug("Auto Standby: %s" % auto_standby)

    def update_auto_phase_matching(self, auto_phase_matching):
        if self.initialized:
            self.auto_phase_matching = auto_phase_matching
            _LOGGER.debug("Auto Phase Matching: %s", auto_phase_matching)


class CommandService:
    device_service = None
    state_service = None
    initialized = False
    block_sending = False

    scroll_step_volume = 1

    logger = logging.getLogger("cmd")
    data_logger = logging.getLogger("send")

    def __init__(self, device_service, state_service, port):
        self.device_service = device_service
        self.state_service = state_service
        self.port = port

    async def async_connect(self):
        try:
            self.command_reader, self.command_writer = await asyncio.open_connection(
                self.device_service.ip, self.port
            )
        except IOError as e:
            _LOGGER.critical(
                "Cannot connect to command socket %d: %s", e.errno, e.strerror
            )
        except Exception:
            _LOGGER.critical(
                "Unknown error on command socket connection %s", sys.exc_info()[0]
            )

    async def async_reconnect(self):
        try:
            await self.async_disconnect()
        except Exception:
            pass
        try:
            await self.async_connect()
        except IOError as e:
            _LOGGER.critical(
                "Cannot connect to command socket %d: %s", e.errno, e.strerror
            )
        except Exception:
            _LOGGER.critical(
                "Unknown error on command socket connection %s", sys.exc_info()[0]
            )

    async def async_disconnect(self):
        try:
            self.command_writer.close()
            await self.command_writer.wait_closed()
        except Exception:
            _LOGGER.error("Cannot disconnect from command socket")

    async def async_send_command(self, cmd):
        if not self.block_sending and self.command_writer is not None:
            try:
                self.command_writer.write(cmd)
                await self.command_writer.drain()
                _LOGGER.debug("Command : %s", ", ".join([hex(byte) for byte in cmd]))
            except Exception:
                _LOGGER.error("Send command failed.  Attempting to reconnect")
                await self.async_reconnect()
                self.command_writer.write(cmd)
                await self.command_writer.drain()
        else:
            if self.block_sending:
                _LOGGER.debug("Blocked")
            if self.command_writer is None:
                _LOGGER.critical("Command Socket doesn't exist")
            await asyncio.sleep(50.0 / 1000.0)

    async def async_power_on(self):
        await self.async_send_command(CMD_POWER_ON)

    async def async_power_off(self):
        await self.async_send_command(CMD_POWER_OFF)

    async def async_toggle_power(self):
        if self.initialized:
            if self.state_service.power:
                await self.async_power_off()
                self.state_service.update_power(False)
            else:
                await self.async_power_on()
                self.state_service.update_power(True)

    async def async_hdmiout_on(self):
        await self.async_send_command(CMD_HDMIOUT_ON)

    async def async_hdmiout_off(self):
        await self.async_send_command(CMD_HDMIOUT_OFF)

    async def async_toggle_hdmiout(self):
        if self.initialized:
            if self.state_service.hdmiout:
                await self.async_hdmiout_off()
                self.state_service.update_hdmiout(False)
            else:
                await self.async_hdmiout_on()
                self.state_service.update_hdmiout(True)

    async def async_set_volume(self, vol):
        if self.state_service.volume_model == 3:
            # Normal Volume Model
            cmd = bytearray(
                [
                    0x02,
                    0x06,
                    0xA0,
                    0x52,
                    0x00,
                    0x03,
                    0x00,
                    min(int(vol), self.state_service.volume_max),
                    0x00,
                ]
            )
        else:
            # Volume Model with float
            # convert vol to closest .0 or .5
            _vol = round(float(vol) * 2) / 2
            _vol = max(
                min(_vol, self.state_service.volume_max), self.state_service.volume_min
            )

            # When the volume is .5, avr always adds .5 to result, so subtract 1 for -ve's

            _vol_byte = (
                int(_vol)
                if _vol > 0
                else int(_vol) + 256 - (1 if (vol % 1) == 0.5 else 0)
            )

            cmd = bytearray(
                [
                    0x02,
                    0x06,
                    0xA0,
                    0x52,
                    0x00,
                    0x01,
                    _vol_byte,
                    0x80 if (vol % 1) == 0.5 else 0x00,
                    0x00,
                ]
            )
        await self.async_send_command(cmd)
        self.state_service.update_volume(vol)

    async def async_volume_up(self):
        target_volume = self.state_service.volume + self.scroll_step_volume
        if target_volume <= self.state_service.volume_max:
            if self.state_service.volume_model == 3:
                await self.async_set_volume(target_volume)
            else:
                await self.async_send_command(CMD_VOLUME_UP)

    async def async_volume_down(self):
        target_volume = self.state_service.volume - self.scroll_step_volume
        if target_volume >= self.state_service.volume_min:
            if self.state_service.volume_model == 3:
                await self.async_set_volume(target_volume)
            else:
                await self.async_send_command(CMD_VOLUME_DOWN)

    async def async_mute(self):
        if self.initialized:
            await self.async_send_command(CMD_MUTE)
            self.state_service.update_muted(True)

    async def async_unmute(self):
        if self.initialized:
            await self.async_send_command(CMD_UNMUTE)
            self.state_service.update_muted(False)

    async def async_select_source(self, source):
        _LOGGER.debug("Select Source %s", source)
        if self.initialized and self.state_service.source != source:
            self.state_service.update_source(source)
            await self.async_send_command(CMD_SOURCE_MAP[source])

    async def async_source_up(self):
        _LOGGER.debug("Source Up")
        for i in range(len(SOURCE_NAMES)):
            if self.state_service.source == SOURCE_NAMES[i]:
                if i < len(SOURCE_NAMES) - 1:
                    await self.async_select_source(SOURCE_NAMES[i + 1])
                    return
                else:
                    await self.async_select_source(SOURCE_NAMES[0])
                    return

    async def async_source_down(self):
        _LOGGER.debug("Source Down")
        for i in range(len(SOURCE_NAMES)):
            if self.state_service.source == SOURCE_NAMES[i]:
                if i > 0:
                    await self.async_select_source(SOURCE_NAMES[i - 1])
                    return
                else:
                    await self.async_select_source(SOURCE_NAMES[len(SOURCE_NAMES) - 1])
                    return

    async def async_select_sound_field(self, sound_field):
        if self.initialized and self.state_service.sound_field != sound_field:
            self.state_service.update_sound_field(sound_field)
            await self.async_send_command(CMD_SOUND_FIELD_MAP[sound_field])

    def set_fmtuner(self, fmtuner):
        self.send_command(CMD_FMTUNER[fmtuner])

    def fmtuner_preset_up(self):
        if self.initialized:
            if self.state_service.source != "fmTuner":
                self.send_command(CMD_SOURCE_MAP["fmTuner"])
            self.send_command(CMD_FMTUNER_PRESET_UP)

    def fmtuner_preset_down(self):
        if self.initialized:
            if self.state_service.source != "fmTuner":
                self.send_command(CMD_SOURCE_MAP["fmTuner"])
            self.send_command(CMD_FMTUNER_PRESET_DOWN)


class DeviceService:
    initialized = False
    my_ip = None
    my_network = None

    ip = None

    logger = logging.getLogger("dev")

    def __init__(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            # doesn't even have to be reachable
            s.connect(("8.8.8.8", 53))
            _ip = s.getsockname()[0]
        except Exception:
            _ip = "127.0.0.1"
        finally:
            s.close()
        self.my_ip = _ip
        _LOGGER.debug(f"IP: {self.my_ip}")


class FeedbackWatcher:
    device_service = None
    state_service = None
    command_service = None
    ended = False
    # socket = None
    port = None

    logger = logging.getLogger("sonyavr.feed")
    data_logger = logging.getLogger("sonyavr.recv")

    def __init__(self, sony_avr, device_service, state_service, command_service, port):
        self.device_service = device_service
        self.state_service = state_service
        self.command_service = command_service
        self.sony_avr = sony_avr
        self.port = port

    async def kill(self):
        self.ended = True
        # self.socket.shutdown(socket.SHUT_WR)
        self.writer.close()
        await self.writer.wait_closed()

    def check_volume(self, data):
        if FEEDBACK_VOLUME[0:5] == data[0:5] or FEEDBACK_VOLUME_1[0:5] == data[0:5]:
            # Check if AVR is STR or not
            if self.state_service.volume_model is None:
                _LOGGER.debug("Vol Max %s", self.state_service.volume_max)
                if data[5] == 1:
                    _LOGGER.debug("Setting Volume Model 1")
                    self.state_service.volume_model = 1
                    self.state_service.volume_min = STR_DA5800ES_MIN_VOLUME
                    if self.state_service.volume_max == 0:
                        # Prevent overwrite of configured volume on reload
                        self.state_service.volume_max = STR_DA5800ES_MAX_VOLUME
                        _LOGGER.debug(
                            "Vol Model 1 : Initial Max Volume set to %s",
                            self.state_service.volume_max,
                        )
                    self.state_service.volume_range = (
                        self.state_service.volume_max - self.state_service.volume_min
                    )
                    self.command_service.scroll_step_volume = STR_DA5800ES_VOLUME_STEP
                else:
                    _LOGGER.debug("Setting Volume Model 3")
                    self.state_service.volume_model = 3
                    self.state_service.volume_min = MIN_VOLUME
                    if self.state_service.volume_max == 0:
                        # Prevent overwrite of configured volume on reload
                        self.state_service.volume_max = MAX_VOLUME
                        _LOGGER.debug(
                            "Vol Model 3 : Initial Max Volume set to %s",
                            self.state_service.volume_max,
                        )
                    self.state_service.volume_range = (
                        self.state_service.volume_max - self.state_service.volume_min
                    )
                    self.command_service.scroll_step_volume = VOLUME_STEP

            if self.state_service.volume_model == 3:
                vol = data[7]
            else:
                vol = float(data[6] if data[6] < 128 else (data[6] - 256)) + (
                    data[7] / 256.0
                )

            _LOGGER.debug("Vol %s", vol)

            if vol <= self.state_service.volume_max:
                self.state_service.update_volume(vol)
            elif vol == self.state_service.volume_max + 1:
                self.command_service.block_sending = False
                self.command_service.async_set_volume(self.state_service.volume_max)
                self.state_service.volume = self.state_service.volume_max
                self.command_service.block_sending = True
            return True
        return False

    def check_source(self, data):
        source_switched = False
        for source, source_feedback in FEEDBACK_SOURCE_MAP.items():
            if source_feedback[0][:6] == data[:6]:
                _LOGGER.debug("Source matched %s", source)
                _LOGGER.debug("Extra data %s", binascii.hexlify(data[-3:], ":"))
                self.state_service.update_source(source)
                # The command also contains the power and muted states
                if source_feedback[3] == data[-3:] or source_feedback[6] == data[-3:]:
                    _LOGGER.debug("Power Off")
                    # FEEDBACK_POWER_OFF
                    self.state_service.update_power(False, True)
                elif source_feedback[1] == data[-3:] or source_feedback[4] == data[-3:]:
                    _LOGGER.debug("Power On Mute Off")
                    # FEEDBACK_POWER_ON_MUTE_OFF
                    self.state_service.update_power(True, True)
                    self.state_service.update_muted(False)
                elif source_feedback[2] == data[-3:] or source_feedback[5] == data[-3:]:
                    _LOGGER.debug("Power On Mute On")
                    # FEEDBACK_POWER_ON_MUTE_ON
                    self.state_service.update_power(True, True)
                    self.state_service.update_muted(True)
                else:
                    _LOGGER.debug(
                        "Unmatched Power/Mute Data %s",
                        binascii.hexlify(data[-3:], ":"),
                    )
                source_switched = True
        return source_switched

    def check_sound_field(self, data):
        sound_field_switched = False
        for sound_field, sound_field_feedback in FEEDBACK_SOUND_FIELD_MAP.items():
            if sound_field_feedback[:6] == data[:6]:
                _LOGGER.debug("Updating Sound Field state")
                self.state_service.update_sound_field(sound_field)
                sound_field_switched = True
        return sound_field_switched

    def check_pure_direct(self, data):
        if FEEDBACK_PURE_DIRECT_ON == data:
            self.state_service.update_pure_direct(True)
            return True
        elif FEEDBACK_PURE_DIRECT_OFF == data:
            self.state_service.update_pure_direct(False)
            return True
        return False

    def check_sound_optimizer(self, data):
        if FEEDBACK_SOUND_OPTIMIZER_PREFIX == data[:-1]:
            if FEEDBACK_SOUND_OPTIMIZER_OFF == data[-1]:
                self.state_service.update_sound_optimizer("off")
            elif FEEDBACK_SOUND_OPTIMIZER_NORMAL == data[-1]:
                self.state_service.update_sound_optimizer("normal")
            elif FEEDBACK_SOUND_OPTIMIZER_LOW == data[-1]:
                self.state_service.update_sound_optimizer("low")
            return True
        return False

    def check_timer(self, data):
        if FEEDBACK_TIMER_PREFIX == data[:-3]:
            if FEEDBACK_TIMER_SET == data[-1]:
                self.state_service.update_timer(
                    data[-3], data[-2], data[-1], True, False
                )
                return True
            elif FEEDBACK_TIMER_UPDATE == data[-1]:
                self.state_service.update_timer(
                    data[-3], data[-2], data[-1], True, True
                )
                return True
            elif FEEDBACK_TIMER_OFF == data[-1]:
                self.state_service.update_timer(
                    data[-3], data[-2], data[-1], False, False
                )
                return True
            else:
                return True
        return False

    def check_fmtuner(self, data):
        if FEEDBACK_FMTUNER_PREFIX == data[0:5]:
            fmtuner = data[5]
            stereo = True
            if data[6] == FEEDBACK_FMTUNER_MONO:
                stereo = False
            freq = round(((data[7] * 255 + data[8]) / 99.5) - 0.1, 1)
            self.state_service.update_fmtuner(fmtuner, stereo, freq)
            # self.state_service.update_source("fmTuner")
            return True
        return False

    def check_auto_standby(self, data):
        if FEEDBACK_AUTO_STANDBY_OFF == data:
            self.state_service.update_auto_standby(False)
            return True
        elif FEEDBACK_AUTO_STANDBY_ON == data:
            self.state_service.update_auto_standby(True)
            return True
        return False

    def check_auto_phase_matching(self, data):
        if FEEDBACK_AUTO_PHASE_MATCHING_OFF == data:
            self.state_service.update_auto_phase_matching(False)
            return True
        elif FEEDBACK_AUTO_PHASE_MATCHING_AUTO == data:
            self.state_service.update_auto_phase_matching(True)
            return True
        return False

    def debug_data(self, data, prepend_text=""):
        _LOGGER.debug("Debug %s%s", prepend_text, binascii.hexlify(data, ":"))

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.device_service.ip, self.port
            )
            self._connected = True
        except IOError as e:
            _LOGGER.critical(
                "Cannot create feedback listener connection %d: %s", e.errno, e.strerror
            )
            self._connected = False
        except Exception:
            _LOGGER.critical(
                "Unknown error on feedback listener connection %s", sys.exc_info()[0]
            )
            self._connected = False

        return self._connected

    async def reconnect(self):
        try:
            self.writer.close()
            await self.writer.wait_closed()

            self.reader, self.writer = await asyncio.open_connection(
                self.device_service.ip, self.port
            )

            self.command_service.block_sending = False
            _LOGGER.error("Reconnected")
        except IOError as e:
            _LOGGER.critical(
                "Cannot create feedback listener re-connection %d: %s",
                e.errno,
                e.strerror,
            )
            self.ended = True
        except Exception:
            _LOGGER.critical(
                "Unknown error on feedback listener re-connection %s", sys.exc_info()[0]
            )
            self.ended = True

    async def stop(self):
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except IOError as e:
            _LOGGER.critical(
                "Cannot close feedback listener %d: %s", e.errno, e.strerror
            )
        except Exception:
            _LOGGER.critical("Unknown error on listener close %s", sys.exc_info()[0])

    async def run(self):
        if not await self.connect():
            return

        while not self.ended:
            try:
                await asyncio.sleep(0.1)

                data = await self.reader.read(BUFFER_SIZE)

                # Prevent feedback loops by block sending commands
                self.command_service.block_sending = True

                if not self.ended:
                    self.debug_data(data)
                if (
                    not self.check_timer(data)
                    and not self.check_source(data)
                    and not self.check_sound_field(data)
                    and not self.check_pure_direct(data)
                    and not self.check_sound_optimizer(data)
                    and not self.check_fmtuner(data)
                    and not self.check_volume(data)
                    and not self.check_auto_standby(data)
                    and not self.check_auto_phase_matching(data)
                    and not self.ended
                ):
                    self.debug_data(data, "[unknown data packet]")
                else:
                    if self.sony_avr._update_cb:
                        self.sony_avr._update_cb()
                    if self.sony_avr._remote_update_cb:
                        self.sony_avr._remote_update_cb()
                    if self.sony_avr._sensor_update_cb:
                        self.sony_avr._sensor_update_cb()
            # except socket.timeout as e:
            # 	_LOGGER.debug("Timeout: reconnecting...")
            # 	self.reconnect()
            except Exception:
                _LOGGER.exception("Failed to process data: reconnecting...")
                await self.reconnect()
            finally:
                # Unblock sending commands after processing
                self.command_service.block_sending = False
        try:
            self.writer.close()
            await self.writer.wait_closed()
            _LOGGER.debug("Connection closed")
        except Exception:
            _LOGGER.error("Cannot close feedback listener connection")


class PingWatcherService:
    def __init__(self, hass, config_entry, host):
        self._hass = hass
        self._config_entry = config_entry
        self._host = host
        self._stop = False

    async def start(self):
        while not self._stop:
            if int(self._config_entry.options.get(CONF_PING_INTERVAL)) == 0:
                # Disable the listener
                _LOGGER.info("Ping Watcher disabled.  Reload config to re-enable")
                self._stop = True
                break
            # Ping the AVR
            _ping = await ping(self._host, timeout=4)
            if not _ping:
                # Pause and try again
                await asyncio.sleep(2)
                _ping = await ping(self._host, timeout=4)
            if _ping:
                # Ping succeeded - wait and retry
                await asyncio.sleep(
                    int(self._config_entry.options.get(CONF_PING_INTERVAL, 60))
                )
            else:
                # Both attempts failed, so break
                break
        # Ping failed, so wait until it succeeds again
        if not self._stop:
            _LOGGER.error(
                "Connectivity lost to %s.  Waiting for availability.", self._host
            )
        while not await ping(self._host, timeout=1) and not self._stop:
            if int(self._config_entry.options.get(CONF_PING_INTERVAL)) == 0:
                _LOGGER.info("Ping Watcher disabled.  Reload config to re-enable")
                # Disable the listener
                self._stop = True
                break
            # Ping failed - wait and retry
            await asyncio.sleep(
                int(self._config_entry.options.get(CONF_PING_INTERVAL, 60))
            )
        # Ping succeeded, so it's back, so reload
        if not self._stop:
            _LOGGER.error(
                "Connectivity re-established with %s.  Reloading configuration",
                self._host,
            )
            await asyncio.sleep(30)
            self._hass.config_entries.async_schedule_reload(self._config_entry.entry_id)

    async def stop(self):
        self._stop = True


class SonyAVR:
    indicator = None
    device_service = None
    feedback_watcher = None
    feedback_watcher_2 = None
    command_service = None
    initialized = False

    logger = logging.getLogger("Class")

    def __init__(self, hass, config_entry, ip=None, name=None, model=None, port=33335):
        self._config_entry = config_entry
        self._hass = hass
        self.device_service = DeviceService()
        self.state_service = StateService()
        self.command_service = CommandService(
            self.device_service, self.state_service, port
        )
        self.feedback_watcher = FeedbackWatcher(
            self,
            self.device_service,
            self.state_service,
            self.command_service,
            port,
        )
        self.ping_watcher = PingWatcherService(self._hass, self._config_entry, ip)

        self.initialize_device()

        self.device_service.ip = ip
        self.name = name
        self.model = model
        self.port = port
        self._update_cb = None
        self._remote_update_cb = None
        self._sensor_update_cb = None

        self.state_service.volume_model = None
        self.state_service.volume_min = 0
        self.state_service.volume_max = 0
        # self.state_service.volume_range = (
        #    self.state_service.volume_max - self.state_service.volume_min
        # )
        self.state_service.volume_range = 1

        # if self.feedback_watcher_1 != None:
        #    self.feedback_watcher_1.start()
        # if self.feedback_watcher_2 != None:
        #    self.feedback_watcher_2.start()

        self.set_initialized(True)

        # self.feedback_watcher_1.probe_volume()
        # self.feedback_watcher_1.probe_input()

    async def quit(self):
        self.set_initialized(False)
        if self.feedback_watcher is not None:
            self.feedback_watcher.kill()
        #    self.feedback_watcher_1.join(8)
        # if self.feedback_watcher_2 != None:
        #    self.feedback_watcher_2.kill()
        #    self.feedback_watcher_2.join(8)

    def initialize_device(self):
        self.device_service.initialized = True

    def poll_state(self):
        self.command_service.mute(None)
        self.command_service.unmute(None)

    async def async_poll_state(self):
        await self.command_service.async_mute()
        await asyncio.sleep(1.0)
        await self.command_service.async_unmute()
        await asyncio.sleep(1.0)
        await self.command_service.async_send_command(CMD_VOLUME_DOWN)
        _LOGGER.debug("Volume Down")
        await asyncio.sleep(1.0)
        await self.command_service.async_send_command(CMD_VOLUME_UP)
        _LOGGER.debug("Volume Down")
        await asyncio.sleep(1.0)
        await self.command_service.async_source_up()
        await asyncio.sleep(2.0)
        await self.command_service.async_source_down()
        await asyncio.sleep(2.0)

    def set_initialized(self, initialized):
        self.initialized = initialized
        self.device_service.initialized = initialized
        self.state_service.initialized = initialized
        self.command_service.initialized = initialized

    async def async_turn_on(self) -> None:
        # await self._device.async_turn_on()
        await self.command_service.async_power_on()

    async def async_turn_off(self) -> None:
        await self.command_service.async_power_off()

    async def async_mute_on(self) -> None:
        # await self._device.async_turn_on()
        await self.command_service.async_mute()

    async def async_mute_off(self) -> None:
        await self.command_service.async_unmute()

    async def async_volume_up(self) -> None:
        await self.command_service.async_volume_up()

    async def async_volume_down(self) -> None:
        await self.command_service.async_volume_down()

    async def async_volume_set(self, _vol) -> None:
        await self.command_service.async_set_volume(_vol)

    async def async_set_mute(self, mute) -> None:
        # await self._device.async_turn_on()
        if mute:
            await self.command_service.async_mute()
        else:
            await self.command_service.async_unmute()

    async def async_send_command(self, command, value):
        # await self.command_service.async_connect()

        match command:
            case "Power On":
                await self.command_service.async_send_command(CMD_POWER_ON)
            case "Power Off":
                await self.command_service.async_send_command(CMD_POWER_OFF)
            case "Mute":
                await self.command_service.async_send_command(CMD_MUTE)
            case "UnMute":
                await self.command_service.async_send_command(CMD_UNMUTE)
            case "Volume Up":
                await self.command_service.async_send_command(CMD_VOLUME_UP)
            case "Volume Down":
                await self.command_service.async_send_command(CMD_VOLUME_DOWN)
            case "Source Up":
                await self.command_service.async_source_up()
            case "Source Down":
                await self.command_service.async_source_down()
            case "Set Sound Field":
                if value is None:
                    _LOGGER.error("You must specific a sound field")
                    return
                await self.async_set_mode(value)
            case "Set Source":
                if value is None:
                    _LOGGER.error("You must specific a source")
                    return
                if value not in SOURCE_MENU_MAP.values():
                    _LOGGER.error('Sound field "%s" is not a valid sound field' % value)
                    return
                await self.async_set_source(value)
            case "Set Volume":
                await self.async_volume_set(value)
            case "Byte Array String":
                _byte_command = bytes.fromhex(value)
                await self.command_service.async_send_command(_byte_command)

    def set_update_cb(self, cb):
        self._update_cb = cb

    def set_remote_update_cb(self, cb):
        self._remote_update_cb = cb

    def set_sensor_update_cb(self, cb):
        self._sensor_update_cb = cb

    async def async_update_status(self):
        _LOGGER.debug("Updating Initial Status")
        await self.async_poll_state()

    async def run_notifier(self):
        _LOGGER.debug("Setting up Sony AVR Notify Listener")
        await self.feedback_watcher.run()

    async def stop_notifier(self):
        _LOGGER.debug("Stopping Sony AVR Notify Listener")
        await self.feedback_watcher.stop()

    async def run_ping_watcher(self):
        _LOGGER.debug("Setting up Ping Watcher")
        await self.ping_watcher.start()

    async def stop_ping_watcher(self):
        _LOGGER.debug("Stopping Ping Watcher")
        await self.ping_watcher.stop()

    @property
    def sources(self):
        return tuple(SOURCE_MENU_MAP.values())

    @property
    def source(self):
        if self.state_service.source:
            return SOURCE_MENU_MAP[self.state_service.source]
        else:
            return ""

    @property
    def mode(self):
        if self.state_service.sound_field:
            return SOUND_FIELD_MENU_MAP[self.state_service.sound_field]
        else:
            return ""

    @property
    def modes(self):
        return tuple(SOUND_FIELD_MENU_MAP.values())

    @property
    def volume(self):
        return self.state_service.volume

    @property
    def volume_min(self):
        return self.state_service.volume_min

    @property
    def volume_max(self):
        return self.state_service.volume_max

    @volume_max.setter
    def volume_max(self, value):
        self.state_service.volume_max = value
        self.state_service.volume_range = (
            self.state_service.volume_max - self.state_service.volume_min
        )
        _LOGGER.debug(
            "Set Max Volume: %d and Volume Range: %d",
            value,
            self.state_service.volume_range,
        )

    @property
    def volume_range(self):
        return self.state_service.volume_range

    @property
    def mute(self):
        return self.state_service.muted

    async def async_set_source(self, source):
        if source not in SOURCE_MENU_MAP.values():
            _LOGGER.error('Source "%s" is not a valid input' % source)
            return

        for key, value in SOURCE_MENU_MAP.items():
            if source == value:
                await self.command_service.async_select_source(key)

    async def async_set_mode(self, source):
        if source not in SOUND_FIELD_MENU_MAP.values():
            _LOGGER.error('Sound field "%s" is not a valid sound field' % source)
            return

        for key, value in SOUND_FIELD_MENU_MAP.items():
            if source == value:
                await self.command_service.async_select_sound_field(key)
