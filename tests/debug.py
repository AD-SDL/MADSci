"""
Session-based utilization report test script.
Tests the new session reporting functionality using only EventClient.
"""

import datetime
import time
from madsci.client.experiment_application import ExperimentApplication, ExperimentDesign
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.client.event_client import EventClient


class SessionReportExperimentApplication(ExperimentApplication):
    url = "http://localhost:8002/"
    experiment_design = ExperimentDesign(
        experiment_name="Session Report Test",
        experiment_description="Testing session-based utilization reporting",
    )


def create_multi_node_workflow():
    """Create workflow using multiple node types to test all tracked nodes."""
    return WorkflowDefinition(
        name="Multi-Node Session Test",
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
                "args": {},
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


def test_session_report_generation():
    """Test session-based utilization report generation."""
    print("Session-Based Utilization Report Test")
    print("=" * 45)
    
    client = EventClient(event_server_url="http://localhost:8001")
    client.logger.setLevel(10)
    
    # Test 1: Get current utilization state before workflow
    print("\n1. Checking current utilization state...")
    try:
        initial_summary = client.get_utilization_summary()
        print(f"   Current system utilization: {initial_summary.system_utilization.utilization_percentage:.1f}%")
        print(f"   Nodes tracked: {len(initial_summary.node_utilizations)}")
        
        if initial_summary.node_utilizations:
            print("   Node states:")
            for node_id, node_util in initial_summary.node_utilizations.items():
                print(f"     {node_id[-8:]}: {node_util.utilization_percentage:.1f}% ({node_util.current_state})")
    except Exception as e:
        print(f"   Error getting current state: {e}")
    
    # Test 2: Run a workflow to generate some activity
    print("\n2. Running workflow to generate activity...")
    experiment_application = SessionReportExperimentApplication()
    
    workflow = create_multi_node_workflow()
    workflow_start_time = datetime.datetime.now()
    
    try:
        with experiment_application.manage_experiment(
            run_name=f"session_test_{workflow_start_time.strftime('%H%M%S')}",
            run_description="Session report test workflow",
        ):
            experiment_application.workcell_client.start_workflow(workflow)
            time.sleep(20)  # Give workflow time to complete
        
        workflow_end_time = datetime.datetime.now()
        duration = (workflow_end_time - workflow_start_time).total_seconds()
        print(f"   Workflow completed in {duration:.1f} seconds")
        
    except Exception as e:
        print(f"   Workflow failed: {e}")
    
    # Test 3: Generate session-based utilization report (JSON)
    print("\n3. Generating session-based utilization report (JSON)...")
    try:
        report = client.get_utilization_report()
        
        if report and "error" not in report:
            metadata = report["report_metadata"]
            overall = report["overall_summary"]
            sessions = report["session_details"]
            
            print("   JSON Report Generated Successfully")
            print(f"   Analysis period: {metadata['analysis_duration_hours']:.1f} hours")
            print(f"   Total sessions: {metadata['total_sessions']}")
            print(f"   Average system utilization: {overall['average_system_utilization_percent']:.1f}%")
            print(f"   Nodes tracked: {overall['nodes_tracked']}")
            print(f"   Total experiments: {overall['total_experiments']}")
            print(f"   Total workflows: {overall['total_workflows']}")
            
            if sessions:
                print(f"\n   Session Details:")
                for session in sessions[-3:]:  # Show last 3 sessions
                    session_name = session.get("session_name", "Unknown")
                    print(f"     {session['session_type']}: {session_name}")
                    print(f"       Duration: {session['duration_hours']:.1f}h")
                    print(f"       Utilization: {session['system_utilization_percent']:.1f}%")
                    print(f"       Nodes active: {session['nodes_active']}")
                    
                    if session['node_utilizations']:
                        print(f"       Node details:")
                        for node_id, node_data in session['node_utilizations'].items():
                            display_name = node_data.get('display_name', node_id[-8:])
                            print(f"         {display_name}: {node_data['utilization_percent']:.1f}%")
        else:
            error_msg = report.get("error", "Unknown error") if report else "No response"
            print(f"   Report generation failed: {error_msg}")
            
    except Exception as e:
        print(f"   Error generating JSON report: {e}")
    
    # Test 4: Generate and save CSV report
    print("\n4. Generating and saving CSV report...")
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"session_utilization_report_{timestamp}.csv"
        
        success = client.save_utilization_csv(csv_filename)
        
        if success:
            print(f"   CSV report saved to: {csv_filename}")
            
            # Read first few lines to verify content
            try:
                with open(csv_filename, 'r') as f:
                    lines = f.readlines()[:10]
                    print(f"   CSV preview (first 10 lines):")
                    for i, line in enumerate(lines, 1):
                        print(f"     {i:2d}: {line.strip()}")
            except Exception as e:
                print(f"   Could not preview CSV: {e}")
        else:
            print("   Failed to save CSV report")
            
    except Exception as e:
        print(f"   Error generating CSV report: {e}")
    
    # Test 5: Generate report for specific timeframe
    print("\n5. Testing custom timeframe report...")
    try:
        # Get report for last 2 hours
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(hours=2)
        
        custom_report = client.get_utilization_report(
            start_time=start_time.isoformat() + "Z",
            end_time=end_time.isoformat() + "Z"
        )
        
        if custom_report and "error" not in custom_report:
            metadata = custom_report["report_metadata"]
            overall = custom_report["overall_summary"]
            
            print("   Custom timeframe report generated successfully")
            print(f"   Analysis period: {metadata['analysis_duration_hours']:.1f} hours")
            print(f"   Sessions in timeframe: {metadata['total_sessions']}")
            print(f"   Average utilization: {overall['average_system_utilization_percent']:.1f}%")
        else:
            error_msg = custom_report.get("error", "Unknown error") if custom_report else "No response"
            print(f"   Custom report failed: {error_msg}")
            
    except Exception as e:
        print(f"   Error generating custom timeframe report: {e}")
    
    # Test 6: Check final utilization state
    print("\n6. Checking final utilization state...")
    try:
        final_summary = client.get_utilization_summary()
        print(f"   Final system utilization: {final_summary.system_utilization.utilization_percentage:.1f}%")
        print(f"   Active time: {final_summary.system_utilization.active_time:.1f}s")
        
        if final_summary.node_utilizations:
            print("   Final node states:")
            sorted_nodes = sorted(
                final_summary.node_utilizations.items(),
                key=lambda x: x[1].utilization_percentage,
                reverse=True
            )
            
            for node_id, node_util in sorted_nodes:
                print(f"     {node_id[-8:]}: {node_util.utilization_percentage:.1f}% ({node_util.busy_time:.1f}s busy)")
                
    except Exception as e:
        print(f"   Error getting final state: {e}")
    
    print("\n" + "=" * 45)
    print("Session-based utilization test completed!")
    print("\nTest Summary:")
    print("- Workflow execution for activity generation")
    print("- JSON session report generation")
    print("- CSV report export and file saving")
    print("- Custom timeframe reporting")
    print("- Utilization state before/after comparison")


def test_report_only():
    """Test only the report generation without running workflows."""
    print("Session Report Generation Test (No Workflow)")
    print("=" * 45)
    
    client = EventClient(event_server_url="http://localhost:8001")
    
    # Generate session report from existing data
    print("\nGenerating session report from existing data...")
    try:
        report = client.get_utilization_report()
        
        if report and "error" not in report:
            metadata = report["report_metadata"]
            overall = report["overall_summary"]
            sessions = report["session_details"]
            
            print("Report Generated Successfully")
            print(f"  Analysis period: {metadata['analysis_start']} to {metadata['analysis_end']}")
            print(f"  Duration: {metadata['analysis_duration_hours']:.1f} hours")
            print(f"  Total sessions: {metadata['total_sessions']}")
            print(f"  Average system utilization: {overall['average_system_utilization_percent']:.1f}%")
            print(f"  Total runtime: {overall['total_system_runtime_hours']:.1f} hours")
            print(f"  Nodes tracked: {overall['nodes_tracked']}")
            
            if overall['node_summary']:
                print(f"\n  Top Node Utilizations:")
                sorted_nodes = sorted(
                    overall['node_summary'].items(),
                    key=lambda x: x[1]['average_utilization_percent'],
                    reverse=True
                )
                
                for node_id, node_data in sorted_nodes[:5]:  # Top 5
                    print(f"    {node_id[-8:]}: {node_data['average_utilization_percent']:.1f}% avg, {node_data['total_busy_time_hours']:.2f}h total")
            
            if sessions:
                print(f"\n  Recent Sessions:")
                for session in sessions[-5:]:  # Last 5 sessions
                    session_name = session.get("session_display_name", session.get("session_name", "Unknown"))
                    print(f"    {session['session_type']}: {session_name}")
                    print(f"      {session['duration_hours']:.1f}h, {session['system_utilization_percent']:.1f}% util, {session['nodes_active']} nodes")
        else:
            error_msg = report.get("error", "Unknown error") if report else "No response"
            print(f"Report generation failed: {error_msg}")
            
    except Exception as e:
        print(f"Error generating report: {e}")


if __name__ == "__main__":
    # import sys
    
    # if len(sys.argv) > 1 and sys.argv[1] == "report":
    #     test_report_only()
    # else:
    #     test_session_report_generation()
    from madsci.common.types.event_types import EventType
    client = EventClient()
    events = client.get_events(number=10000)
    
    for event_id, event in events.items():
        print(event.event_type)
        if event.event_type == EventType.WORKCELL_START:
            print(f"Processing event: {event_id}")
            

    print(len(events))
    report = client.get_utilization_report(

    )

    # Use the data
    if report and "error" not in report:
        print(f"System utilization: {report['overall_summary']['average_system_utilization_percent']:.1f}%")
        print(f"Sessions found: {report['report_metadata']['total_sessions']}")
        
        # Save to file if needed
        import json
        with open("report.json", "w") as f:
            json.dump(report, f, indent=2)