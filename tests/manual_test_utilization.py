from madsci.client.event_client import EventClient
import json

def example_usage():
    """Example usage of the time-series analysis."""
    
    client = EventClient()
    
    print("=== TIME-SERIES ANALYSIS EXAMPLES ===")
    
    # Example 1: Daily analysis (default - last 7 days)
    print("\n1. Daily analysis for last week:")
    daily_report = client.get_time_series_analysis()
    
    if daily_report:
        print(f"Peak utilization: {daily_report['key_metrics']['peak_utilization']:.1f}%")
        print(f"Average utilization: {daily_report['key_metrics']['average_utilization']:.1f}%")
        print(f"Total experiments: {daily_report['key_metrics']['total_experiments']}")
        print(f"Active days: {daily_report['key_metrics']['active_days']}/{daily_report['key_metrics']['total_analysis_days']}")
        
        # Show trend
        trend = daily_report['trends_analysis']['utilization_trend']
        print(f"Utilization trend: {trend['direction']} ({trend['change_percent']:+.1f}%)")
    
    # Example 2: Hourly analysis for today
    print("\n2. Hourly analysis for today:")
    from datetime import datetime, timezone
    
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = datetime.now(timezone.utc)
    
    hourly_report = client.get_time_series_analysis(
        start_time=today_start.isoformat().replace('+00:00', 'Z'),
        end_time=today_end.isoformat().replace('+00:00', 'Z'),
        analysis_type="hourly"
    )
    
    if hourly_report:
        print(f"Today's peak utilization: {hourly_report['key_metrics']['peak_utilization']:.1f}%")
        print(f"Experiments today: {hourly_report['key_metrics']['total_experiments']}")
        
        # Show busiest hours
        busiest = hourly_report['trends_analysis']['busiest_periods']['highest_utilization']
        if busiest:
            print("Busiest hours today:")
            for period in busiest[:3]:
                hour = period['timestamp'].split('T')[1][:5]  # Extract HH:MM
                print(f"  {hour}: {period['system_utilization']:.1f}% utilization")
    
    # Example 3: Weekly analysis for last month
    print("\n3. Weekly analysis for last month:")
    from datetime import timedelta
    
    month_end = datetime.now(timezone.utc)
    month_start = month_end - timedelta(days=30)
    
    weekly_report = client.get_time_series_analysis(
        start_time=month_start.isoformat().replace('+00:00', 'Z'),
        end_time=month_end.isoformat().replace('+00:00', 'Z'),
        analysis_type="weekly"
    )
    
    if weekly_report:
        print(f"Monthly peak utilization: {weekly_report['key_metrics']['peak_utilization']:.1f}%")
        print(f"Total experiments this month: {weekly_report['key_metrics']['total_experiments']}")
        
        # Show weekly trend
        trend = weekly_report['trends_analysis']['utilization_trend']
        print(f"Monthly trend: {trend['direction']} ({trend['change_percent']:+.1f}%)")
    
    # Example 4: Save detailed report
    print("\n4. Saving detailed report...")
    if daily_report:
        with open("time_series_report.json", "w") as f:
            json.dump(daily_report, f, indent=2)
        print("Detailed report saved to time_series_report.json")

def analyze_system_performance():
    """More advanced analysis using time-series data."""
    
    client = EventClient()
    
    # Get weekly data for analysis
    weekly_report = client.get_time_series_analysis(analysis_type="weekly")
    
    if not weekly_report:
        print("Could not get weekly report")
        return
    
    print("=== SYSTEM PERFORMANCE ANALYSIS ===")
    
    # Overall performance
    key_metrics = weekly_report['key_metrics']
    print(f"\nSystem Overview:")
    print(f"  Peak utilization: {key_metrics['peak_utilization']:.1f}%")
    print(f"  Average utilization: {key_metrics['average_utilization']:.1f}%")
    print(f"  Total experiments: {key_metrics['total_experiments']}")
    print(f"  Active periods: {key_metrics['active_days']}/{key_metrics['total_analysis_days']}")
    
    # Node performance
    aggregated = weekly_report['aggregated_summary']
    node_performance = aggregated.get('node_performance', {})
    
    print(f"\nNode Performance:")
    for node_id, metrics in node_performance.items():
        print(f"  Node {node_id[-8:]}:")
        print(f"    Average utilization: {metrics['average_utilization_percent']:.1f}%")
        print(f"    Peak utilization: {metrics['peak_utilization_percent']:.1f}%")
        print(f"    Total busy time: {metrics['total_busy_hours']:.2f} hours")
    
    # Trend analysis
    trends = weekly_report['trends_analysis']
    util_trend = trends['utilization_trend']
    exp_trend = trends['experiment_trend']
    
    print(f"\nTrends:")
    print(f"  Utilization: {util_trend['direction']} ({util_trend['change_percent']:+.1f}%)")
    print(f"  Experiments: {exp_trend['direction']} ({exp_trend['change_percent']:+.1f}%)")
    
    # Recommendations
    print(f"\nRecommendations:")
    if key_metrics['average_utilization'] < 10:
        print("  - System utilization is low. Consider consolidating workloads.")
    elif key_metrics['average_utilization'] > 80:
        print("  - System utilization is high. Consider adding more nodes.")
    
    if util_trend['direction'] == 'increasing':
        print("  - Utilization is trending up. Monitor for capacity needs.")
    elif util_trend['direction'] == 'decreasing':
        print("  - Utilization is trending down. Investigate efficiency opportunities.")

