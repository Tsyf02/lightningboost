import psutil

def get_system_metrics():
    # interval=None allows fetching CPU usage immediately without blocking.
    # The first call will return 0.0, but subsequent calls return % since last call.
    cpu_percent = psutil.cpu_percent(interval=None)
    ram_info = psutil.virtual_memory()
    ram_percent = ram_info.percent
    
    status = "OK"
    if ram_percent > 80:
        status = "CRITICAL"
        
    return {
        "cpu_percent": cpu_percent,
        "ram_percent": ram_percent,
        "status": status
    }
