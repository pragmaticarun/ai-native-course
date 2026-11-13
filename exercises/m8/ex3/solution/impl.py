from datetime import timedelta

from temporalio import activity, workflow

T = timedelta(seconds=10)


@activity.defn
async def charge(order: str) -> str:
    return f"charged {order}"


@activity.defn
async def fraud_check(order: str) -> str:
    return f"checked {order}"


@activity.defn
async def ship(order: str) -> str:
    return f"shipped {order}"


@workflow.defn(name="Order")
class OrderV1:
    @workflow.run
    async def run(self, order: str) -> list[str]:
        steps = [await workflow.execute_activity(charge, order, start_to_close_timeout=T)]
        steps.append(await workflow.execute_activity(ship, order, start_to_close_timeout=T))
        return steps


@workflow.defn(name="Order")
class OrderV2:
    @workflow.run
    async def run(self, order: str) -> list[str]:
        steps = [await workflow.execute_activity(charge, order, start_to_close_timeout=T)]
        if workflow.patched("fraud-check"):
            steps.append(
                await workflow.execute_activity(fraud_check, order, start_to_close_timeout=T)
            )
        steps.append(await workflow.execute_activity(ship, order, start_to_close_timeout=T))
        return steps
