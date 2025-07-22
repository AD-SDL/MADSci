"""
Complete multi-node utilization test script.
Tests utilization tracking across different node types.
"""

import datetime
import time
from madsci.client.experiment_application import ExperimentApplication, ExperimentDesign
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.client.event_client import EventClient


class MultiNodeExperimentApplication(ExperimentApplication):
    url = "http://localhost:8002/"
    experiment_design = ExperimentDesign(
        experiment_name="Multi-Node Utilization Test",
        experiment_description="Testing utilization with multiple node types",
    )


def create_multi_node_workflow():
    """Create workflow using multiple node types to test all tracked nodes."""
    return WorkflowDefinition(
        name="Multi-Node Test",
        steps=[
            # Liquid Handler Steps
            {
                "name": "Step 1 - Initialize Liquid Handler",
                "description": "Initialize liquid handler",
                "node": "liquidhandler_1",
                "action": "run_command",
                "args": {"command": "initialize"},
            },
            {
                "name": "Step 2 - Load Tips",
                "description": "Load pipette tips",
                "node": "liquidhandler_1",
                "action": "run_command",
                "args": {"command": "load_tips"},
            },
            
            # Robot Arm Steps  
            {
                "name": "Step 3 - Transfer Plate",
                "description": "Transfer plate using robot arm",
                "node": "robotarm_1",
                "action": "transfer",
                "args": {
                    
                },
            },
            
            # Plate Reader Steps
            {
                "name": "Step 4 - Read Plate",
                "description": "Read plate using plate reader", 
                "node": "platereader_1",
                "action": "read_plate",
                "args": {},
            },
            
            # Liquid Handler Final Step
            {
                "name": "Step 5 - Process Samples",
                "description": "Process samples",
                "node": "liquidhandler_1",
                "action": "run_command",
                "args": {"command": "process_samples"},
            },
        ],
    )


def run_multi_node_test():
    """Test utilization tracking across multiple node types."""
    print("Multi-Node Utilization Test")
    print("=" * 40)
    
    client = EventClient(event_server_url="http://localhost:8001")
    client.logger.setLevel(10)
    
    # Get initial state
    print("\nInitial State:")
    initial_summary = client.get_utilization_summary()
    print(f"   System utilization: {initial_summary.system_utilization.utilization_percentage:.1f}%")
    print(f"   Tracked nodes: {len(initial_summary.node_utilizations)}")
    
    if initial_summary.node_utilizations:
        print("   Node states:")
        for node_id, node_util in initial_summary.node_utilizations.items():
            print(f"     {node_id}: {node_util.utilization_percentage:.1f}% ({node_util.current_state})")
    
    experiment_application = MultiNodeExperimentApplication()
    
    # Test: Multi-node workflow
    print(f"\nRunning Multi-Node Workflow...")
    
    workflow = create_multi_node_workflow()
    start_time = datetime.datetime.now()
    
    try:
        with experiment_application.manage_experiment(
            run_name=f"multi_node_test_{start_time.strftime('%H%M%S')}",
            run_description="Multi-node utilization test",
        ):
            experiment_application.workcell_client.start_workflow(workflow)
            time.sleep(15)  # Give workflow time to complete
        
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"   Multi-node workflow completed in {duration:.1f} seconds")
        
    except Exception as e:
        print(f"   Multi-node workflow failed: {e}")
    
    # Final report
    print(f"\nFinal Multi-Node Utilization Report:")
    print("=" * 40)
    
    final_summary = client.get_utilization_summary()
    print(f"System Overview:")
    print(f"  Utilization: {final_summary.system_utilization.utilization_percentage:.1f}%")
    print(f"  Total time tracked: {final_summary.system_utilization.total_time:.1f}s")
    print(f"  Active time: {final_summary.system_utilization.active_time:.1f}s")
    
    if final_summary.node_utilizations:
        print(f"\nNode Performance (All {len(final_summary.node_utilizations)} Nodes):")
        sorted_nodes = sorted(
            final_summary.node_utilizations.items(),
            key=lambda x: x[1].utilization_percentage,
            reverse=True
        )
        
        for node_id, node_util in sorted_nodes:
            print(f"  {node_id}:")
            print(f"    Utilization: {node_util.utilization_percentage:.1f}%")
            print(f"    Busy time: {node_util.busy_time:.1f}s")
            print(f"    State: {node_util.current_state}")
    
    print(f"\nMulti-node test completed! Should see utilization across multiple nodes.")


def test_current_state():
    """Just check current utilization state."""
    print("Current Utilization State Check")
    print("=" * 35)
    
    client = EventClient(event_server_url="http://localhost:8001")
    
    summary = client.get_utilization_summary()
    
    print(f"System:")
    print(f"  Utilization: {summary.system_utilization.utilization_percentage:.1f}%")
    print(f"  State: {summary.system_utilization.current_state}")
    print(f"  Active experiments: {len(summary.system_utilization.active_experiments)}")
    print(f"  Active workflows: {len(summary.system_utilization.active_workflows)}")
    print(f"  Tracker uptime: {summary.tracker_uptime/60:.1f} minutes")
    
    if summary.node_utilizations:
        print(f"\nNodes ({len(summary.node_utilizations)} tracked):")
        for node_id, node_util in summary.node_utilizations.items():
            print(f"  {node_id}:")
            print(f"    Utilization: {node_util.utilization_percentage:.1f}%")
            print(f"    State: {node_util.current_state}")
            print(f"    Busy time: {node_util.busy_time:.1f}s")
    else:
        print("  No nodes currently tracked")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        test_current_state()
    else:
        run_multi_node_test()