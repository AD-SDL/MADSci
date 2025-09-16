import {
  ref,
  watchEffect,
} from 'vue';

import { Event } from './types/event_types';
import { Experiment } from './types/experiment_types';
import {
  WorkcellState,
} from './types/workcell_types';
import { Workflow } from './types/workflow_types';

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
const labContext = ref<any>(null)
const labHealth = ref<any>(null)
const isRefreshing = ref<boolean>(false)
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

    async function updateLabContext() {
        try {
            labContext.value = await (await fetch(main_url.value.concat("/context"))).json();
        } catch (error) {
            console.error("Failed to fetch lab context:", error);
            labContext.value = null;
        }
    }

    async function updateLabHealth() {
        try {
            labHealth.value = await (await fetch(main_url.value.concat("/lab_health"))).json();
        } catch (error) {
            console.error("Failed to fetch lab health:", error);
            labHealth.value = null;
        }
    }

    // Initial load of lab information
    updateLabContext();
    updateLabHealth();

})

async function refreshLabInfo() {
    isRefreshing.value = true;
    try {
        const contextPromise = fetch(main_url.value.concat("/context")).then(res => res.json());
        const healthPromise = fetch(main_url.value.concat("/lab_health")).then(res => res.json());

        const [context, health] = await Promise.all([contextPromise, healthPromise]);

        labContext.value = context;
        labHealth.value = health;
    } catch (error) {
        console.error("Failed to refresh lab information:", error);
    } finally {
        isRefreshing.value = false;
    }
}

function get_status(value: any) {
    if(value["errored"] === true)  {
        return "errored"
    }
    if(value["cancelled"] === true)  {
        return "cancelled"
    }
    if(value["locked"] === true)  {
        return "locked"
    }
    if(value["paused"] === true) {
        return "paused"
    }
    if((value["busy"] === true) || (value["running_actions"] && (value["running_actions"].length > 0))) {
        return "running"
    }
    if (value["initializing"] === true) {
        return "initializing"
    } else {
        return "ready"
    }
}

export {
  active_workflows,
  archived_workflows,
  campaigns,
  campaigns_url,
  events,
  experiment_keys,
  experiment_objects,
  experiments,
  experiments_url,
  get_status,
  isRefreshing,
  labContext,
  labHealth,
  main_url,
  refreshLabInfo,
  resources,
  state_url,
  urls,
  workcell_info,
  workcell_info_url,
  workcell_state,
};
