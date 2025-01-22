"""Default MADSci Workcell scheduler"""

from madsci.common.types.step_types import Step
from schedulers.scheduler import AbstractScheduler


class Scheduler(AbstractScheduler):
    """the main class that handles checking whether steps are ready to run and assigning priority"""

    def run_iteration(self) -> None:
        """run an iteration of the scheduler and set priority for which workflow to run next"""
        priority = 0
        workflows = sorted(
            self.state_handler.get_all_workflows().values(),
            key=lambda item: item.submitted_time,
        )
        for wf in workflows:
            step = wf.steps[wf.step_index]
            wf.scheduler_metadata.ready_to_run = (
                not (wf.paused)
                and wf.status in ["queued", "in_progress"]
                and self.check_step(step)
            )
            wf.scheduler_metadata.priority = priority
            priority -= 1
            self.state_handler.set_workflow_quiet(wf)

    def check_step(self, step: Step) -> bool:
        """check if a step is ready to run"""
        return self.resource_checks(step) and self.node_checks(step)

    def resource_checks(self, step: Step) -> bool:  # noqa: ARG002
        """check if the resources for the step are ready TODO: actually check"""
        return True

    def node_checks(self, step: Step) -> bool:
        """check if the step node is ready to run a step"""
        node = self.state_handler.get_node(step.node)
        return node is not None and node.status.ready
