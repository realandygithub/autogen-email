import autogen
from dotenv import load_dotenv
import os
from fetch_emails import get_gmail_service, fetch_emails
from gmail_create_draft import gmail_create_draft
from typing import Optional, Dict, Any

# load environment variables
load_dotenv()


OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

config_list = [
    {
        "model": "gpt-4-turbo-preview",
        "api_type": "openai",
        "api_key": OPENAI_API_KEY,
        "base_url": OPENAI_BASE_URL,
    }
]

llm_config = {
    "timeout": 600,  # 10 minutes
    "config_list": config_list,
    "temperature": 0,
}

# Start logging
logging_session_id = autogen.runtime_logging.start(config={"dbname": "logs.db"})
print("Logging session ID: " + str(logging_session_id))


user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="TERMINATE",
    max_consecutive_auto_reply=20,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"work_dir": "web", "use_docker": "python:3"},
    llm_config=llm_config,
    system_message="""Reply TERMINATE if draft emails have been successfully created and are ready to be reviewed and sent to the respective teams. Otherwise, reply CONTINUE, or the reason why the task is not solved yet.""",
)

task_handler = autogen.UserProxyAgent(
    name="task_handler",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=20,
    code_execution_config={"work_dir": "web", "use_docker": "python:3"},
    llm_config=llm_config,
    system_message="""Execute relevant functions with the given parameters. Return the result to the user. When drafting a reply to an email, make sure to reply to the original email sender.""",
)


inquiry_handler = autogen.AssistantAgent(
    name="inquiry_handler",
    system_message="Expert in answering questions about insurance policies, claims, and other insurance-related topics. Read the inquiry and draft a response to the original email sender by replying the email. The email should be from the original receiver of the original email, and to the original sender of the email, which was in the original email message. Ask the task handler to draft the email.",
    llm_config=llm_config,
)

categorize_handler = autogen.UserProxyAgent(
    name="Categorizer",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=20,
    code_execution_config={"work_dir": "web", "use_docker": "python:3"},
    system_message="""
    You are an email receive bot. You inspect emails retrieved from the email_retriever and categorize them into 4 categories:
    1. Escalations. Any customer feedback, dissatisfaction or complaints, such as delay in claims, bad experiences, etc must be escalated immediately and not categorized otherwise. These are emails that needs human input to instruct next steps, for example complex tasks that requires additional information.  Ask the executor to handle these emails.
    2. Inquiries. These are emails that ask questions about insurance policies, claims, and other insurance-related topics. Ask inquiry_handler to handle these emails.
    3. Claims. These are emails that are related to insurance claims. notify the executor to handle these emails.

    4. No action required. These are emails that do not require any action.
    Suggest the category of the email, and ask the relevant agents to handle the emails accordingly.
    """,
    llm_config=llm_config,
)


@task_handler.register_for_execution()
@categorize_handler.register_for_llm(description="Email retriever")
def fetch_emails_and_mark_as_read():
    service = get_gmail_service()
    return fetch_emails(service)


@task_handler.register_for_execution()
@categorize_handler.register_for_llm(description="Email drafter")
def create_draft_to_reply_email(
    content: str,
    to: str,
    from_: str,
    subject: str,
    reply_to: Optional[str] = None,
    reply: Optional[bool] = False,
) -> Dict[str, Any]:
    return gmail_create_draft(content, to, from_, subject, reply_to, reply)


@task_handler.register_for_execution()
@inquiry_handler.register_for_llm(description="Email drafter")
def create_draft(
    content: str,
    to: str,
    from_: str,
    subject: str,
    reply_to: Optional[str] = None,
    reply: Optional[bool] = False,
) -> Dict[str, Any]:
    return gmail_create_draft(content, to, from_, subject, reply_to, reply)


autogen.agentchat.register_function(
    fetch_emails_and_mark_as_read,
    caller=categorize_handler,
    executor=task_handler,
    description="Retrieve emails",
)

autogen.agentchat.register_function(
    create_draft,
    caller=categorize_handler,
    executor=task_handler,
    description="Draft emails",
)
autogen.agentchat.register_function(
    create_draft,
    caller=inquiry_handler,
    executor=task_handler,
    description="Draft emails",
)


groupchat = autogen.GroupChat(
    agents=[user_proxy, inquiry_handler, task_handler, categorize_handler],
    messages=[],
    max_round=12,
)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

task = """
retrieve emails from the gmail inbox. Ask categorize_handler to handle the emails accordingly.
"""

manager.initiate_chat(
    categorize_handler,
    message=task,
)

autogen.runtime_logging.stop()
