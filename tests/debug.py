"""Simple test script for CSV export functionality."""

from madsci.client.event_client import EventClient

# Initialize client
client = EventClient()

# Test 1: Basic utilization periods CSV export
saved_files = client.get_utilization_periods(
    analysis_type="daily",
    csv_export=True,
    save_to_file=True,
    output_path="./reports"
)
# print(f"Daily periods saved: {list(saved_files.keys())}")

# Test 2: User utilization report
user_file = client.get_user_utilization_report(
    csv_export=True,
    save_to_file=True,
    output_path="./reports"
)
# print(f"User report saved: {user_file}")

# Test 3: Time series analysis
time_series_files = client.get_time_series_analysis(
    analysis_type="weekly",
    csv_export=True,
    save_to_file=True,
    output_path="./reports"
)
# print(f"Time series saved: {list(time_series_files.keys())}")

# Test 4: User summary
user_summary_file = client.get_user_utilization_summary(
    csv_export=True,
    save_to_file=True,
    output_path="./reports"
)
# print(f"User summary saved: {user_summary_file}")

# Test 5: Basic utilization report
util_file = client.get_utilization_report(
    csv_export=True,
    save_to_file=True,
    output_path="./reports"
)
# print(f"Utilization report saved: {util_file}")

print("All CSV exports completed")