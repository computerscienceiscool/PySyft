# RUN: just reset-high && pytest -s tests/scenariosv2/l2_test.py
## .logs files will be created in pwd

# stdlib
import asyncio
import random

# third party
from faker import Faker
from l0_test import Event
from l0_test import admin_create_bq_pool_high
from l0_test import admin_create_endpoint
from l0_test import admin_signup_users
from l0_test import query_sql
import pytest
from sim.core import Simulator
from sim.core import SimulatorContext
from sim.core import sim_activity
from sim.core import sim_entrypoint

# syft absolute
import syft as sy
from syft.client.client import SyftClient

fake = Faker()


# ---------------------------------- admin ----------------------------------
@sim_activity(
    wait_for=[
        Event.USER_CAN_SUBMIT_QUERY,
    ]
)
async def admin_triage_requests(ctx: SimulatorContext, admin_client: SyftClient):
    while True:
        await asyncio.sleep(random.uniform(3, 5))
        ctx.logger.info("Admin: Triaging requests")

        pending_requests = admin_client.requests.get_all_pending()
        if len(pending_requests) == 0:
            break
        for request in admin_client.requests.get_all_pending():
            ctx.logger.info(f"Admin: Found request {request.__dict__}")
            if "invalid_func" in request.code.service_func_name:
                request.deny(reason="you submitted an invalid code")
            else:
                request.approve()


@sim_activity(trigger=Event.ADMIN_HIGHSIDE_FLOW_COMPLETED)
async def admin_flow(
    ctx: SimulatorContext, admin_auth: dict, users: list[dict]
) -> None:
    admin_client = sy.login(**admin_auth)
    ctx.logger.info("Admin: logged in")

    await asyncio.gather(
        admin_signup_users(ctx, admin_client, users),
        admin_create_bq_pool_high(ctx, admin_client),
        admin_create_endpoint(ctx, admin_client),
        admin_triage_requests(ctx, admin_client),
    )


# ---------------------------------- user ----------------------------------
@sim_activity(
    wait_for=[
        Event.ADMIN_ALL_ENDPOINTS_CREATED,
        Event.ADMIN_HIGHSIDE_WORKER_POOL_CREATED,
    ],
    trigger=Event.USER_CAN_QUERY_TEST_ENDPOINT,
)
async def user_query_test_endpoint(ctx: SimulatorContext, client: sy.DatasiteClient):
    """Run query on test endpoint"""

    user = client.logged_in_user

    def _query_endpoint():
        ctx.logger.info(f"User: {user} - Calling client.api.bigquery.test_query (mock)")
        res = client.api.bigquery.test_query(sql_query=query_sql())
        assert len(res) == 10000
        ctx.logger.info(f"User: {user} - Received {len(res)} rows")

    await asyncio.to_thread(_query_endpoint)


@sim_activity(
    wait_for=[
        Event.USER_CAN_QUERY_TEST_ENDPOINT,
        Event.ADMIN_HIGHSIDE_WORKER_POOL_CREATED,
    ],
    trigger=Event.USER_CAN_SUBMIT_QUERY,
)
async def user_bq_submit(ctx: SimulatorContext, client: sy.DatasiteClient):
    """Submit query to be run on private data"""
    user = client.logged_in_user

    def _submit_endpoint():
        ctx.logger.info(
            f"User: {user} - Calling client.api.services.bigquery.submit_query"
        )
        res = client.api.bigquery.submit_query(
            func_name="invalid_func",
            query=query_sql(),
        )
        ctx.logger.info(f"User: {user} - Received {res}")

    await asyncio.to_thread(_submit_endpoint)


@sim_activity(
    wait_for=[Event.GUEST_USERS_CREATED, Event.ADMIN_ALL_ENDPOINTS_CREATED],
    trigger=Event.USER_FLOW_COMPLETED,
)
async def user_flow(ctx: SimulatorContext, server_url: str, user: dict):
    client = sy.login(
        url=server_url,
        email=user["email"],
        password=user["password"],
    )
    ctx.logger.info(f"User: {client.logged_in_user} - logged in")

    await user_query_test_endpoint(ctx, client)
    await user_bq_submit(ctx, client)


# ---------------------------------- test ----------------------------------
@sim_entrypoint()
async def sim_l2_scenario(ctx: SimulatorContext):
    users = [
        {
            "name": fake.name(),
            "email": fake.email(),
            "password": "password",
        }
        for i in range(3)
    ]

    server_url = "http://localhost:8080"

    admin_auth = {
        "url": server_url,
        "email": "info@openmined.org",
        "password": "changethis",
    }

    ctx.events.trigger(Event.INIT)
    await asyncio.gather(
        admin_flow(ctx, admin_auth, users),
        *[user_flow(ctx, server_url, user) for user in users],
    )


@pytest.mark.asyncio
async def test_l2_scenario(request):
    sim = Simulator()

    await sim.start(
        sim_l2_scenario,
        random_wait=None,
        check_events=[
            Event.GUEST_USERS_CREATED,
            Event.ADMIN_HIGHSIDE_WORKER_POOL_CREATED,
            Event.ADMIN_ALL_ENDPOINTS_CREATED,
            Event.ADMIN_HIGHSIDE_FLOW_COMPLETED,
        ],
        timeout=300,
    )
