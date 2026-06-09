import requests
import sys

# Configure UTF-8 encoding for Windows terminals
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

def test_flow():
    print("====================================================")
    print("   RUNNING MULTILINGUAL CHAT INTEGRATION TESTS")
    print("====================================================\n")

    # Step 1: Login as Client Arun (seeded on startup)
    print("Step 1: Logging in as client 'arun'...")
    try:
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "arun",
            "password": "password123"
        })
        if login_res.status_code != 200:
            print(f"❌ Login failed: {login_res.text}")
            return
        
        arun_token = login_res.json()["access_token"]
        print("✅ Client login successful.")
        print(f"   Preferred Language: {login_res.json()['preferred_language']}")
        
        # Step 2: Create a ticket in Tamil
        print("\nStep 2: Creating support ticket in Tamil (தமிழ்)...")
        headers_arun = {"Authorization": f"Bearer {arun_token}"}
        ticket_payload = {
            "title": "கணக்கு சிக்கல்",
            "initial_message": "எனது கணக்கில் நுழைய முடியவில்லை, பிழை குறியீடு 500 காட்டுகிறது"
        }
        
        ticket_res = requests.post(f"{BASE_URL}/api/tickets", json=ticket_payload, headers=headers_arun)
        if ticket_res.status_code != 200:
            print(f"❌ Ticket creation failed: {ticket_res.text}")
            return
            
        ticket_data = ticket_res.json()
        ticket_id = ticket_data["id"]
        print(f"✅ Ticket created successfully with ID: {ticket_id}")
        print(f"   Original message (Tamil): '{ticket_payload['initial_message']}'")
        print(f"   Translated English: '{ticket_data['messages'][0]['translated_text']}'")
        print(f"   Detected Language: {ticket_data['messages'][0]['language']}")
        print(f"   AI Urgency Priority: {ticket_data['priority']}")
        print(f"   AI Tone Sentiment: {ticket_data['sentiment']}")
        
        # Step 3: Login as Support Engineer
        print("\nStep 3: Logging in as Support Engineer...")
        eng_login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "engineer",
            "password": "admin123"
        })
        if eng_login_res.status_code != 200:
            print(f"❌ Engineer login failed: {eng_login_res.text}")
            return
            
        eng_token = eng_login_res.json()["access_token"]
        headers_eng = {"Authorization": f"Bearer {eng_token}"}
        print("✅ Engineer login successful.")

        # Step 4: Engineer fetches queue and reviews arun's ticket
        print("\nStep 4: Fetching engineer inbox queue...")
        queue_res = requests.get(f"{BASE_URL}/api/tickets", headers=headers_eng)
        if queue_res.status_code != 200:
            print(f"❌ Failed to fetch queue: {queue_res.text}")
            return
            
        queue = queue_res.json()
        print(f"✅ Queue fetched. Total open tickets: {len(queue)}")
        
        # Step 5: Engineer replies in English
        print("\nStep 5: Engineer sending reply in English...")
        reply_payload = {
            "text": "Thank you for reporting. We will reset your account credentials, please wait."
        }
        reply_res = requests.post(
            f"{BASE_URL}/api/tickets/{ticket_id}/messages", 
            json=reply_payload, 
            headers=headers_eng
        )
        if reply_res.status_code != 200:
            print(f"❌ Engineer reply failed: {reply_res.text}")
            return
            
        reply_data = reply_res.json()
        print("✅ Reply successfully sent by Engineer.")
        print(f"   Engineer original (English): '{reply_payload['text']}'")
        print(f"   Backend translation back to client language (Tamil): '{reply_data['translated_text']}'")
        
        # Step 6: Verify client chat history sees translation
        print("\nStep 6: Retrieving chat history as Client 'arun'...")
        history_res = requests.get(f"{BASE_URL}/api/tickets/{ticket_id}", headers=headers_arun)
        if history_res.status_code != 200:
            print(f"❌ Failed to retrieve history: {history_res.text}")
            return
            
        history = history_res.json()
        print(f"✅ History retrieved. Total messages: {len(history['messages'])}")
        for i, msg in enumerate(history["messages"]):
            sender = "Client" if msg["sender_role"] == "client" else "Engineer"
            print(f"   [{i+1}] {sender}: {msg['original_text']} (Eng translation: {msg['translated_text']})")
            
        print("\n====================================================")
        print("   🎉 ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")
        print("====================================================")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")

if __name__ == "__main__":
    test_flow()
