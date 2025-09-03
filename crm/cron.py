import datetime
import asyncio
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport


def log_crm_heartbeat():
    now = datetime.datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    message = f"{now} CRM is alive\n"

    with open("/tmp/crm_heartbeat_log.txt", "a") as log_file:
        log_file.write(message)

        # Run optional GraphQL hello query
        try:
            asyncio.run(query_graphql_hello(log_file, now))
        except Exception as e:
            log_file.write(f"{now} GraphQL check failed: {e}\n")


async def query_graphql_hello(log_file, now):
    transport = RequestsHTTPTransport(
        url="http://localhost:8000/graphql",
        verify=True,
        retries=3,
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)

    query = gql("{ hello }")
    result = await client.execute_async(query)

    log_file.write(f"{now} GraphQL hello response: {result}\n")

def update_low_stock():
    now = datetime.datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    with open("/tmp/low_stock_updates_log.txt", "a") as log_file:
        try:
            result = asyncio.run(run_update_mutation())
            products = result.get("updateLowStockProducts", {}).get("products", [])
            for product in products:
                log_file.write(
                    f"{now} - Updated {product['name']} to stock {product['stock']}\n"
                )
        except Exception as e:
            log_file.write(f"{now} - Error updating low stock: {e}\n")
