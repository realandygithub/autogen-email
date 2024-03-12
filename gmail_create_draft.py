import base64
from typing import Optional, Dict, Any
import textwrap
from googleapiclient.errors import HttpError
from fetch_emails import get_gmail_service
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def gmail_create_draft(
    content: str,
    to: str,
    from_: str,
    subject: str,
    original_message_id: str,
    reply: Optional[bool] = True,
) -> Dict[str, Any]:
    """Create and insert a draft email.
    Print the returned draft's message and id.
    Returns: Draft object, including draft id and message meta data.
    """

    try:
        # create gmail api client
        service = get_gmail_service()

        message = MIMEMultipart("alternative")
        create_message = {"message": {}}

        if reply and original_message_id:
            # Get the original message
            original_message = (
                service.users()
                .messages()
                .get(userId="me", id=original_message_id)
                .execute()
            )

            print(f"Original message: {original_message}")
            thread_id = original_message["threadId"]

            # Get the content of the original message
            original_content = original_message["payload"]["parts"][0]["body"]["data"]
            original_content = base64.urlsafe_b64decode(original_content).decode()

            # Get the date, time, and sender's email from the original message
            headers = original_message["payload"]["headers"]
            date = next(
                header["value"] for header in headers if header["name"] == "Date"
            )
            sender = next(
                header["value"] for header in headers if header["name"] == "From"
            )

            # Add the thread ID to the draft message
            create_message["message"]["threadId"] = thread_id

            # Indent the original message
            indented_original_content = textwrap.indent(original_content, "> ")

            # Append the original message to the new content
            content += f"\n\nOn {date} {sender} wrote:\n" + indented_original_content

        # Create the plain-text and HTML version of your message
        text_part = MIMEText(content, "plain")

        # The email client will try to render the last part first
        message.attach(text_part)

        message["To"] = to
        message["From"] = from_
        message["Subject"] = subject

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"message": {"raw": encoded_message}}

        # pylint: disable=E1101
        draft = (
            service.users().drafts().create(userId="me", body=create_message).execute()
        )

        print(f'Draft id: {draft["id"]}\nDraft message: {draft["message"]}')

    except HttpError as error:
        print(f"An error occurred: {error}")
        draft = None

    return draft


# def test_draft_email():

#     return gmail_create_draft(
#         "Dear Andy,\n\nWe received your email regarding the car accident and your intention to file a claim. We're truly sorry to hear about your accident and hope that everyone involved is safe.\n\nTo proceed with your claim, we would need the following information:\n- Date and time of the accident\n- Location of the accident\n- A detailed description of the incident\n- Photos of the damage to your vehicle\n- Any police reports filed\n- Contact information for any other parties involved\n\nOnce we have this information, we will be able to move forward with your claim. Please send the required documents at your earliest convenience.\n\nIf you have any questions or need further assistance, please don't hesitate to reach out.\n\nBest regards,\n\n[Your Name]\n[Your Position]\nMagic Insurance",
#         "jiangchen.611@gmail.com",
#         "realandycok9@gmail.com",
#         "Re: Claim",
#         "18e2a59871f60fe9",
#         True,
#     )


# test_draft_email()
