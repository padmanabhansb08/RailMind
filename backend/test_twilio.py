import os
from dotenv import load_dotenv

# Load the environment variables from .env
load_dotenv()

from services.twilio_service import TwilioSMSClient

def test_twilio():
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    
    if sid == "live_twilio_sid" or token == "live_twilio_token":
        print("❌ Error: Please update your TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in backend/.env with your real Twilio credentials before testing.")
        return

    print("✅ Twilio credentials found in .env")
    print(f"🔄 Initializing Twilio Client (From: {from_number})...")
    
    try:
        client = TwilioSMSClient(
            account_sid=sid,
            auth_token=token,
            from_number=from_number
        )
        
        # Test number to send the SMS to (we'll use the MAINTENANCE_PHONE or the FROM number for testing if no other is provided)
        test_to_number = os.getenv("MAINTENANCE_PHONE", from_number)
        
        print(f"📤 Sending test SMS to: {test_to_number}...")
        
        message_sid = client.send_incident_alert(
            to_phone=test_to_number,
            message_body="🚨 RAILMIND TEST: This is a test message from your Twilio integration."
        )
        
        if message_sid:
            print(f"✅ Success! Message sent with SID: {message_sid}")
        else:
            print("❌ Failed to send message. Check your Twilio logs or console.")
            
    except Exception as e:
        print(f"❌ Error during Twilio test: {e}")

if __name__ == "__main__":
    test_twilio()
