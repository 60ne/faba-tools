# Script Name:  faba_ntag.py
# Description:  This script allows to read, write, erase NTAG compatible with Faba+
#       
# Usage:        python3 faba_ntag.py [-h] [-r | -w ID | -d | -e] [-c UID TYPE ID] [-p PORT] [-v]
#
# Author:       60ne https://github.com/60ne/
# Date:         2025-06-07
# Version:      0.9
#
# This script is provided "as is" without warranty of any kind.
#

# Adafruit PN532 RFID/NFC Shield
#
#  +=======+======+
#  | PN532 | FTDI |
#  +=======+======+
#  | GND   | GND  |
#  +-------+------+
#  | VCC   | 5V   |
#  +-------+------+
#  | MOSI  | RX   |
#  +-------+------+
#  | SS    | TX   |
#  +-------+------+
#
#
# Elechouse NFC Module v3
#
#  +=======+======+        DIP Switch HSU:
#  | PN532 | FTDI |        
#  +=======+======+        +======+=====+=====+
#  | GND   | GND  |        | Mode | SW1 | SW2 |
#  +-------+------+        +======+=====+=====+
#  | VCC   | 3V3  |        | HSU  |  0  |  0  |
#  +-------+------+        +------+-----+-----+
#  | SDA   | RX   |        | I2C  |  1  |  0  |
#  +-------+------+        +------+-----+-----+
#  | SCL   | TX   |        | SPI  |  0  |  1  |
#  +-------+------+        +------+-----+-----+
#


import re
import time
import string
import serial
import logging
import argparse
import binascii
import serial.tools.list_ports
from adafruit_pn532.uart import PN532_UART

VALID_TAG_TYPES = {"NTAG203", "NTAG213", "NTAG215", "NTAG216"}

class NTAGData:
    def __init__(self):
        self.pages = {}
        self.uid = None
        self.type = "Unknown"
        self.size = 0

    def add_page(self, page, data):
        self.pages[page] = data

    #def print_pages(self):
    #    print(f"")
    #    print(f"Page ##:  HEX          |  ASCII")
    #    print(f"--------  -----------     -----")
    #    for page, data in sorted(self.pages.items()):
    #        hex_part = ' '.join(f'{byte:02X}' for byte in data)
    #        ascii_part = ''.join(chr(byte) if chr(byte) in string.printable and byte >= 0x20 else '.' for byte in data)
    #        print(f"Page {page:02X}:  {hex_part:<12} |  {ascii_part}")

    def read_page(self, page_number):
        if page_number in self.pages:
            page_data = self.pages[page_number]
            return page_data
        else:
            print(f"Page {page_number} not found.")
            return None
    
    def get_all_bytes(self):
        all_data = bytearray()
        for page in sorted(self.pages):
            all_data.extend(self.pages[page])
        return all_data


def init_pn532(port):
    try:
        serial_port = serial.Serial(port, baudrate=115200, timeout=1)
        pn532 = PN532_UART(serial_port, debug=False)
        ic, ver, rev, support = pn532.firmware_version
        logging.info(f"Found PN532 with firmware version: {ver}.{rev}")
        pn532.SAM_configuration()
        return pn532
    except Exception as e:
        logging.error(f"Error initializing PN532: {e}")
        return None


def wait_for_card(pn532):
    logging.info("Waiting for NTAG card...")
    while True:
        uid = pn532.read_passive_target(timeout=0.5)
        #print(".", end=" ", flush=True)
        if uid:
            logging.info(f"  UID:    {' '.join([f'{byte:02X}' for byte in uid])}")
            return uid


