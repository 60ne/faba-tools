# Script Name:  myfaba_upload.py
# Description:  This script allows you to upload custom .wav audio to Faba+ using the Faba Me sharing functionality.
#               The share_id is the string of the last 10 characters of the invite to record link.
#               To generate the invite link from the mobile app:
#                  Faba Me > FABA Me White (or Red/Blue), + Add new track > Invite to record
#                  e.g.: 8K3TzYl2WB for https://studio.myfaba.com/record/8K3TzYl2WB
#
# Note:         Uploaded audio will be stored and processed by the MyFaba cloud.
#               .mp3 files can be converted to .wav as follow:
#                  vlc.exe --sout "#transcode{acodec=s16l,channels=2,samplerate=44100}:std{access=file,mux=wav,dst=audio\test.wav}" audio\test.mp3
#                  ffmpeg -i ./audio/test.mp3 -acodec pcm_s16le -ac 2 -ar 44100 ./audio/test.wav 
#                  
# Usage:        python3 myfaba_upload.py [-h] <share_id> <author> <title> <wav_file>
#                  e.g.: python3 myfaba_upload.py 8K3TzYl2WB "Author Name" "Audio Title"  ./audio/test.wav
#
# Author:       60ne https://github.com/60ne/
# Date:         2025-03-16
# Version:      1.0
#
# This script is provided "as is" without warranty of any kind.
#

import re
import wave
import logging
import argparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, parse_qs

BASE_URL = "https://studio.myfaba.com/record/"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def check_share_id(share_id):
    match = re.search(r"([A-Za-z0-9]{10})$", share_id)
    return match.group(1) if match else None


def load_page(session, share_id):
    url = f"{BASE_URL}{share_id}"
    try:
        response = session.get(url, allow_redirects=False)
        response.raise_for_status()
        
        if response.status_code == 302:
            xsrf_token = session.cookies.get("XSRF-TOKEN")
            myfaba_session = session.cookies.get("myfaba_cms_session")
            location_url = response.headers.get("Location")
            
            if xsrf_token and myfaba_session and location_url:
                logging.info("Loading page")
                return xsrf_token, myfaba_session, location_url
            
        logging.error(f"Unexpected response status: {response.status_code}")
    except requests.RequestException as e:
        logging.error(f"Failed to fetch parameters: {e}")
    return None, None, None


def fetch_parameters(session, xsrf_token, myfaba_session, location_url):
    headers = {"Cookie": f"XSRF-TOKEN={xsrf_token}; myfaba_cms_session={myfaba_session}"}
    try:
        response = session.get(location_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        form = soup.find("form", {"id": "form"})
        
        if form:
            action_url = form["action"]
            query_params = parse_qs(urlparse(action_url).query)
            _token = soup.find("input", {"name": "_token"})
            
            if _token and action_url:
                logging.info("Parameters extracted successfully")
                return action_url, query_params.get("expires", [None])[0], query_params.get("signature", [None])[0], _token["value"]
            
        logging.error("Form or token not found")
    except requests.RequestException as e:
        logging.error(f"Failed to fetch form parameters: {e}")
    return None, None, None, None


def get_wav_duration(wav_path):
    try:
        with wave.open(wav_path, "rb") as wav_file:
            return int(wav_file.getnframes() / float(wav_file.getframerate()))
    except (wave.Error, FileNotFoundError) as e:
        logging.error(f"Error reading WAV file: {e}")
    return None


def upload_wav(session, action_url, xsrf_token, myfaba_session, _token, wav_path, author, title):
    duration = get_wav_duration(wav_path)
    if duration is None:
        logging.error("Invalid .wav file duration. Check .wav file")
        return False
    
    headers = {"Cookie": f"XSRF-TOKEN={xsrf_token}; myfaba_cms_session={myfaba_session}"}
    data = {"_token": _token, "duration": str(duration), "creator": author, "title": title}
    
    try:
        with open(wav_path, "rb") as audio_file:
            files = {"userAudio": ("recorded.wav", audio_file, "audio/wav")}
            response = session.post(action_url, headers=headers, files=files, data=data)
            response.raise_for_status()
            logging.info("Upload successfully completed!")
            logging.info("Check Faba mobile app")
            return True
    except (requests.RequestException, IOError) as e:
        logging.error(f"Upload failed: {e}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Upload custom .wav audio to Faba+ using the Faba Me sharing functionality")
    parser.add_argument("share_id", help="The share_id is the string of the last 10 characters of the invite to record link")
    parser.add_argument("author", help="Author name")
    parser.add_argument("title", help="Audio title")
    parser.add_argument("wav_path", help="Path of .wav file to upload")
    args = parser.parse_args()
    
    share_id = check_share_id(args.share_id)
    if not share_id:
        logging.error("Invalid share_id format")
        exit(1)
    
    session = requests.Session()
    xsrf_token, myfaba_session, location_url = load_page(session, args.share_id)
    
    if xsrf_token and myfaba_session and location_url:
        parsed_url = urlparse(location_url)
        query_params = parse_qs(parsed_url.query)
        expires_timestamp = int(query_params.get('expires', [0])[0])
        expires_datetime = datetime.utcfromtimestamp(expires_timestamp)
        logging.info("share_id valid until: %s", expires_datetime.strftime('%Y-%m-%d %H:%M:%S UTC'))

        action_url, expires, signature, _token = fetch_parameters(session, xsrf_token, myfaba_session, location_url)
        
        if action_url and _token:
            success = upload_wav(session, action_url, xsrf_token, myfaba_session, _token, args.wav_path, args.author, args.title)
            if not success:
                logging.error("Upload failed, try again")


if __name__ == "__main__":
    main()