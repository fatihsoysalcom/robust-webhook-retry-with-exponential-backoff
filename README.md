# Robust Webhook Retry with Exponential Backoff

This example demonstrates a robust webhook retry mechanism using exponential backoff and jitter. It spins up a local mock HTTP server that simulates temporary failures (503 and 429 status codes) before succeeding, showing how the sender handles failures gracefully without overloading the receiver.

## Language

`python`

## How to Run

Run 'python webhook_retry.py' in your terminal. No external dependencies are required.

## Original Article

This example accompanies the Turkish article: [Robust Webhook Retry Stratejisi Nasıl Kurulur?](https://fatihsoysal.com/blog/robust-webhook-retry-stratejisi-nasil-kurulur/).

## License

MIT — see [LICENSE](LICENSE).