def detect_card(pn532, ntag):
    ntag.uid = wait_for_card(pn532)

    # Read all pages
    page = 0
    while True:
        data = read_page(pn532, page)
        if not data:
            break
        ntag.add_page(page, data)
        page = page + 1
    
    cc_byte = ntag.read_page(3)[2]
    #logging.debug(f"  Capability Container (CC) byte: 0x{cc_byte:02X}")
    
    # Verify CC and total pages identified
    if cc_byte == 0x12:
        if page == 42:
            ntag.type = "NTAG203"
        elif page == 45:
            ntag.type = "NTAG213"
        else:
            page = 45; # Force page size
            ntag.type = "NTAG213" # NTAG213 Clone
    elif cc_byte == 0x3E:
        if page == 135:
            ntag.type = "NTAG215"
        else:
            page = 135; # Force page size
            ntag.type = "NTAG215" # NTAG215 Clone  
    elif cc_byte == 0x6D:
        if page == 231:
            ntag.type = "NTAG216"
        else:
            page = 231; # Force page size
            ntag.type = "NTAG216" # NTAG216 Clone   
    else:
        ntag.type = "Unknown"
    
    ntag.size = page
    logging.info(f"  Type:   {ntag.type} [CC: 0x{cc_byte:02X}]")
    logging.info(f"  Pages:  {ntag.size}")
    return True


def read_page(pn532, page):
    try:
        data = pn532.ntag2xx_read_block(page)
        return data

    except Exception as e:
        logging.warning(f"Error reading page {page}: {e}")
        return None


def parse_text(ntag):
    # Read page 6
    page6 = ntag.read_page(6)
    if page6 is None:
        logging.error("Failed to read Page 6")
        return

    # Parse header
    ndef_header    = page6[0]  # 01 - NDEF record header
    payload_length = page6[1]  # 11 - Payload length (17 bytes)
    type_field     = page6[2]  # 54 - 'T' for Text Record
    status_byte    = page6[3]  # 02 - Status byte (lang length = 2)
    
    logging.debug(f"  Header:   0x{ndef_header:02X} [0x01]")
    logging.debug(f"  Payload:  0x{payload_length:02X} [0x11]")
    logging.debug(f"  Type:     0x{type_field:02X} [0x54]")
    logging.debug(f"  Status:   0x{status_byte:02X} [0x02]")

    if type_field != 0x54:
        logging.info(f"No text record found [0x{type_field:02X}]")
        #return

    lang_length = status_byte & 0x3F  # Mask out encoding bit
    encoding = "UTF-16" if (status_byte & 0x80) else "UTF-8"

    # Read next pages to get full payload
    full_payload = []
    next_page = 7
    remaining_bytes = payload_length

    while remaining_bytes > 0:
        page_data = ntag.read_page(next_page)
        if page_data is None:
            logging.debug(f"Page {next_page} missing, stopping read")
            break

        for byte in page_data:
            if remaining_bytes == 0 or byte == 0xFE:  # Stop at payload_length or terminator TLV
                break
            full_payload.append(byte)
            remaining_bytes -= 1

        next_page += 1

    # Extract language code and text content
    if len(full_payload) < lang_length:
        logging.error("Invalid NDEF record: insufficient data for language code")
        return

    lang_code = bytes(full_payload[:lang_length]).decode("ascii")  # Language code
    text_content = bytes(full_payload[lang_length:]).decode(encoding)  # Extract text

    logging.debug(f"NTAG content:")
    logging.debug(f"  Encoding: {encoding}")
    logging.debug(f"  Language: {lang_code}")
    logging.debug(f"  Text:     {text_content}")
    if text_content.startswith("02190530") and len(text_content) >= 12:
        extracted_id = text_content[8:12]  # Extract next 4 digits
        ntag.code = extracted_id
        logging.info(f"  FabaID: {ntag.code}")
    else:
        logging.info("No valid Faba folder ID found")


