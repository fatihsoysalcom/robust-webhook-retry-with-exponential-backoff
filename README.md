# robust-webhook-retry-with-exponential-backoff
This example demonstrates a robust webhook retry mechanism using exponential backoff and jitter. It spins up a local mock HTTP server that simulates temporary failures (503 and 429 status codes) before succeeding, showing how the sender handles failures gracefully without overloading the receiver.
