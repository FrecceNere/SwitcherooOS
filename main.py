#!/usr/bin/env python3

import subprocess
import requests
import json
import re
import sys
import platform
import time
import gui.gui
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlencode
from bs4 import BeautifulSoup

try:
    import wmi
    HAS_WMI = True
except ImportError:
    HAS_WMI = False

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

@dataclass
class HardwareComponent:
    type: str
    vendor: str
    model: str
    device_id: Optional[str] = None
    vendor_id: Optional[str] = None
    driver: Optional[str] = None
    windows_name: Optional[str] = None

class LinuxHardwareAPI:
    def __init__(self):
        self.base_url = "https://linux-hardware.org"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LinuxMigrationTool (https://github.com/FrecceNere/windows-to-linux-migrator)'
        })
        self.cache = {}

    def search_hardware(self, vendor_id: str, device_id: str) -> Dict:
        cache_key = f"{vendor_id}:{device_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        search_url = f"{self.base_url}/index.php"
        params = {
            'view': 'search',
            'vendor_id': vendor_id,
            'device_id': device_id
        }

        try:
            response = self.session.get(search_url, params=params, timeout=10)
            if response.status_code == 200:
                result = self._parse_search_results(response.text)
                self.cache[cache_key] = result
                return result
        except Exception:
            pass

        return {'status': 'unknown', 'compatibility': 'unknown'}

    def _parse_search_results(self, html: str) -> Dict:
        try:
            soup = BeautifulSoup(html, 'html.parser')

            status_indicators = {
                'works': ['works', 'supported', 'ok', 'yes'],
                'partial': ['partial', 'limited', 'issues'],
                'broken': ['broken', 'unsupported', 'no', 'failed']
            }

            text_content = soup.get_text().lower()

            for status, indicators in status_indicators.items():
                if any(indicator in text_content for indicator in indicators):
                    return {
                        'status': 'found',
                        'compatibility': status,
                        'source': 'linux-hardware.org'
                    }

            return {'status': 'unknown', 'compatibility': 'unknown'}

        except Exception:
            return {'status': 'error', 'compatibility': 'unknown'}

