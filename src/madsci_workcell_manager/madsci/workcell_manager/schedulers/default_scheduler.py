"""Default MADSci Workcell scheduler"""

import traceback

from madsci.common.types.step_types import Step
from madsci.common.types.workflow_types import Workflow
from madsci.workcell_manager.condition_checks import evaluate_condition_checks
from madsci.workcell_manager.schedulers.scheduler import AbstractScheduler


class Scheduler(AbstractScheduler):
    """The main class that handles checking whether steps are ready to run and assigning priority"""

    def run_iteration(self, workflows: list[Workflow]) -> None:
        """Run an iteration of the scheduling algorithm and markup the scheduler metadata for each workflow"""
        priority = 0
        workflows: list[Workflow] = sorted(
            self.state_handler.get_all_workflows().values(),
            key=lambda item: item.submitted_time,
        )
        for wf in workflows:
            try:
                if wf.step_index < len(wf.steps):
                    step = wf.steps[wf.step_index]
                    wf.scheduler_metadata.ready_to_run = True
                    wf.scheduler_metadata.reasons = []
                    if wf.paused:
                        wf.scheduler_metadata.ready_to_run = False
                        wf.scheduler_metadata.reasons.append("Workflow is paused")
                    if wf.status not in ["queued", "in_progress"]:
                        wf.scheduler_metadata.ready_to_run = False
                        wf.scheduler_metadata.reasons.append(
                            "Workflow is not queued or in progress"
                        )
                    self.location_checks(step, wf)
                    self.resource_checks(step, wf)
                    self.node_checks(step, wf)
                    evaluate_condition_checks(
                        step, wf, self.workcell_definition, self.state_handler
                    )
                    wf.scheduler_metadata.priority = priority
                    priority -= 1
            except Exception as e:
                self.logger.log_error(
                    f"Error in scheduler while evaluating workflow {wf.workflow_id}: {traceback.format_exc()}"
                )
                wf.scheduler_metadata.ready_to_run = False
                wf.scheduler_metadata.reasons.append(f"Exception in scheduler: {e}")
            finally:
                self.state_handler.set_workflow_quiet(wf)

    def location_checks(self, step: Step, wf: Workflow) -> None:
        """Check if the location(s) for the step are ready"""
        for location in step.locations.values():
            if location.resource_id is not None and self.resource_client is not None:
                self.resource_client.get_resource(location.resource_id)
                # TODO: what do we do with the location_resource?
            if location.reservation is not None:
                wf.scheduler_metadata.ready_to_run = False
                wf.scheduler_metadata.reasons.append(
                    f"Location {location.location_id} is reserved by {location.reservation.owned_by.model_dump(mode='json', exclude_none=True)}"
                )

    def resource_checks(self, step: Step, wf: Workflow) -> None:
        """Check if the resources for the step are ready TODO: actually check"""

    def node_checks(self, step: Step, wf: Workflow) -> None:
        """Check if the node used in the step currently has a "ready" status"""
        node = self.state_handler.get_node(step.node)
        if node is None:
            wf.scheduler_metadata.ready_to_run = False
            wf.scheduler_metadata.reasons.append(f"Node {step.node} not found")
        if not node.status.ready:
            wf.scheduler_metadata.ready_to_run = False
            wf.scheduler_metadata.reasons.append(
                f"Node {step.node} not ready: {node.status.description}"
            )
        if node.reservation is not None and node.reservation.check(wf.ownership_info):
            wf.scheduler_metadata.ready_to_run = False
            wf.scheduler_metadata.reasons.append(
                f"Node {step.node} is reserved by {node.reservation.owned_by.model_dump(mode='json', exclude_none=True)}"
            )
