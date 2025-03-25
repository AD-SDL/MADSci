
import { ref, watchEffect } from 'vue';

const main_url = ref()
const state_url = ref()
const workcell_info_url = ref()
const workflows_url = ref()
const workflows = ref()
const experiments = ref()
const experiments_url = ref()
const events_url = ref()
const events = ref()
const workcell_state = ref()
const workcell_info = ref()
const campaigns = ref()
const campaigns_url = ref()
const experiment_keys = ref()
const resources_url = ref()
const urls = ref()
const experiment_objects: any = ref([])
const resources = ref()
main_url.value = "http://".concat(window.location.host)
class ExperimentInfo {
    experiment_id?: string;
    experiment_workflows: any;
    experiment_name?: string;
    num_wfs?: any;
    num_events?: any;
    events?: any
}
async function get_events(experiment_id: string) {
    return Object.values(await ((await fetch(main_url.value.concat("/experiments/".concat(experiment_id).concat("/events"))))).json());
}
watchEffect(async () => {
    urls.value = await ((await fetch(main_url.value.concat("/urls"))).json())
    state_url.value = urls.value.workcell_manager.concat("state")
    resources_url.value = urls.value.resource_manager
    experiments_url.value = main_url.value.concat("/experiments/all")
    campaigns_url.value = main_url.value.concat("/campaigns/all")
    workcell_info_url.value = urls.value.workcell_manager.concat("workcell")
    workflows_url.value = urls.value.workcell_manager.concat("workflows")
    events_url.value = main_url.value.concat("/events/all")

    updateResources()
    setInterval(updateWorkcellState, 1000)
    setInterval(updateWorkflows, 1000)
    setInterval(updateResources, 5000)
    // setInterval(updateCampaigns, 10000);
    // setInterval(updateEvents, 10000);

    async function updateResources() {
        resources.value = await ((await fetch(urls.value.resource_manager.concat('resource/query'), {
            method: "POST",
            body: JSON.stringify({"multiple": true}),
            headers: {
                'Content-Type': 'application/json'
            }
          })).json());
    }

    async function updateCampaigns() {
        campaigns.value = await ((await fetch(campaigns_url.value)).json());
    }

    async function updateEvents() {
        events.value = await ((await fetch(events_url.value)).json());
    }

    async function updateWorkcellState() {
        workcell_state.value = await (await fetch(state_url.value)).json();
        workcell_info.value = await (await fetch(workcell_info_url.value)).json();
    }

    async function updateWorkflows() {
        workflows.value = await (await fetch(workflows_url.value)).json();
    }


})

function get_status(value: any) {
    if(value["error"] && value["error"] != false)  {
        return "error"
    }
    if(value["cancelled"] && value["cancelled"] != false)  {
        return "cancelled"
    }
    if(value["locked"] && value["locked"] != false)  {
        return "locked"
    }
    if(value["paused"] && value["paused"] != false) {
        return "paused"
    }
    if(value["busy"] && value["busy"]) {
        return "busy"
    } else {
        return "ready"
    }
}

export { campaigns, campaigns_url, events, experiment_keys, experiment_objects, experiments, experiments_url, get_status, main_url, state_url, workcell_info, workcell_info_url, workcell_state, workflows, urls, resources };
