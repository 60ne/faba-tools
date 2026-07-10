# Script Name:  myfaba_upload.py
# Description:  This script allows you to upload custom .wav audio to Faba+ using the Faba Me
#               "Invite to Record" sharing functionality.
#
#               MyFaba Studio invite links now look like:
#                  https://studio.myfaba.com/<lang>/invites/<invitePublicId>?token=<jwt>
#               e.g.: https://studio.myfaba.com/it/invites/b92b4a71-19c7-486a-8114-9bdd1e6fe886?token=eyJ...
#
#               Pass either the full URL or just the <invitePublicId> and <token> separately.
#
# Note:         Uploaded audio will be stored and processed by the MyFaba cloud.
#               .mp3 files can be converted to .wav as follow:
#                  vlc.exe --sout "#transcode{acodec=s16l,channels=2,samplerate=44100}:std{access=file,mux=wav,dst=audio\test.wav}" audio\test.mp3
#                  ffmpeg -i ./audio/test.mp3 -acodec pcm_s16le -ac 2 -ar 44100 ./audio/test.wav
#
# Usage:        python3 myfaba_upload.py [-h] <invite_url_or_id> <author> <title> <wav_file> [-t TOKEN]
#                  e.g.: python3 myfaba_upload.py "https://studio.myfaba.com/it/invites/<id>?token=<jwt>" "Author Name" "Audio Title" ./audio/test.wav
#
# Author:       60ne https://github.com/60ne/
# Date:         2025-03-16
# Version:      2.0
#
# This script is provided "as is" without warranty of any kind.
#

import re
import logging
import argparse
import requests
from urllib.parse import urlparse, parse_qs

API_URL = "https://api.myfaba.com/api/v3/studio/invites/{invite_id}/recordings"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def parse_invite(invite_arg, token_arg):
    """Accepts either a full invite URL (with ?token=...) or a bare invitePublicId + separate token."""
    if invite_arg.startswith("http"):
        parsed = urlparse(invite_arg)
        match = UUID_RE.search(parsed.path)
        if not match:
            return None, None
        invite_id = match.group(0)
        token = parse_qs(parsed.query).get("token", [None])[0]
        return invite_id, token

    invite_id = invite_arg if UUID_RE.fullmatch(invite_arg) else None
    return invite_id, token_arg


def upload_wav(invite_id, token, wav_path, author, title):
    url = API_URL.format(invite_id=invite_id)
    params = {"token": token}
    ext = wav_path.rsplit(".", 1)[-1].lower()
    mime = {"wav": "audio/wav", "mp3": "audio/mpeg"}.get(ext, "application/octet-stream")

    try:
        with open(wav_path, "rb") as audio_file:
            files = {"audio": (f"recording.{ext}", audio_file, mime)}
            data = {"title": title}
            if author:
                data["creator"] = author

            response = requests.post(url, params=params, files=files, data=data)
    except (requests.RequestException, IOError) as e:
        logging.error(f"Upload failed: {e}")
        return False

    try:
        payload = response.json()
    except ValueError:
        logging.error(f"Upload failed: unexpected response ({response.status_code}): {response.text[:300]}")
        return False

    if response.status_code >= 200 and response.status_code < 300 and payload.get("success"):
        logging.info("Upload successfully completed!")
        logging.info("Check Faba mobile app")
        return True

    logging.error(f"Upload failed: {payload.get('error')} - {payload.get('message')}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Upload custom .wav audio to Faba+ using the Faba Me sharing functionality")
    parser.add_argument("invite", help="Full invite URL (https://studio.myfaba.com/<lang>/invites/<id>?token=<jwt>) or bare invitePublicId")
    parser.add_argument("author", help="Author name")
    parser.add_argument("title", help="Audio title")
    parser.add_argument("wav_path", help="Path of .wav file to upload")
    parser.add_argument("-t", "--token", help="JWT token, required if 'invite' is a bare invitePublicId rather than a full URL")
    args = parser.parse_args()

    invite_id, token = parse_invite(args.invite, args.token)
    if not invite_id or not token:
        logging.error("Could not determine invitePublicId/token. Pass the full invite URL, or invitePublicId with -t TOKEN.")
        exit(1)

    logging.info(f"Uploading to invite {invite_id}")
    success = upload_wav(invite_id, token, args.wav_path, args.author, args.title)
    if not success:
        exit(1)


if __name__ == "__main__":
    main()
