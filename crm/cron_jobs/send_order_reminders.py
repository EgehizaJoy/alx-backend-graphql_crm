#!/usr/bin/env python3

import asyncio
from datetime import datetime, timedelta
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

async def main():
    # GraphQL endpoint
    transport = RequestsHTTPTransport(
        url="http://localhost:8000/graphql",
        verify=True,
        retries=3,
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)

    # Date range: last 7 days
    cutoff_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    # GraphQL query
    query = gql(
        """
        query getRecentOrders($cutoff: Date!) {
            orders(filter: {orderDate_Gte: $cutoff, status: "PENDING"}) {
                id
                customer {
                    email
                }
            }
        }
        """
    )

    # Execute query
    result = await client.execute_async(query, variable_values={"cutoff": cutoff_date})
    orders = result.get("orders", [])

    # Log results
    with open("/tmp/order_reminders_log.txt", "a") as log_file:
        for order in orders:
            log_file.write(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Order {order['id']} for {order['customer']['email']}\n"
            )

    print("Order reminders processed!")

if __name__ == "__main__":
    asyncio.run(main())
