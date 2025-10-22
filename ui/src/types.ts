type MADSciError = {


    message: string
    logged_at: string
    error_type: string | null

}

type WorkcellStatus = {

    paused: boolean;

    errored: boolean;

    errors: MADSciError[];

    initializing: boolean;

    shutdown: boolean;

    locked: boolean;


}

type WorkcellState = {
    status: WorkcellStatus

    workflow_queue: Workflow[]

    workcell_definition: WorkcellDefinition

    nodes: Record<string, NodeData>

    locations: Record<string, LocationData>
}

type WorkcellDefinition  = {

    workcell_name: string;
    manager_type: string;
    workcell_id: string;
    description: string | null;
    nodes: Record<string, string>
    locations: LocationDefinition[]

}

type Step = {

}

type Workflow = {

}

type NodeInfo = {

}

type NodeData = {

}

type LocationData = LocationDefinition &
{
    reservation: any | null;
    resource_id: string | null;
}
type LocationDefinition = {
    location_name: string;
    location_id: string;
    description: string | null;
    reference: Record<string, any>;
    resource_definition: any | null;


}
