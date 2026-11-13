from temporalio import workflow


@workflow.defn(name="PublishWithApproval")
class PublishWithApproval:
    def __init__(self) -> None:
        self._status = "waiting"

    @workflow.run
    async def run(self, title: str) -> str:
        # TODO: wait up to 7 days for approve/reject
        self._status = "expired"
        return "expired"

    @workflow.signal
    async def approve(self, reviewer: str) -> None:
        pass  # TODO

    @workflow.signal
    async def reject(self, reason: str) -> None:
        pass  # TODO

    @workflow.query
    def status(self) -> str:
        return self._status
