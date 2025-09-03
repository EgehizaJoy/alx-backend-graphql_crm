import datetime

def log_crm_heartbeat():
    now = datetime.datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    message = f"{now} CRM is alive\n"
    with open("/tmp/crm_heartbeat_log.txt", "a") as log_file:
        log_file.write(message)

    # Optional: verify GraphQL endpoint (hello query)
    try:
        import requests
        response = requests.post(
            "http://localhost:8000/graphql",
            json={"query": "{ hello }"},
            timeout=5
        )
        if response.status_code == 200:
            log_file.write(f"{now} GraphQL endpoint responsive: {response.json()}\n")
        else:
            log_file.write(f"{now} GraphQL endpoint error: {response.status_code}\n")
    except Exception as e:
        log_file.write(f"{now} GraphQL check failed: {e}\n")
