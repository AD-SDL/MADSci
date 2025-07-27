
import { Console } from 'console';
import { ref, watchEffect } from 'vue';
import { WorkcellState } from './types/workcell_types';
import {Event} from './types/event_types'
import {Experiment} from './types/experiment_types'
import { NodeStatus } from './types/workcell_types';

const main_url = ref<string>("")
const state_url = ref<string>("")
const workcell_info_url = ref<string>("")
const active_workflows_url = ref<string>("")
const archived_workflows_url = ref<string>("")
const active_workflows = ref<Record<string, Workflow>>({})
const archived_workflows = ref<Record<string, Workflow>>({})
const experiments = ref<Experiment[]>([])
const experiments_url = ref<string>("")
const events_url = ref<string>("")
const events = ref<Event[]>([])
const workcell_state = ref<WorkcellState>()
const workcell_info = ref()
const campaigns = ref()
const campaigns_url = ref()
const experiment_keys = ref()
const resources_url = ref()
const urls = ref()
const experiment_objects: any = ref([])
const resources = ref()
main_url.value = "http://".concat(window.location.host)
interface ExperimentInfo {
    experiment_id?: string;
    experiment_workflows: Workflow[];
    experiment_name?: string;
    num_wfs?: number;
    num_events?: number;
    events?: Event[]
}
async function get_events(experiment_id: string) {
    return Object.values(await ((await fetch(main_url.value.concat("/experiments/".concat(experiment_id).concat("/events"))))).json());
}
watchEffect(async () => {
    urls.value = await ((await fetch(main_url.value.concat("/context"))).json())
    state_url.value = urls.value.workcell_server_url.concat("state")
    resources_url.value = urls.value.resource_server_url
    experiments_url.value = urls.value.experiment_server_url.concat("experiments")
    campaigns_url.value = urls.value.experiment_server_url.concat("campaigns")
    workcell_info_url.value = urls.value.workcell_server_url.concat("workcell")
    active_workflows_url.value = urls.value.workcell_server_url.concat("workflows/active")
    archived_workflows_url.value = urls.value.workcell_server_url.concat("workflows/archived")
    events_url.value = urls.value.event_server_url.concat("events")

    updateResources()
    setInterval(updateWorkcellState, 1000)
    setInterval(updateWorkflows, 1000)
    setInterval(updateResources, 1000)
    setInterval(updateExperiments, 1000);
    // setInterval(updateEvents, 10000);

    async function updateResources() {
        resources.value = await ((await fetch(resources_url.value.concat('resource/query'), {
            method: "POST",
            body: JSON.stringify({"multiple": true}),
            headers: {
                'Content-Type': 'application/json'
            }
          })).json());
    }

    async function updateExperiments() {
        experiments.value = await ((await fetch(experiments_url.value)).json());
    }

    async function updateEvents() {
        events.value = await ((await fetch(events_url.value)).json());
    }

    async function updateWorkcellState() {
        workcell_state.value = await (await fetch(state_url.value)).json();
        workcell_info.value = await (await fetch(workcell_info_url.value)).json();
    }

    async function updateWorkflows() {
        active_workflows.value = await (await fetch(active_workflows_url.value)).json();
        archived_workflows.value = await (await fetch(archived_workflows_url.value)).json();
    }


})

function get_status(status: NodeStatus): string {
    if(status["errored"] != false)  {
        return "errored"
    }
    if(status["cancelled"] != false)  {
        return "cancelled"
    }
    if(status["locked"] != false)  {
        return "locked"
    }
    if(status["paused"] != false) {
        return "paused"
    }
    if((status["busy"] != false) || (status["running_actions"] && (status["running_actions"].length > 0))) {
        return "running"
    }
    if (status["initializing"] != false) {
        return "initializing"
    } else {
        return "ready"
    }
}

export { campaigns, campaigns_url, events, experiment_keys, experiment_objects, experiments, experiments_url, get_status, main_url, state_url, workcell_info, workcell_info_url, workcell_state, active_workflows, archived_workflows, urls, resources };
