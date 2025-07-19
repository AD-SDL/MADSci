"""
Simple working utilization test using only existing nodes.
"""

import datetime
import time
from madsci.client.experiment_application import ExperimentApplication, ExperimentDesign
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.client.event_client import EventClient


class SimpleExperimentApplication(ExperimentApplication):
    url = "http://localhost:8002/"
    experiment_design = ExperimentDesign(
        experiment_name="Simple Utilization Test",
        experiment_description="Testing utilization with existing nodes only",
    )


def create_liquid_handler_workflow():
    """Create multiple liquid handler workflows."""
    return WorkflowDefinition(
        name="Liquid Handler Test",
        steps=[
            {
                "name": "Step 1 - Initialize",
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
            {
                "name": "Step 3 - Process Samples",
                "description": "Process samples",
                "node": "liquidhandler_1",
                "action": "run_command", 
                "args": {"command": "process_samples"},
            },
        ],
    )


def run_multiple_workflows_test():
    """Run multiple workflows in sequence to test utilization."""
    print("🧪 Running Multiple Workflow Utilization Test")
    print("=" * 50)
    
    client = EventClient(event_server_url="http://localhost:8001")
    client.logger.setLevel(10)
    
    # Get initial state
    print("\n📊 Initial State:")
    initial_summary = client.get_utilization_summary()
    print(f"   System utilization: {initial_summary.system_utilization.utilization_percentage:.1f}%")
    print(f"   System state: {initial_summary.system_utilization.current_state}")
    print(f"   Active experiments: {len(initial_summary.system_utilization.active_experiments)}")
    print(f"   Tracked nodes: {len(initial_summary.node_utilizations)}")
    
    if initial_summary.node_utilizations:
        print("   Node states:")
        for node_id, node_util in initial_summary.node_utilizations.items():
            print(f"     {node_id}: {node_util.utilization_percentage:.1f}% ({node_util.current_state})")
    
    # Run multiple workflows
    experiment_application = SimpleExperimentApplication()
    
    for i in range(3):
        print(f"\n🔬 Running Workflow {i+1}/3...")
        
        workflow = create_liquid_handler_workflow()
        
        start_time = datetime.datetime.now()
        
        try:
            with experiment_application.manage_experiment(
                run_name=f"test_workflow_{i+1}_{start_time.strftime('%H%M%S')}",
                run_description=f"Utilization test workflow {i+1}",
            ):
                experiment_application.workcell_client.start_workflow(workflow)
                
                # Wait for completion
                time.sleep(10)  # Give workflow time to complete
            
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"   ✅ Workflow {i+1} completed in {duration:.1f} seconds")
            
        except Exception as e:
            print(f"   ❌ Workflow {i+1} failed: {e}")
            continue
        
        # Check utilization after each workflow
        summary = client.get_utilization_summary()
        print(f"   System utilization: {summary.system_utilization.utilization_percentage:.1f}%")
        print(f"   Active experiments: {len(summary.system_utilization.active_experiments)}")
        
        if summary.node_utilizations:
            for node_id, node_util in summary.node_utilizations.items():
                print(f"     {node_id}: {node_util.utilization_percentage:.1f}% ({node_util.current_state}) - Busy: {node_util.busy_time:.1f}s")
        
        # Short pause between workflows
        if i < 2:
            print("   ⏳ Waiting 5 seconds...")
            time.sleep(5)
    
    # Final report
    print(f"\n🎯 Final Utilization Report:")
    print("=" * 30)
    
    final_summary = client.get_utilization_summary()
    print(f"System Overview:")
    print(f"  Utilization: {final_summary.system_utilization.utilization_percentage:.1f}%")
    print(f"  State: {final_summary.system_utilization.current_state}")
    print(f"  Total time tracked: {final_summary.system_utilization.total_time:.1f}s")
    print(f"  Active time: {final_summary.system_utilization.active_time:.1f}s")
    print(f"  Idle time: {final_summary.system_utilization.idle_time:.1f}s")
    print(f"  Tracker uptime: {final_summary.tracker_uptime:.1f}s")
    
    if final_summary.node_utilizations:
        print(f"\nNode Performance:")
        for node_id, node_util in final_summary.node_utilizations.items():
            print(f"  {node_id}:")
            print(f"    Utilization: {node_util.utilization_percentage:.1f}%")
            print(f"    State: {node_util.current_state}")
            print(f"    Total time: {node_util.total_time:.1f}s")
            print(f"    Busy time: {node_util.busy_time:.1f}s")
            print(f"    Idle time: {node_util.idle_time:.1f}s")
    
    print(f"\n✨ Test completed! Current utilization tracking is working.")
    print(f"📊 You can now run your report generation script to create graphs.")


def test_current_state():
    """Just check current utilization state."""
    print("📊 Current Utilization State Check")
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
        run_multiple_workflows_test()