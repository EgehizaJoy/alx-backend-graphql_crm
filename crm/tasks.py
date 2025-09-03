import datetime
import asyncio
from celery import shared_task
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from datetime import datetime
import requests


@shared_task
def generate_crm_report():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        result = asyncio.run(fetch_report_data())
        customers = result["customers"]["totalCount"]
        orders = result["orders"]["totalCount"]
        revenue = result["orders"]["totalRevenue"]

        log_message = f"{now} - Report: {customers} customers, {orders} orders, {revenue} revenue\n"
    except Exception as e:
        log_message = f"{now} - Error generating report: {e}\n"

    with open("/tmp/crm_report_log.txt", "a") as log_file:
        log_file.write(log_message)


async def fetch_report_data():
    transport = RequestsHTTPTransport(
        url="http://localhost:8000/graphql",
        verify=True,
        retries=3,
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)

    query = gql(
        """
        query {
            customers {
                totalCount
            }
            orders {
                totalCount
                totalRevenue
            }
        }
        """
    )

    return await client.execute_async(query)
