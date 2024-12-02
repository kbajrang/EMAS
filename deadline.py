from langchain_groq import ChatGroq
import os
import datetime
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import tiktoken  # To calculate token usage

# Load environment variables
load_dotenv()

# Set API keys
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

# Initialize the LLM client
llm_client = ChatGroq(api_key=groq_api_key, model_name="llama3-8b-8192")


def start_fetching_deadline(email_list):
    """Start processing deadlines from the given email list."""
    processed_emails = process_emails_with_llm(email_list, llm_client)
    return processed_emails


def process_emails_with_llm(email_list, llm_client):
    """
    Process emails to extract deadlines using the LLM.
    
    :param email_list: List of emails with 'subject' and 'body'.
    :param llm_client: The LLM client to process emails.
    :return: A list of processed emails with extracted deadlines.
    """
    # Get the current date
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    print(f"Processing emails for the date: {date}")

    # Create a ChatPromptTemplate to manage the prompt structure
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful AI email alert and automation bot. Today is {date}. Your specialty is {specialty}."),
            ("user", (
                "For the email below, respond with any deadlines in this format:\n"
                "- Date: YYYY-MM-DD\n"
                "- Task: Brief task description\n"
                "- Urgency: High/Medium/Low (if applicable)\n\n"
                "Subject: {subject}\nBody: {body}"
            ))
        ]
    )

    # Chain the prompt template with the LLM client
    chain = prompt_template | llm_client

    processed_emails = []

    # Limit input size
    max_body_length = 500
    max_subject_length = 100
    batch_size = 5  # Process in batches to avoid large token requests

    # Iterate through emails in batches
    for i in range(0, len(email_list), batch_size):
        batch = email_list[i:i + batch_size]
        for email in batch:
            # Truncate email body and subject to avoid token overflow
            trimmed_body = email['body'][:max_body_length] + "..." if len(email['body']) > max_body_length else email['body']
            trimmed_subject = email['subject'][:max_subject_length] + "..." if len(email['subject']) > max_subject_length else email['subject']

            try:
                # Generate prompt by filling in the subject and body of each email
                llm_response = chain.invoke({
                    'specialty': 'Extract deadlines and format them as per user requirements.',
                    'subject': trimmed_subject,
                    'body': trimmed_body,
                    'date': date
                })

                # Extract response text
                response_text = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

                processed_emails.append({
                    'id': email['id'],
                    'subject': email['subject'],
                    'deadlines': response_text
                })

            except Exception as e:
                print(f"Error processing email {email['id']}: {str(e)}")
                processed_emails.append({
                    'id': email['id'],
                    'subject': email['subject'],
                    'deadlines': "Error processing this email."
                })

    return processed_emails


# Optional: Debugging token usage (for troubleshooting)
def calculate_token_usage(text):
    """Calculate token usage for a given text."""
    encoding = tiktoken.get_encoding("gpt-3.5-turbo")  # Adjust model name
    tokens = encoding.encode(text)
    return len(tokens)
