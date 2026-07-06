import http.server
import socketserver
import threading
import time
import random
import urllib.request
import urllib.error
import json

PORT = 8080
URL = f"http://localhost:{PORT}/webhook"

# --- MOCK WEBHOOK RECEIVER (SERVER) ---
# This server simulates a flaky destination that fails initially and then succeeds.
class FlakyWebhookReceiver(http.server.BaseHTTPRequestHandler):
    attempt_counter = 0

    def do_POST(self):
        FlakyWebhookReceiver.attempt_counter += 1
        
        # Simulate failure for the first 3 attempts to test our retry mechanism
        if FlakyWebhookReceiver.attempt_counter < 4:
            # Alternate between 503 Service Unavailable and 429 Too Many Requests
            status_code = 503 if FlakyWebhookReceiver.attempt_counter % 2 != 0 else 429
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"error": "Temporary failure", "attempt": FlakyWebhookReceiver.attempt_counter}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            print(f"[Receiver] Received request #{FlakyWebhookReceiver.attempt_counter} -> Responded with HTTP {status_code} (Simulated Failure)")
        else:
            # 4th attempt succeeds
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "success", "message": "Webhook processed successfully!"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            print(f"[Receiver] Received request #{FlakyWebhookReceiver.attempt_counter} -> Responded with HTTP 200 (Success!)")

    def log_message(self, format, *args):
        # Suppress default HTTP logging to keep console output clean
        return

def start_mock_server():
    handler = FlakyWebhookReceiver
    # Allow immediate reuse of the port
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"[System] Mock Webhook Receiver started on port {PORT}")
        httpd.serve_forever()

# --- ROBUST WEBHOOK SENDER WITH RETRY STRATEGY ---
def send_webhook_with_retry(url, payload, max_retries=5, base_delay=1.0, max_delay=8.0):
    """
    Sends a webhook payload with an exponential backoff and jitter retry strategy.
    """
    data = json.dumps(payload).encode('utf-8')
    
    for attempt in range(1, max_retries + 1):
        print(f"\n[Sender] Attempt {attempt} of {max_retries}...")
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            # Perform the HTTP POST request
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    print(f"[Sender] Success! Server Response: {result}")
                    return True
                    
        except urllib.error.HTTPError as e:
            print(f"[Sender] HTTP Error encountered: {e.code} {e.reason}")
            
            # Robustness Rule: Only retry on 5xx (Server Errors) or 429 (Rate Limits).
            # Do NOT retry on 400 Bad Request, 401 Unauthorized, or 404 Not Found.
            is_retryable = (500 <= e.code < 600) or (e.code == 429)
            if not is_retryable:
                print(f"[Sender] Non-retryable HTTP status code {e.code}. Aborting webhook delivery.")
                break
                
        except urllib.error.URLError as e:
            # Network-level failures (DNS, connection refused, timeouts) are always retryable
            print(f"[Sender] Network error encountered: {e.reason}")
            
        # If we reached here, the attempt failed but is eligible for retry
        if attempt == max_retries:
            print("[Sender] Max retries reached. Moving webhook payload to Dead Letter Queue (DLQ) for manual review.")
            return False
            
        # --- EXPONENTIAL BACKOFF WITH JITTER ---
        # Formula: delay = min(max_delay, base_delay * 2^(attempt-1))
        backoff_delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
        
        # Full Jitter: Randomize delay to prevent "thundering herd" problem on the receiver
        jitter = random.uniform(0, backoff_delay)
        total_delay = backoff_delay + jitter
        
        print(f"[Sender] Retrying in {total_delay:.2f}s (Backoff: {backoff_delay:.2f}s + Jitter: {jitter:.2f}s)")
        time.sleep(total_delay)
        
    return False

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # 1. Start the mock receiver in a background daemon thread
    server_thread = threading.Thread(target=start_mock_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to start up
    time.sleep(1)
    
    # 2. Define payload
    webhook_payload = {
        "event": "payment.completed",
        "data": {
            "transaction_id": "tx_987654321",
            "amount": 150.00,
            "currency": "TRY"
        }
    }
    
    # 3. Trigger the robust sender
    print("\n[System] Initiating robust webhook delivery flow...")
    success = send_webhook_with_retry(URL, webhook_payload)
    
    if success:
        print("\n[System] Webhook delivery workflow completed successfully!")
    else:
        print("\n[System] Webhook delivery workflow failed.")
