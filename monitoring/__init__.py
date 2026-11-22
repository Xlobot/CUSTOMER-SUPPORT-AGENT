"""
monitoring package for NetCare AI.
"""

from monitoring.temporary_logs import log_event, get_temporary_logs, clear_temporary_logs
from monitoring.server_status import record_request, get_server_status, get_formatted_uptime
