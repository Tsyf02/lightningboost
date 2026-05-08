def generate_tips(metrics_data):
    if metrics_data.get('ram_percent', 0) > 80:
        return [
            "Kill background browser processes",
            "Clear pip cache",
            "Offload current task to AMD Cloud"
        ]
    else:
        return [
            "System is optimal",
            "Ready for workloads"
        ]