def test_basic_functionality():
    """Test basic functionality step by step."""
    
    print("=== SIMPLE FUNCTIONALITY TEST ===")
    
    client = EventClient()
    
    # Test 4: Try lightweight summary (if implemented)
    print("\n4. Testing lightweight summary...")
    report = client.get_utilization_periods(analysis_type="daily")
    with open("summary_report.json", "w") as f:
        json.dump(report, f, indent=2)

def test_timezone_awareness():
    """Test timezone functionality."""
    
    print("\n=== TIMEZONE TEST ===")
    
    from datetime import datetime, timezone
    import pytz
    
    # Test timezone conversion
    print("\n1. Testing timezone conversion...")
    
    utc_now = datetime.now(timezone.utc)
    print(f"UTC time: {utc_now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Convert to Chicago time
    chicago_tz = pytz.timezone('America/Chicago')
    chicago_time = utc_now.astimezone(chicago_tz)
    print(f"Chicago time: {chicago_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Test with client (if timezone support added)
    client = EventClient()
    
    print("\n2. Testing timezone-aware analysis...")
    try:
        if hasattr(client, 'get_time_series_analysis'):
            # Test with explicit timezone
            ts_report = client.get_time_series_analysis(
                analysis_type="daily",
                user_timezone="America/Chicago"
            )
            
            if ts_report and 'display_settings' in ts_report:
                tz = ts_report['display_settings'].get('user_timezone', 'Not set')
                print(f"✅ Timezone support working: {tz}")
            else:
                print("⚠️  Timezone support not fully implemented")
        else:
            print("⚠️  Time-series analysis not available for timezone test")
    except Exception as e:
        print(f"❌ Timezone test error: {e}")

def quick_performance_test():
    """Quick performance comparison."""
    
    print("\n=== PERFORMANCE TEST ===")
    
    import time
    client = EventClient()
    
    # Test existing session report speed
    print("\n1. Testing session report speed...")
    start_time = time.time()
    try:
        session_report = client.get_utilization_report()
        session_time = time.time() - start_time
        print(f"✅ Session report: {session_time:.2f} seconds")
    except Exception as e:
        print(f"❌ Session report failed: {e}")
    
    # Test time-series analysis speed (if available)
    print("\n2. Testing time-series analysis speed...")
    start_time = time.time()
    try:
        if hasattr(client, 'get_time_series_analysis'):
            ts_report = client.get_time_series_analysis(analysis_type="daily")
            ts_time = time.time() - start_time
            print(f"✅ Time-series analysis: {ts_time:.2f} seconds")
        else:
            print("⚠️  Time-series analysis not implemented")
    except Exception as e:
        print(f"❌ Time-series analysis failed: {e}")
    
    # Test lightweight summary speed (if available)
    print("\n3. Testing lightweight summary speed...")
    start_time = time.time()
    try:
        if hasattr(client, 'get_utilization_summary'):
            summary = client.get_utilization_summary(analysis_type="daily")
            summary_time = time.time() - start_time
            print(f"✅ Lightweight summary: {summary_time:.2f} seconds")
        else:
            print("⚠️  Lightweight summary not implemented")
    except Exception as e:
        print(f"❌ Lightweight summary failed: {e}")

def test_what_you_have_now():
    """Test just what you currently have implemented."""
    
    print("=== TESTING CURRENT IMPLEMENTATION ===")
    
    client = EventClient()
    
    # Test your existing time-series function
    print("\nTesting get_time_series_analysis()...")
    try:
        report = client.get_time_series_analysis(analysis_type="daily")
        
        if report:
            print("✅ get_time_series_analysis() working!")
            
            # Extract key info
            key_metrics = report.get('key_metrics', {})
            peak_util = key_metrics.get('peak_utilization', 0)
            avg_util = key_metrics.get('average_utilization', 0)
            total_exp = key_metrics.get('total_experiments', 0)
            active_days = key_metrics.get('active_days', 0)
            total_days = key_metrics.get('total_analysis_days', 0)
            
            print(f"Peak utilization: {peak_util:.1f}%")
            print(f"Average utilization: {avg_util:.1f}%")
            print(f"Total experiments: {total_exp}")
            print(f"Active days: {active_days}/{total_days}")
            
            # Check for timezone issues
            if active_days < 2 and total_exp > 100:
                print("⚠️  POTENTIAL TIMEZONE ISSUE: High experiments but low active days")
                print("   This suggests experiments might be spanning UTC midnight")
            
        else:
            print("❌ get_time_series_analysis() returned no data")
            
    except Exception as e:
        print(f"❌ get_time_series_analysis() failed: {e}")

if __name__ == "__main__":
    # Run the test that matches your current setup
    test_what_you_have_now()
    
    print("\n" + "="*50)
    
    # Run other tests
    test_basic_functionality()
    # test_timezone_awareness()
    # quick_performance_test()
    
    # example_usage()
    # print("\n" + "="*50 + "\n")
    # analyze_system_performance()
    # client = EventClient()
    # report = client.get_utilization_report(

    # )

    # # Use the data
    # if report and "error" not in report:
    #     print(f"System utilization: {report['overall_summary']['average_system_utilization_percent']:.1f}%")
    #     print(f"Sessions found: {report['report_metadata']['total_sessions']}")
        
    #     # Save to file if needed
    #     import json
    #     with open("report.json", "w") as f:
    #         json.dump(report, f, indent=2)