def create_byte_array(input_str, ntag):

    size_to_mlen = {
        42:  0x6D,  # NTAG203
        45:  0xA0,  # NTAG213
        135: 0xE0,  # NTAG215
        231: 0xFA   # NTAG216
    }

    # Get MLen based on size, default to 0xA0 (NTAG213)
    mlen = size_to_mlen.get(ntag.size, 0xA0)

    page04 = [0x01, 0x03, mlen, 0x0C]
    page05 = [0x34, 0x03, 0x15, 0xD1]
    page06 = [0x01, 0x11, 0x54, 0x02]  # Fixed for FabaID
    page11 = [0xFE, 0x00, 0x00, 0x00]
    
    # Pages 00-03
    pages0_3 = []
    for i in range(4):  
        page = ntag.read_page(i)
        if page is not None and len(page) == 4:
            pages0_3.extend(page)
        else:
            pages0_3.extend([0x00] * 4) # Default empty
    
    # Pages 07-10
    if input_str:
        hex_data = input_str.encode('utf-8').hex()
        pages7_10 = [int(hex_data[i:i+2], 16) for i in range(0, len(hex_data), 2)]
    
    else:
        pages7_10 = []
        for i in range(7, 11):
            page = ntag.read_page(i)
            if page is not None and len(page) == 4:
                pages7_10.extend(page)
            else:
                pages7_10.extend([0x00] * 4) # Default empty
    
    # Create default values array
    last5 = [0x00, 0x00, 0x00, 0xBD,
             0x04, 0x00, 0x00, 0xFF,
             0x00, 0x00, 0x00, 0x00,
             0x00, 0x00, 0x00, 0x00,
             0x00, 0x00, 0x00, 0x00]
    
    byte_array = pages0_3 + page04 + page05 + page06 + pages7_10 + page11 + [0x00] * (ntag.size - 17) * 4 + last5
    #byte_array = [0x00] * 16 + page04 + page05 + page06 + [int(hex_data[i:i+2], 16) for i in range(0, len(hex_data), 2)] + page11
    return byte_array


def print_byte_array(byte_array):
    logging.debug(" ")
    logging.debug("Content:")
    logging.debug(" ")
    logging.debug(f"Page       HEX          |  ASCII")
    logging.debug(f"---------  -----------  |  -----")
    for i in range(0, len(byte_array), 4):
        chunk = byte_array[i:i+4]
        hex_part = ' '.join(f'{byte:02X}' for byte in chunk)
        ascii_part = ''.join(chr(byte) if chr(byte) in string.printable and byte >= 0x20 else '.' for byte in chunk)
        logging.debug(f"Page {i//4:03d}:  {hex_part:<12} |  {ascii_part}")


def encode_faba_id(id):
    text = "en02190530" + id + "00"
    return text


def read_ntag(ntag):
    parse_text(ntag)


def write_ntag(pn532, id, ntag):
    logging.info(f"Writing tag with UID: {' '.join([f'{byte:02X}' for byte in ntag.uid])}")
    logging.info(f"FabaID: {id}")
    text = encode_faba_id(id)
    logging.debug(f" Encoded FabaID: {text}")
    byte_array = create_byte_array(text, ntag)
    print_byte_array(byte_array)
    if write_blocks(pn532, byte_array, 4, 11, ntag):
        if verify_blocks(pn532, byte_array, 4, 11):
            logging.info("NTAG successfully written")
            # Dump content
            dump_ntag(byte_array, ntag)


def write_blocks(pn532, byte_array, start, end, ntag):
    logging.debug(" ")
    logging.debug("Write:")
    logging.debug(" ")
    logging.debug(f"Page       HEX          |  Status")
    logging.debug(f"---------  -----------  |  ------")
    uid = pn532.read_passive_target(timeout=0.5)
    
    if uid == ntag.uid:
        for block_num in range(start, end + 1):
            start_idx = block_num * 4
            end_idx = start_idx + 4
            block_data = byte_array[start_idx:end_idx]
            
            try:
                wr = pn532.ntag2xx_write_block(block_num, block_data)
                logging.debug(f"Page {block_num:03d}:  " + " ".join([f"{byte:02X}" for byte in block_data]) + f"  |  {wr}")
                if wr == False:
                    logging.error(f"Failed writing page {block_num}")
                    return False
            except Exception as e:
                logging.error(f"Error writing page {block_num}: {e}")
                return False
    
    else:
        logging.error(f"UID not matching initial read")
        return False
    
    return True


