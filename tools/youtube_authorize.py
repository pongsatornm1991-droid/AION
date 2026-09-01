"""One-time local OAuth consent helper for AION's YouTube uploader.

This writes no credentials to the repository.  It prints only the refresh
token so the operator can place it in a protected GitHub Actions secret.
"""

import argparse
import sys
from pathlib import Path

# Permit direct execution with `python tools/youtube_authorize.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.youtube import YOUTUBE_UPLOAD_SCOPE


def authorize(client_secrets_path):
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(
        client_secrets_path, scopes=[YOUTUBE_UPLOAD_SCOPE]
    )
    credentials = flow.run_local_server(port=0, open_browser=False)
    if not credentials.refresh_token:
        raise RuntimeError("Google did not issue a refresh token; revoke the app and authorize again.")
    return credentials.refresh_token


def main():
    parser = argparse.ArgumentParser(description="Authorize AION to upload to its YouTube channel once.")
    parser.add_argument("--client-secrets", required=True, help="Downloaded OAuth desktop-client JSON path")
    args = parser.parse_args()
    # Deliberately print the token only to this local interactive process.
    print(authorize(args.client_secrets))


if __name__ == "__main__":
    main()
