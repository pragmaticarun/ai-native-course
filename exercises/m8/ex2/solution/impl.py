from datetime import timedelta

from temporalio import workflow


@workflow.defn(name="PublishWithApproval")
class PublishWithApproval:
    def __init__(self) -> None:
        self._status = "waiting"
        self._detail = ""

    @workflow.run
    async def run(self, title: str) -> str:
        try:
            await workflow.wait_condition(
                lambda: self._status != "waiting", timeout=timedelta(days=7)
            )
        except TimeoutError:
            self._status = "expired"
            return "expired"
        if self._status == "approved":
            return f"published {title} (approved by {self._detail})"
        return f"rejected: {self._detail}"

    @workflow.signal
    async def approve(self, reviewer: str) -> None:
        if self._status == "waiting":
            self._status, self._detail = "approved", reviewer

    @workflow.signal
    async def reject(self, reason: str) -> None:
        if self._status == "waiting":
            self._status, self._detail = "rejected", reason

    @workflow.query
    def status(self) -> str:
        return self._status