def verify_blocks(pn532, byte_array, start, end):
    logging.debug(" ")
    logging.debug("Verify:")
    logging.debug(" ")
    logging.debug(f"Page       Expected     ::  Read")
    logging.debug(f"---------  -----------  ::  -----------")
    for block_num in range(start, end + 1):
        start_idx = block_num * 4
        end_idx = start_idx + 4
        expected_data = byte_array[start_idx:end_idx]

        read_data = read_page(pn532, block_num)
        if read_data is None:
            logging.error(f"Error: Failed to read page {block_num}")
            return False

        # Convert both expected data and read data to hex strings
        expected_hex = " ".join([f"{byte:02X}" for byte in expected_data])
        read_hex = " ".join([f"{byte:02X}" for byte in list(read_data)])
        logging.debug(f"Page {block_num:03d}:  {expected_hex}  ::  {read_hex}")
        

        if expected_hex != read_hex:
            logging.error(f"Mismatch at page {block_num}: expected {expected_hex}, got {read_hex}")
            return False
    
    return True


def erase_ntag(pn532, ntag):
    logging.info("Erasing NTAG")
    logging.info(f"  UID :   {' '.join([f'{byte:02X}' for byte in ntag.uid])}")
    logging.info(f"  Type:   {ntag.type}")
    
    # NTAG203 and NTAG213
    if ntag.type == "NTAG203" or ntag.type == "NTAG213":
        page04 = [0x01, 0x03, 0xA0, 0x0C]
        page05 = [0x34, 0x03, 0x00, 0xFE]      
       
    # NTAG215 and NTAG216 
    if ntag.type == "NTAG215" or ntag.type == "NTAG216":
        page04 = [0x03, 0x00, 0xFE, 0x00]
        page05 = [0x00, 0x00, 0x00, 0x00]
    
    # Unknown
    if ntag.type == "Unknown":
        page04 = [0x00, 0x00, 0x00, 0x00]
        page05 = [0x00, 0x00, 0x00, 0x00] 

    # Create default values array
    last5 = [0x00, 0x00, 0x00, 0xBD,
             0x04, 0x00, 0x00, 0xFF,
             0x00, 0x00, 0x00, 0x00,
             0x00, 0x00, 0x00, 0x00,
             0x00, 0x00, 0x00, 0x00]
    
    erase = [0x00] * 16 + page04 + page05 + [0x00] * (ntag.size - 11) * 4 + last5
    print_byte_array(erase)
    if write_blocks(pn532, erase, 4, ntag.size - 1, ntag):
        if verify_blocks(pn532, erase, 4, ntag.size - 1):
            logging.info("NTAG successfully erased") 


def dump_ntag(byte_array, ntag):
    if len(byte_array) > 43:
        filename_bytes = byte_array[38:42]
        filename = ''.join(chr(byte) if chr(byte) in string.printable and byte >= 0x20 else '' for byte in filename_bytes)

        if filename == "": # If empty, use UID
            filename = ''.join([f'{byte:02X}' for byte in ntag.uid])
        
        logging.info(f"Saving files")

        save_raw(byte_array, filename)
        save_ndef(byte_array, filename)
        save_flipper(byte_array, ntag, filename)