class WindowsHardwareDetector:
    def __init__(self):
        self.api = LinuxHardwareAPI()
        if HAS_WMI:
            self.wmi_conn = wmi.WMI()

    def detect_hardware(self) -> List[HardwareComponent]:
        components = []

        if HAS_WMI:
            components.extend(self._detect_wmi())
        else:
            components.extend(self._detect_powershell())

        return self._deduplicate_components(components)

    def _detect_wmi(self) -> List[HardwareComponent]:
        components = []

        try:
            for gpu in self.wmi_conn.Win32_VideoController():
                if gpu.Name and "Basic Display" not in gpu.Name:
                    vendor_id, device_id = self._parse_pci_ids(gpu.PNPDeviceID)
                    components.append(HardwareComponent(
                        type="GPU",
                        vendor=self._extract_vendor(gpu.Name),
                        model=gpu.Name,
                        device_id=device_id,
                        vendor_id=vendor_id,
                        driver=gpu.DriverVersion,
                        windows_name=gpu.Name
                    ))

            for adapter in self.wmi_conn.Win32_NetworkAdapter():
                if adapter.Name and adapter.PNPDeviceID and "ROOT\\" not in adapter.PNPDeviceID:
                    vendor_id, device_id = self._parse_pci_ids(adapter.PNPDeviceID)
                    adapter_type = "WiFi" if any(x in adapter.Name.lower() for x in ["wireless", "wifi", "802.11"]) else "Network"
                    components.append(HardwareComponent(
                        type=adapter_type,
                        vendor=self._extract_vendor(adapter.Name),
                        model=adapter.Name,
                        device_id=device_id,
                        vendor_id=vendor_id,
                        windows_name=adapter.Name
                    ))

            for audio in self.wmi_conn.Win32_SoundDevice():
                if audio.Name and audio.PNPDeviceID:
                    vendor_id, device_id = self._parse_pci_ids(audio.PNPDeviceID)
                    components.append(HardwareComponent(
                        type="Audio",
                        vendor=self._extract_vendor(audio.Name),
                        model=audio.Name,
                        device_id=device_id,
                        vendor_id=vendor_id,
                        windows_name=audio.Name
                    ))

            for cpu in self.wmi_conn.Win32_Processor():
                if cpu.Name:
                    components.append(HardwareComponent(
                        type="CPU",
                        vendor=cpu.Manufacturer or "Unknown",
                        model=cpu.Name,
                        windows_name=cpu.Name
                    ))

        except Exception:
            pass

        return components

    def _detect_powershell(self) -> List[HardwareComponent]:
        components = []
        commands = [
            ("GPU", "Get-WmiObject Win32_VideoController | Select-Object Name, PNPDeviceID"),
            ("Network", "Get-WmiObject Win32_NetworkAdapter | Select-Object Name, PNPDeviceID"),
            ("Audio", "Get-WmiObject Win32_SoundDevice | Select-Object Name, PNPDeviceID"),
            ("CPU", "Get-WmiObject Win32_Processor | Select-Object Name, Manufacturer")
        ]

        for hw_type, command in commands:
            try:
                result = subprocess.run([
                    "powershell", "-Command", command
                ], capture_output=True, text=True, timeout=15)

                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n')[2:]:
                        if line.strip():
                            name = line.split()[0] if line.split() else "Unknown"
                            components.append(HardwareComponent(
                                type=hw_type,
                                vendor=self._extract_vendor(name),
                                model=name,
                                windows_name=name
                            ))
            except Exception:
                continue

        return components

    def _parse_pci_ids(self, pnp_device_id: str) -> Tuple[Optional[str], Optional[str]]:
        if not pnp_device_id:
            return None, None

        ven_match = re.search(r'VEN_([0-9A-F]{4})', pnp_device_id)
        dev_match = re.search(r'DEV_([0-9A-F]{4})', pnp_device_id)

        vendor_id = ven_match.group(1).lower() if ven_match else None
        device_id = dev_match.group(1).lower() if dev_match else None

        return vendor_id, device_id

    def _extract_vendor(self, name: str) -> str:
        if not name:
            return "Unknown"

        vendor_map = {
            "NVIDIA": "NVIDIA",
            "AMD": "AMD",
            "Intel": "Intel",
            "Realtek": "Realtek",
            "Broadcom": "Broadcom",
            "Qualcomm": "Qualcomm",
            "Microsoft": "Microsoft"
        }

        name_upper = name.upper()
        for vendor, normalized in vendor_map.items():
            if vendor.upper() in name_upper:
                return normalized

        return name.split()[0] if name.split() else "Unknown"

    def _deduplicate_components(self, components: List[HardwareComponent]) -> List[HardwareComponent]:
        seen = set()
        unique_components = []

        for comp in components:
            key = (comp.type, comp.vendor, comp.model)
            if key not in seen:
                seen.add(key)
                unique_components.append(comp)

        return unique_components

    def check_compatibility(self, component: HardwareComponent) -> Dict:
        if component.vendor_id and component.device_id:
            result = self.api.search_hardware(component.vendor_id, component.device_id)
            if result['status'] != 'unknown':
                return result

        return self._fallback_compatibility_check(component)

    def _fallback_compatibility_check(self, component: HardwareComponent) -> Dict:
        compatibility_db = {
            'intel': {'status': 'works', 'notes': 'Excellent native support'},
            'amd': {'status': 'works', 'notes': 'Good open source drivers'},
            'nvidia': {'status': 'partial', 'notes': 'Requires proprietary drivers'},
            'realtek': {'status': 'works', 'notes': 'Generally well supported'},
            'broadcom': {'status': 'partial', 'notes': 'May require proprietary drivers'},
            'qualcomm': {'status': 'partial', 'notes': 'Mixed support'},
            'microsoft': {'status': 'works', 'notes': 'Basic compatibility'}
        }

        vendor_lower = component.vendor.lower()

        for vendor_key, compat_info in compatibility_db.items():
            if vendor_key in vendor_lower:
                return {
                    'status': 'estimated',
                    'compatibility': compat_info['status'],
                    'notes': compat_info['notes'],
                    'source': 'fallback_db'
                }

        return {
            'status': 'unknown',
            'compatibility': 'unknown',
            'notes': 'Manual verification recommended'
        }

