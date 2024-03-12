import os
import csv
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# If modifying these SCOPES, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


def get_gmail_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    service = build("gmail", "v1", credentials=creds)
    return service


def fetch_emails(service):
    # Call the Gmail API to fetch INBOX
    results = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], q="is:unread", maxResults=10)
        .execute()
    )
    messages = results.get("messages", [])

    if not messages:
        print("No new messages found.")
        return
    print("Message snippets:")
    email_details = []
    for message in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message["id"], format="full")
            .execute()
        )
        payload = msg["payload"]
        headers = payload.get("headers")
        subject = None
        from_email = None
        to_email = None
        for header in headers:
            if header["name"] == "Subject":
                subject = header["value"]
            if header["name"] == "From":
                from_email = header["value"]
            if header["name"] == "To":
                to_email = header["value"]
        snippet = msg["snippet"]
        email_details.append([subject, snippet, from_email, to_email, message["id"]])
        print(
            f"Subject: {subject}",
            f"Snippet: {snippet}",
            f"From: {from_email}",
            f"To: {to_email}",
            sep="\n",
            end="\n\n",
        )

    # Save the emails into a CSV file
    with open("emails.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Subject", "Snippet", "From", "To"])
        writer.writerows(email_details)

    return email_details