def crete_ntag(uid, type, id):
    logging.info(f"  UID:    {' '.join([f'{byte:02X}' for byte in uid])}")
    logging.info(f"  Type:   {type}")
    logging.info(f"  FabaID: {id}")

    if len(uid) != 7:
        raise ValueError("UID must be exactly 7 bytes")

    CT = 0x88 # Cascade tag fixed byte
    bcc0 = CT ^ uid[0] ^ uid[1] ^ uid[2]
    bcc1 = uid[3] ^ uid[4] ^ uid[5] ^ uid[6]

    page00 = [uid[0], uid[1], uid[2], bcc0]
    page01 = [uid[3], uid[4], uid[5], uid[6]]
    page02 = [bcc1, 0x48, 0x00, 0x00]

    ntag_specs = {
        "NTAG203": {"capc": 0x12, "mlen": 0x6D, "ntag_size": 42},
        "NTAG213": {"capc": 0x12, "mlen": 0xA0, "ntag_size": 45},
        "NTAG215": {"capc": 0x3E, "mlen": 0xE0, "ntag_size": 135},
        "NTAG216": {"capc": 0x6D, "mlen": 0xFA, "ntag_size": 231},
    }

    if type not in ntag_specs:
        raise ValueError(f"Unsupported tag type: {type}")

    spec = ntag_specs[type]

    page03 = [0xE1, 0x10, spec["capc"], 0x00]
    page04 = [0x01, 0x03, spec["mlen"], 0x0C]
    
    # Create NTAGData instance and assign properties
    ntag = NTAGData()
    ntag.uid = uid
    ntag.type = type
    ntag.size = spec["ntag_size"]
    ntag.add_page(0, page00)
    ntag.add_page(1, page01)
    ntag.add_page(2, page02)
    ntag.add_page(3, page03)
    ntag.add_page(4, page04)

    text = encode_faba_id(id)
    logging.debug(f" Encoded FabaID: {text}")
    byte_array = create_byte_array(text, ntag)
    print_byte_array(byte_array)
    dump_ntag(byte_array, ntag)


