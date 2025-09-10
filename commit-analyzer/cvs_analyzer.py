#!/usr/bin/env python3
"""
CVS Commit Analyzer
Analyzes CVS logs to group related commits and export to Excel + HTML

Usage:
  Run directly, or build an executable with:
    pip install pyinstaller
    pyinstaller --onefile cvs_config.py
"""

import subprocess
import re
import json
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import os
import sys
from pathlib import Path
import webbrowser

class CVSLogParser:
    def __init__(self, cvs_root=None, module_path="."):
        self.cvs_root = cvs_root
        self.module_path = Path(module_path).resolve()
        self.log_entries = []
        self.grouped_commits = []
        self.output_dir = None

    def run_cvs_log(self, start_date=None, end_date=None, author=None):
        print("Extracting CVS logs...")
        cmd = ["cvs", "log"]
        if start_date and end_date:
            date_range = f"{start_date}<{end_date}"
            cmd.extend(["-d", date_range])
        if author:
            cmd.extend(["-w", author])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.module_path, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error running CVS command: {e}")
            print(f"Error output: {e.stderr}")
            return None
        except FileNotFoundError:
            print("Error: CVS command not found. Make sure CVS is installed and in PATH.")
            return None

    def parse_log_output(self, log_output):
        if not log_output:
            return []
        print("Parsing CVS log output...")
        entries = []
        current_file = None
        rcs_sections = re.split(r'^RCS file:', log_output, flags=re.MULTILINE)
        for section in rcs_sections[1:]:
            lines = section.strip().split('\n')
            if not lines:
                continue
            rcs_file = lines[0].strip()
            current_file = self.extract_filename(rcs_file)
            revision_pattern = r'^revision (\S+)'
            date_pattern = r'^date: ([^;]+);  author: ([^;]+);'
            i = 0
            while i < len(lines):
                line = lines[i]
                rev_match = re.match(revision_pattern, line)
                if rev_match:
                    revision = rev_match.group(1)
                    i += 1
                    if i < len(lines):
                        date_match = re.match(date_pattern, lines[i])
                        if date_match:
                            date_str = date_match.group(1).strip()
                            author = date_match.group(2).strip()
                            i += 1
                            comment_lines = []
                            while i < len(lines) and not re.match(r'^(revision|---)', lines[i]):
                                line_text = lines[i].strip()
                                if line_text and not re.match(r'^=+$', line_text):
                                    comment_lines.append(line_text)
                                i += 1
                            comment = ' '.join(comment_lines)
                            commit_date = None
                            date_formats = [
                                '%Y/%m/%d %H:%M:%S',
                                '%Y-%m-%d %H:%M:%S',
                                '%Y-%m-%d %H:%M:%S %z',
                                '%Y/%m/%d %H:%M:%S %z'
                            ]
                            for fmt in date_formats:
                                try:
                                    commit_date = datetime.strptime(date_str, fmt)
                                    break
                                except ValueError:
                                    continue
                            if not commit_date:
                                print(f"Warning: Could not parse date: {date_str}")
                                continue
                            entries.append({
                                'file': current_file,
                                'revision': revision,
                                'date': commit_date,
                                'author': author,
                                'comment': comment,
                                'raw_date_str': date_str
                            })
                i += 1
        print(f"Parsed {len(entries)} log entries")
        return entries

    def extract_filename(self, rcs_path):
        clean_path = rcs_path.replace('/RCS/', '/')
        if clean_path.endswith(',v'):
            clean_path = clean_path[:-2]
        return clean_path

    def group_commits(self, entries, time_window_minutes=10):
        print(f"Grouping commits within {time_window_minutes} minute windows...")
        sorted_entries = sorted(entries, key=lambda x: x['date'])
        groups = []
        current_group = []
        group_id = 1
        for entry in sorted_entries:
            if not current_group:
                current_group = [entry]
            else:
                last_entry = current_group[-1]
                time_diff = abs((entry['date'] - last_entry['date']).total_seconds() / 60)
                if (entry['author'] == last_entry['author'] and time_diff <= time_window_minutes):
                    current_group.append(entry)
                else:
                    if current_group:
                        groups.append({
                            'group_id': group_id,
                            'entries': current_group.copy(),
                            'start_time': min(e['date'] for e in current_group),
                            'end_time': max(e['date'] for e in current_group),
                            'author': current_group[0]['author'],
                            'file_count': len(current_group),
                            'files': [e['file'] for e in current_group]
                        })
                        group_id += 1
                    current_group = [entry]
        if current_group:
            groups.append({
                'group_id': group_id,
                'entries': current_group.copy(),
                'start_time': min(e['date'] for e in current_group),
                'end_time': max(e['date'] for e in current_group),
                'author': current_group[0]['author'],
                'file_count': len(current_group),
                'files': [e['file'] for e in current_group]
            })
        print(f"Created {len(groups)} commit groups")
        return groups

    def _prepare_output_dir(self):
        reports_root = Path("cvs-reports")
        reports_root.mkdir(exist_ok=True)
        timestamp_folder = reports_root / datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamp_folder.mkdir()
        self.output_dir = timestamp_folder
        return timestamp_folder

    def export_to_excel(self, groups, filename):
        print(f"Exporting to Excel: {filename}")
        rows = []
        for group in groups:
            comments = [e['comment'] for e in group['entries'] if e['comment']]
            common_comment = max(set(comments), key=comments.count) if comments else ""
            rows.append({
                'Group_ID': group['group_id'],
                'Date_Time': group['start_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'Author': group['author'],
                'File_Count': group['file_count'],
                'Duration_Minutes': (group['end_time'] - group['start_time']).total_seconds() / 60,
                'Files': '; '.join(group['files']),
                'Common_Comment': common_comment,
                'All_Comments': ' | '.join([e['comment'] for e in group['entries'] if e['comment']])
            })
        df = pd.DataFrame(rows)
        detailed_rows = []
        for group in groups:
            for entry in group['entries']:
                detailed_rows.append({
                    'Group_ID': group['group_id'],
                    'File': entry['file'],
                    'Revision': entry['revision'],
                    'Date_Time': entry['date'].strftime('%Y-%m-%d %H:%M:%S'),
                    'Author': entry['author'],
                    'Comment': entry['comment']
                })
        detailed_df = pd.DataFrame(detailed_rows)
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Commit_Groups', index=False)
            detailed_df.to_excel(writer, sheet_name='Detailed_Changes', index=False)
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        print(f"Excel file created: {filename}")
        return filename

    def export_to_html(self, groups, filename):
        print(f"Exporting HTML report: {filename}")
        html_parts = [
            "<html><head><meta charset='utf-8'>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            ".commit { border: 1px solid #ccc; border-radius: 8px; margin-bottom: 10px; }",
            ".header { background: #f0f0f0; padding: 8px; cursor: pointer; font-weight: bold; }",
            ".files { display: block; padding: 8px 20px; font-family: monospace; }",
            "button { margin: 5px; padding: 5px 10px; }",
            "</style>",
            "<script>",
            "function toggle(id) {",
            "  var el = document.getElementById(id);",
            "  el.style.display = (el.style.display === 'none') ? 'block' : 'none';",
            "}",
            "function expandAll() {",
            "  var els = document.getElementsByClassName('files');",
            "  for (var i=0; i<els.length; i++) els[i].style.display = 'block';",
            "}",
            "function collapseAll() {",
            "  var els = document.getElementsByClassName('files');",
            "  for (var i=0; i<els.length; i++) els[i].style.display = 'none';",
            "}",
            "</script></head>",
            "<body onload='expandAll()'>",
            "<h1>CVS Commit Report</h1>",
            "<button onclick='expandAll()'>Expand All</button>",
            "<button onclick='collapseAll()'>Collapse All</button>"
        ]
        for idx, group in enumerate(groups, 1):
            commit_time = group['start_time'].strftime('%Y-%m-%d %H:%M:%S')
            author = group['author']
            comments = [e['comment'] for e in group['entries'] if e['comment']]
            main_comment = max(set(comments), key=comments.count) if comments else ""
            header_text = f"[{commit_time}] {author} Comment: {main_comment}"
            files_html = "<br>".join(
                f"-- {entry['file']} (rev {entry['revision']})" for entry in group['entries']
            )
            html_parts.append("<div class='commit'>")
            html_parts.append(f"<div class='header' onclick=\"toggle('files{idx}')\">{header_text}</div>")
            html_parts.append(f"<div class='files' id='files{idx}'>{files_html}</div>")
            html_parts.append("</div>")
        html_parts.append("</body></html>")
        html_content = "\n".join(html_parts)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        webbrowser.open(f"file://{os.path.abspath(filename)}")
        print(f"HTML report created: {filename}")
        return filename

    def save_json_backup(self, groups, filename):
        print(f"Saving JSON backup: {filename}")
        json_groups = []
        for group in groups:
            json_group = group.copy()
            json_group['start_time'] = group['start_time'].isoformat()
            json_group['end_time'] = group['end_time'].isoformat()
            json_entries = []
            for entry in group['entries']:
                json_entry = entry.copy()
                json_entry['date'] = entry['date'].isoformat()
                json_entries.append(json_entry)
            json_group['entries'] = json_entries
            json_groups.append(json_group)
        with open(filename, 'w') as f:
            json.dump(json_groups, f, indent=2)
        print(f"JSON backup saved: {filename}")

    def analyze_repository(self, start_date=None, end_date=None, author=None, time_window=1, output_file=None):
        print("=== CVS Commit Analysis Started ===")
        log_output = self.run_cvs_log(start_date, end_date, author)
        if not log_output:
            print("Failed to get CVS logs. Exiting.")
            return None
        self.log_entries = self.parse_log_output(log_output)
        if not self.log_entries:
            print("No log entries found. Exiting.")
            return None
        self.grouped_commits = self.group_commits(self.log_entries, time_window)
        out_dir = self._prepare_output_dir()
        if not output_file:
            output_file = out_dir / "cvs_commit_analysis.xlsx"
        else:
            output_file = out_dir / output_file
        excel_file = self.export_to_excel(self.grouped_commits, output_file)
        json_file = out_dir / "cvs_analysis_backup.json"
        self.save_json_backup(self.grouped_commits, json_file)
        html_file = out_dir / "cvs_commit_report.html"
        self.export_to_html(self.grouped_commits, html_file)
        print("=== Analysis Complete ===")
        print(f"Total log entries: {len(self.log_entries)}")
        print(f"Commit groups created: {len(self.grouped_commits)}")
        print(f"Excel output: {excel_file}")
        print(f"JSON backup: {json_file}")
        print(f"HTML report: {html_file}")
        return excel_file

if __name__ == "__main__":
    analyzer = CVSLogParser()
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    result = analyzer.analyze_repository(
        start_date=start_date,
        end_date=end_date,
        time_window=10,
        output_file="cvs_commit_analysis.xlsx"
    )
