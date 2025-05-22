import smtplib
import yaml
from email.mime.text import MIMEText
from loguru import logger

CONFIG_FILE_PATH = "conf.yaml"

def load_smtp_config():
    """Loads SMTP configuration from conf.yaml."""
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = yaml.safe_load(f)
        smtp_config = config.get("SMTP")
        if not smtp_config:
            logger.error("SMTP configuration not found in conf.yaml.")
            return None
        return smtp_config
    except FileNotFoundError:
        logger.error(f"Configuration file {CONFIG_FILE_PATH} not found.")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML in {CONFIG_FILE_PATH}: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading SMTP config: {e}")
        return None

def send_email(to_address: str, subject: str, body: str) -> bool:
    """
    Sends an email using the SMTP configuration from conf.yaml.

    Args:
        to_address (str): The recipient's email address.
        subject (str): The subject of the email.
        body (str): The body content of the email (plain text).

    Returns:
        bool: True if the email was sent successfully, False otherwise.

    Example:
        To use this function, first ensure your conf.yaml has the SMTP section configured:
        ```yaml
        SMTP:
          HOST: "smtp.example.com"
          PORT: 587
          USE_TLS: True
          USE_SSL: False
          USERNAME: "your_email@example.com"
          PASSWORD: "your_password" # Replace with your actual password
          SENDER_EMAIL: "your_email@example.com"
        ```

        Then you can call the function like this:
        ```python
        # Assuming this code is in a file within the project structure
        # where it can access utils.email_handler and conf.yaml
        # from utils.email_handler import send_email
        #
        # if __name__ == "__main__":
        #     if send_email("recipient@example.com", "Test Subject", "This is a test email body."):
        #         print("Email sent successfully!")
        #     else:
        #         print("Failed to send email.")
        ```
    """
    smtp_config = load_smtp_config()
    if not smtp_config:
        return False

    host = smtp_config.get("HOST")
    port = smtp_config.get("PORT")
    use_tls = smtp_config.get("USE_TLS", False)
    use_ssl = smtp_config.get("USE_SSL", False)
    username = smtp_config.get("USERNAME")
    password = smtp_config.get("PASSWORD")
    sender_email = smtp_config.get("SENDER_EMAIL")

    if not all([host, port, sender_email]):
        logger.error("SMTP configuration is missing required fields (HOST, PORT, SENDER_EMAIL).")
        return False
    
    if password == "your_password" or username == "your_email@example.com":
        logger.warning("Using default placeholder credentials from conf.yaml. Email sending will likely fail.")
        logger.warning("Please update SMTP USERNAME and PASSWORD in conf.yaml with real credentials.")


    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_address

    server = None
    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port)
            logger.info(f"Connecting to SMTP server {host}:{port} using SSL.")
        else:
            server = smtplib.SMTP(host, port)
            logger.info(f"Connecting to SMTP server {host}:{port}.")
            if use_tls:
                logger.info("Starting TLS encryption.")
                server.starttls()
        
        if username and password:
            logger.info(f"Attempting to login as {username}.")
            server.login(username, password)
            logger.info("SMTP login successful.")
        
        server.sendmail(sender_email, to_address, msg.as_string())
        logger.success(f"Email sent successfully to {to_address} with subject '{subject}'.")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication error: {e}. Check username/password in conf.yaml.")
    except smtplib.SMTPServerDisconnected as e:
        logger.error(f"SMTP server disconnected: {e}. Check server address, port, or network.")
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP connection error: {e}. Check server address and port.")
    except smtplib.SMTPHeloError as e:
        logger.error(f"SMTP HELO error: {e}.")
    except smtplib.SMTPRecipientsRefused as e:
        logger.error(f"SMTP recipients refused: {e}. Check recipient email address.")
    except smtplib.SMTPSenderRefused as e:
        logger.error(f"SMTP sender refused: {e}. Check SENDER_EMAIL in conf.yaml.")
    except smtplib.SMTPDataError as e:
        logger.error(f"SMTP data error: {e}.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending email: {e}")
    finally:
        if server:
            try:
                server.quit()
                logger.info("Disconnected from SMTP server.")
            except smtplib.SMTPServerDisconnected:
                logger.warning("Server was already disconnected.") # If starttls fails, server might be disconnected.
            except Exception as e:
                logger.error(f"Error during SMTP server quit: {e}")
    return False

if __name__ == '__main__':
    # This is a simple test block.
    # Ensure conf.yaml is correctly configured before running this.
    # You would typically call send_email from other parts of your application.
    logger.info("Attempting to send a test email (if conf.yaml is configured)...")
    
    # Create a dummy conf.yaml for testing if it doesn't exist or is misconfigured
    # In a real scenario, conf.yaml should be properly set up by the user.
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            yaml.safe_load(f).get("SMTP", {}).get("HOST", "smtp.example.com")
    except (FileNotFoundError, AttributeError, TypeError):
        logger.warning(f"Creating a dummy {CONFIG_FILE_PATH} for testing purposes.")
        dummy_conf_content = """
SMTP:
  HOST: "smtp.example.com"
  PORT: 587
  USE_TLS: True
  USE_SSL: False
  USERNAME: "your_email@example.com"
  PASSWORD: "your_password"
  SENDER_EMAIL: "noreply@example.com"
"""
        with open(CONFIG_FILE_PATH, 'w') as f:
            f.write(dummy_conf_content)

    # Replace with a real recipient for actual testing,
    # but be mindful of sending emails to arbitrary addresses.
    test_recipient = "test_recipient@example.com" 
    
    smtp_settings = load_smtp_config()
    if smtp_settings and smtp_settings.get("HOST") != "smtp.example.com":
        logger.info(f"Found SMTP configuration for {smtp_settings.get('HOST')}.")
        logger.info(f"To run a real email test, ensure USERNAME and PASSWORD are correct in {CONFIG_FILE_PATH}")
        logger.info(f"and change 'test_recipient' in utils/email_handler.py to a valid email address.")

        # Example of how to call it (commented out by default to prevent accidental sends)
        # if send_email(test_recipient, "Test Email from EmailHandler", "Hello! This is a test email sent from the email_handler.py script."):
        #     logger.success("Test email sent successfully (check your inbox and spam folder).")
        # else:
        #     logger.error("Failed to send test email. Check logs for details.")
    else:
        logger.warning(f"SMTP host in {CONFIG_FILE_PATH} is still 'smtp.example.com' or config is missing.")
        logger.warning("Skipping actual email sending test. Please configure SMTP settings in conf.yaml to test.")

    logger.info("Email handler script execution finished.")

# To ensure the utils directory is recognized as a package
# especially if other modules in utils might be added or used later.
# Create an __init__.py file in the utils directory if it doesn't exist.
# This is not strictly necessary for this single file script if run directly,
# but good practice for module structure.
# For now, this file focuses on the send_email functionality.
# If this file were imported by another, the __main__ block would not run.
# Example usage is provided in the docstring of send_email.