def save_raw(byte_array, filename):
    filename = f"{filename}.raw"

    try:
        lines = []

        for i in range(0, len(byte_array), 4):
            chunk = byte_array[i:i+4]
            if len(chunk) < 4:
                chunk += [0] * (4 - len(chunk))  # Pad incomplete pages
            hex_part = ''.join(f'{byte:02X}' for byte in chunk)
            lines.append(f"{hex_part:<8}")


        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logging.info(f"  RAW             : {filename}")
        return True

    except OSError as e:
        logging.error(f"Failed to write file {filename}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

    return False


def save_ndef(byte_array, filename):
    ndef_bytes = byte_array[23:44]
    hex_string = ''.join(f'{byte:02x}' for byte in ndef_bytes)

    filename = f"{filename}.ndef"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"<NdefMessage>{hex_string}</NdefMessage>")
        logging.info(f"  NDEF            : {filename}")
        return True
        
    except OSError as e:
        logging.error(f"Failed to write to file {filename}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

    return False


def save_flipper(byte_array, ntag, filename):
    filename = f"{filename}.nfc"

    try:
        lines = [
            "Filetype: Flipper NFC device",
            "Version: 4",
            "# Device type can be ISO14443-3A, ISO14443-3B, ISO14443-4A, ISO14443-4B, ISO15693-3, FeliCa, NTAG/Ultralight, Mifare Classic, Mifare Plus, Mifare DESFire, SLIX, ST25TB, EMV",
            "Device type: NTAG/Ultralight",
            "# UID is common for all formats",
            f"UID: {' '.join(f'{byte:02X}' for byte in ntag.uid)}",
            "# ISO14443-3A specific data",
            "ATQA: 00 44",
            "SAK: 00",
            "# NTAG/Ultralight specific data",
            "Data format version: 2",
            f"NTAG/Ultralight type: {ntag.type}",
            "Signature:" + " 00" * 32,
            "Mifare version: 00 53 04 02 01 00 0F 03",
            "Counter 0: 0",
            "Tearing 0: 00",
            "Counter 1: 0",
            "Tearing 1: 00",
            "Counter 2: 0",
            "Tearing 2: 00",
            f"Pages total: {ntag.size}",
            f"Pages read: {ntag.size}",
        ]

        for i in range(0, len(byte_array), 4):
            chunk = byte_array[i:i+4]
            if len(chunk) < 4:
                chunk += [0] * (4 - len(chunk))  # Pad incomplete pages
            hex_part = ' '.join(f'{byte:02X}' for byte in chunk)
            lines.append(f"Page {i//4}: {hex_part:<11}")

        lines.append("Failed authentication attempts: 0")

        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logging.info(f"  Flipper Zero NFC: {filename}")
        return True

    except OSError as e:
        logging.error(f"Failed to write file {filename}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

    return False


def main():
    try:
        parser = argparse.ArgumentParser(
            description="Read, write, erase, dump or create NTAG2xx data with FabaID",
            add_help=True
        )

        # Exclusive group: read/write/dump/erase
        nfc_ops = parser.add_mutually_exclusive_group()

        nfc_ops.add_argument("-r", "--read", action="store_true", help="Read NTAG and decode Faba folder ID")
        nfc_ops.add_argument("-w", "--write", metavar="ID", type=str, help="Write NTAG with Faba folder ID (4-digit ID)")
        nfc_ops.add_argument("-d", "--dump", action="store_true", help="Dump NTAG content and save to Flipper Zero (.nfc) and NXP TagWriter (.ndef)")
        nfc_ops.add_argument("-e", "--erase", action="store_true", help="Erase NTAG restoring default values")

        # Create option outside the group so we can enforce exclusivity manually
        parser.add_argument("-c", "--create", nargs=3, metavar=("UID", "TYPE", "ID"), help="Create manually Flipper Zero (.nfc) file. Requires UID (7-byte hex), TYPE (NTAG203/213/215/216), ID (4-digit)")

        parser.add_argument("-p", "--port", metavar="PORT", type=str, help="NFC reader serial port (e.g. COM1 or /dev/ttyUSB0)")
        parser.add_argument("-v", action="store_true", help="Enable debug logging")

        args = parser.parse_args()

        # Set up logging
        logging_level = logging.DEBUG if args.v else logging.INFO
        logging.basicConfig(level=logging_level, format='%(levelname)s: %(message)s')

        # Validate mutual exclusivity
        if args.create and (args.read or args.write or args.dump or args.erase):
            logging.error("Option --create (-c) cannot be used with -r, -w, -e, or -d")
            return False

        # Handle --create mode
        if args.create:
            uid_str, tag_type, tag_id = args.create

            # Validate UID (must be 14 hex chars representing 7 bytes)
            if not re.fullmatch(r"[0-9a-fA-F]{14}", uid_str):
                logging.error("UID must be a 7-byte hexadecimal string (14 hex characters, e.g., '04742FF1780000')")
                return False

            uid = [int(uid_str[i:i+2], 16) for i in range(0, 14, 2)]

            # Validate type
            if tag_type.upper() not in VALID_TAG_TYPES:
                logging.error(f"Invalid tag type '{tag_type}'. Must be one of: {', '.join(VALID_TAG_TYPES)}")
                return False

            # Validate ID
            if not re.fullmatch(r"\d{4}", tag_id):
                logging.error("ID must be a 4-digit number")
                return False
            
            crete_ntag(uid, tag_type, tag_id)

            return True


        # Non-create mode requires port
        if not args.port:
            logging.error("Serial port (-p) is required")
            return False

        ports = [port.device for port in serial.tools.list_ports.comports()]
        if args.port not in ports:
            logging.error(f"Serial port '{args.port}' not found.")
            logging.info("Available serial ports:")
            for port in ports:
                print(f"   {port}")
            return False

        # Initialize NFC reader
        pn532 = init_pn532(args.port)
        if not pn532:
            logging.error("Failed to initialize PN532.")
            return False

        # Initialize NTAG data and detect card
        ntag = NTAGData()
        if not detect_card(pn532, ntag):
            logging.error("No NTAG detected or failed to read card.")
            return False

        # Read NTAG
        if args.read:
            read_ntag(ntag)

        # Write NTAG
        elif args.write:
            if re.fullmatch(r"\d{4}", args.write):
                write_ntag(pn532, args.write, ntag)
            else:
                logging.error("Invalid ID format. Must be a 4-digit number (e.g., '1234').")
                return False

        # Dump NTAG
        elif args.dump:
            try:
                byte_array = ntag.get_all_bytes()
                dump_ntag(byte_array, ntag)
            except Exception as e:
                logging.error(f"Failed to dump NTAG data: {e}")
                return False

        # Erase NTAG
        elif args.erase:
            erase_ntag(pn532, ntag)

    except KeyboardInterrupt:
        logging.warning("Interrupted by user.")
        return False

    except Exception as e:
        logging.exception(f"Unexpected error occurred: {e}")
        return False


if __name__ == "__main__":
    main()