class CompatibilityChecker:
    def __init__(self):
        self.detector = WindowsHardwareDetector()

    def run_check(self) -> Dict:
        if platform.system() != "Windows":
            print("ERROR: This software must be run on Windows!")
            sys.exit(1)

        print("Linux Hardware Compatibility Checker")
        print("=" * 50)

        components = self.detector.detect_hardware()

        if not components:
            print("No hardware components detected!")
            return {}

        print(f"Detected {len(components)} hardware components")

        report = self._generate_report(components)
        self._display_results(report)
        self._save_reports(report)

        return report

    def _generate_report(self, components: List[HardwareComponent]) -> Dict:
        report = {
            'system_info': {
                'os': platform.system(),
                'version': platform.version(),
                'architecture': platform.architecture()[0],
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            },
            'summary': {
                'total': len(components),
                'compatible': 0,
                'partial': 0,
                'incompatible': 0,
                'unknown': 0
            },
            'components': []
        }

        print("\nChecking Linux compatibility...")

        for i, component in enumerate(components, 1):
            print(f"[{i:2d}/{len(components)}] {component.type}: {component.model[:60]}")

            compatibility = self.detector.check_compatibility(component)

            component_data = {
                'type': component.type,
                'vendor': component.vendor,
                'model': component.model,
                'vendor_id': component.vendor_id,
                'device_id': component.device_id,
                'compatibility': compatibility
            }

            report['components'].append(component_data)

            status = compatibility.get('compatibility', 'unknown')
            report['summary'][self._map_status(status)] += 1

            print(f"         {self._get_status_symbol(status)} {status.title()}")

            time.sleep(0.1)

        return report

    def _map_status(self, status: str) -> str:
        mapping = {
            'works': 'compatible',
            'partial': 'partial',
            'broken': 'incompatible'
        }
        return mapping.get(status, 'unknown')

    def _get_status_symbol(self, status: str) -> str:
        symbols = {
            'works': '[OK]',
            'partial': '[WARN]',
            'broken': '[FAIL]',
            'unknown': '[?]'
        }
        return symbols.get(status, '[?]')

    def _display_results(self, report: Dict):
        print("\n" + "=" * 50)
        print("COMPATIBILITY RESULTS")
        print("=" * 50)

        summary = report['summary']
        total = summary['total']

        print(f"Total components:     {total}")
        print(f"Compatible:          {summary['compatible']:3d}")
        print(f"Partial support:     {summary['partial']:3d}")
        print(f"Incompatible:        {summary['incompatible']:3d}")
        print(f"Unknown:             {summary['unknown']:3d}")

        if total > 0:
            compat_score = ((summary['compatible'] + summary['partial'] * 0.5) / total) * 100
            print(f"\nCompatibility Score: {compat_score:.1f}%")

            if compat_score >= 90:
                print("Status: Excellent - Ready for Linux migration")
            elif compat_score >= 75:
                print("Status: Good - Minor issues possible")
            elif compat_score >= 50:
                print("Status: Fair - Some components may need attention")
            else:
                print("Status: Poor - Significant compatibility issues")

        problematic = [
            comp for comp in report['components']
            if comp['compatibility']['compatibility'] in ['broken', 'partial', 'unknown']
        ]

        if problematic:
            print(f"\nComponents requiring attention ({len(problematic)}):")
            print("-" * 40)
            for comp in problematic:
                status = comp['compatibility']['compatibility']
                print(f"{self._get_status_symbol(status)} {comp['type']}: {comp['model']}")
                notes = comp['compatibility'].get('notes', 'No additional information')
                print(f"    Notes: {notes}")
        else:
            print("\nNo problematic components detected!")

    def _save_reports(self, report: Dict):
        with open('linux_compatibility_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        with open('linux_compatibility_report.txt', 'w') as f:
            f.write("LINUX HARDWARE COMPATIBILITY REPORT\n")
            f.write("=" * 50 + "\n\n")

            f.write(f"System: {report['system_info']['os']} {report['system_info']['version']}\n")
            f.write(f"Architecture: {report['system_info']['architecture']}\n")
            f.write(f"Generated: {report['system_info']['timestamp']}\n\n")

            summary = report['summary']
            f.write("SUMMARY:\n")
            f.write(f"  Total: {summary['total']}\n")
            f.write(f"  Compatible: {summary['compatible']}\n")
            f.write(f"  Partial: {summary['partial']}\n")
            f.write(f"  Incompatible: {summary['incompatible']}\n")
            f.write(f"  Unknown: {summary['unknown']}\n\n")

            f.write("COMPONENTS:\n")
            f.write("-" * 30 + "\n")

            for comp in report['components']:
                f.write(f"\n{comp['type']}: {comp['model']}\n")
                f.write(f"  Vendor: {comp['vendor']}\n")
                if comp['vendor_id'] and comp['device_id']:
                    f.write(f"  Hardware ID: {comp['vendor_id']}:{comp['device_id']}\n")
                f.write(f"  Compatibility: {comp['compatibility']['compatibility']}\n")
                f.write(f"  Notes: {comp['compatibility'].get('notes', 'N/A')}\n")

        print(f"\nReports saved:")
        print(f"  - linux_compatibility_report.json")
        print(f"  - linux_compatibility_report.txt")

def main():
    checker = CompatibilityChecker()
    checker.run_check()

if __name__ == "__main__":
    main()
