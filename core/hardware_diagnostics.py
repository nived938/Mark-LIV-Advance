"""Hardware diagnostics report.

No stress testing is performed automatically. The diagnostic action gathers
health/telemetry information and optionally queries smartctl when installed.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time


def _run(cmd: list[str], timeout: int = 12) -> str:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return (p.stdout or p.stderr or "").strip()
    except Exception as exc:
        return f"unavailable: {exc}"


def diagnostic_report(deep: bool = False) -> str:
    lines = [
        "J.A.R.V.I.S. HARDWARE DIAGNOSTICS",
        f"OS: {platform.platform()}",
        f"CPU: {os.cpu_count() or '?'} logical cores",
    ]

    try:
        import psutil
        lines.append(f"CPU load: {psutil.cpu_percent(interval=1):.1f}%")
        vm = psutil.virtual_memory()
        lines.append(
            f"RAM: {vm.percent:.1f}% used "
            f"({vm.used / (1024**3):.1f} GB / {vm.total / (1024**3):.1f} GB)"
        )

        try:
            battery = psutil.sensors_battery()
            if battery:
                lines.append(
                    f"Battery: {battery.percent:.0f}% "
                    f"({'charging' if battery.power_plugged else 'on battery'})"
                )
        except Exception:
            pass

        try:
            temps = psutil.sensors_temperatures()
            vals = []
            for entries in temps.values():
                for entry in entries:
                    if getattr(entry, "current", None) is not None:
                        vals.append(float(entry.current))
            if vals:
                lines.append(f"Temperature: min {min(vals):.1f}°C / max {max(vals):.1f}°C")
            else:
                lines.append("Temperature: unavailable from OS sensors")
        except Exception:
            lines.append("Temperature: unavailable from OS sensors")

        lines.append("DISKS:")
        for part in psutil.disk_partitions(all=False):
            try:
                usage = shutil.disk_usage(part.mountpoint)
                lines.append(
                    f"  {part.mountpoint}: {usage.free / (1024**3):.1f} GB free / "
                    f"{usage.total / (1024**3):.1f} GB total"
                )
            except Exception:
                continue
    except Exception as exc:
        lines.append(f"Telemetry error: {exc}")

    if platform.system() == "Windows":
        lines.append("WINDOWS DEVICE CHECK:")
        lines.append("  Physical disks:")
        disk = _run([
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-Command",
            "Get-CimInstance Win32_DiskDrive | "
            "Select-Object Model,Status,InterfaceType,Size | ConvertTo-Json -Compress"
        ])
        lines.append("  " + disk[:2500].replace("\r\n", " ") if disk else "  unavailable")

        battery = _run([
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-Command",
            "Get-CimInstance Win32_Battery | "
            "Select-Object Name,Status,EstimatedChargeRemaining,BatteryStatus | "
            "ConvertTo-Json -Compress"
        ])
        if battery:
            lines.append("  Battery detail: " + battery[:1200])

    if deep:
        smart = shutil.which("smartctl")
        if smart:
            scan = _run([smart, "--scan-open"], timeout=20)
            lines.append("SMART scan:")
            lines.append(scan[:3000] if scan else "No SMART devices reported.")
        else:
            lines.append("SMART: smartctl is not installed; skipped.")

    lines.append("Diagnostic collection complete. No stress test was run.")
    return "\n".join(lines)
