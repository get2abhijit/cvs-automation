#!/usr/bin/env python3
"""
CVS Commit Manager - PySide6 GUI (complete)

Place next to your cvs_analyzer.py (the module with CVSLogParser).
Run with:
    python gui_pyside6.py

Packaging (Windows):
    pip install pyinstaller
    pyinstaller --noconfirm --onefile --add-data "cvs_analyzer.py;." gui_pyside6.py

Notes:
- This app calls CVSLogParser(module_path=...) and expects it to set .grouped_commits and .output_dir in analyze_repository().
- The GUI ensures end_date includes today's commits (it shifts end_date +1 day before calling cvs log).
"""

import subprocess
import sys
import os
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QSpinBox, QMessageBox, QProgressBar, QCheckBox, QComboBox
)

# Attempt to import your analyzer module
try:
    from cvs_analyzer import CVSLogParser  # expects the analyzer file to be next to this GUI
except Exception as e:
    CVSLogParser = None
    IMPORT_ERROR = e
else:
    IMPORT_ERROR = None


class AnalyzerThread(QThread):
    """
    Runs the analysis in background to keep UI responsive.
    Emits:
      finished_signal(groups:list, outdir:str)
      error_signal(message:str)
      log_signal(message:str)
      started_signal()
      canceled_signal()
    """
    finished_signal = Signal(object, str)
    error_signal = Signal(str)
    log_signal = Signal(str)
    started_signal = Signal()
    canceled_signal = Signal()

    def __init__(self, module_path: str, start_date: str, end_date: str,
                 author: Optional[str], window: int, output_filename: str):
        super().__init__()
        self.module_path = module_path
        self.start_date = start_date
        self.end_date = end_date
        self.author = author
        self.window = window
        self.output_filename = output_filename
        self._cancel_requested = False

    def request_cancel(self):
        self._cancel_requested = True

    def run(self):
        if CVSLogParser is None:
            self.error_signal.emit(f"cvs_analyzer import failed: {IMPORT_ERROR}")
            return

        try:
            self.started_signal.emit()
            self.log_signal.emit(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting analyzer...")

            analyzer = CVSLogParser(module_path=self.module_path)

            # Make sure end_date includes the whole day: add +1 day
            try:
                end_dt = datetime.strptime(self.end_date, '%Y-%m-%d')
                end_dt_plus = end_dt + timedelta(days=1)
                end_str = end_dt_plus.strftime('%Y-%m-%d')
            except Exception:
                # fallback: pass through
                end_str = self.end_date

            # The analyzer does not provide progress callbacks; we log major steps.
            self.log_signal.emit("Running CVS log & parsing (this may take a while for large repos)...")

            # Call analyze_repository. This will run CVS commands and create output files.
            # We can't cancel subprocess easily here; but we respect pre-cancel request.
            if self._cancel_requested:
                self.canceled_signal.emit()
                return

            analyzer.analyze_repository(
                start_date=self.start_date,
                end_date=end_str,
                author=self.author,
                time_window=self.window,
                output_file=self.output_filename
            )

            if self._cancel_requested:
                self.canceled_signal.emit()
                return

            groups = getattr(analyzer, 'grouped_commits', [])
            out_dir = str(getattr(analyzer, 'output_dir', '') or '')
            self.log_signal.emit("Analysis finished.")
            self.finished_signal.emit(groups, out_dir)
        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            self.error_signal.emit(f"{str(exc)}\n\n{tb}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CVS Commit Manager")
        self.resize(1100, 700)

        # central widget
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)
        self.setCentralWidget(w)

        # Top row: workspace path and controls
        top_row = QHBoxLayout()
        layout.addLayout(top_row)

        top_row.addWidget(QLabel("Workspace path:"))
        self.path_edit = QLineEdit(str(Path('.').resolve()))
        top_row.addWidget(self.path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.on_browse)
        top_row.addWidget(browse_btn)

        top_row.addWidget(QLabel("Days:"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 36500)
        self.days_spin.setValue(30)
        top_row.addWidget(self.days_spin)

        top_row.addWidget(QLabel("Window (min):"))
        self.window_spin = QSpinBox()
        self.window_spin.setRange(1, 120)
        self.window_spin.setValue(10)
        top_row.addWidget(self.window_spin)

        top_row.addWidget(QLabel("Author (opt):"))
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("username (leave empty for all)")
        top_row.addWidget(self.author_edit)

        self.run_btn = QPushButton("Run Analysis")
        self.run_btn.clicked.connect(self.on_run)
        top_row.addWidget(self.run_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.on_cancel)
        top_row.addWidget(self.cancel_btn)

        # Status / progress / small logger
        status_row = QHBoxLayout()
        layout.addLayout(status_row)

        self.status_label = QLabel("Ready")
        status_row.addWidget(self.status_label, 2)

        self.pb = QProgressBar()
        self.pb.setRange(0, 0)  # indeterminate until finished
        self.pb.setVisible(False)
        status_row.addWidget(self.pb, 1)

        # Main area: tree + details + actions
        main_row = QHBoxLayout()
        layout.addLayout(main_row, 1)

        # Left: tree
        left_col = QVBoxLayout()
        main_row.addLayout(left_col, 2)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Commit / Files (rev)"])
        self.tree.itemSelectionChanged.connect(self.on_selection_changed)
        left_col.addWidget(self.tree)

        tree_btn_row = QHBoxLayout()
        left_col.addLayout(tree_btn_row)
        expand_all_btn = QPushButton("Expand All")
        expand_all_btn.clicked.connect(self.tree.expandAll)
        tree_btn_row.addWidget(expand_all_btn)
        collapse_all_btn = QPushButton("Collapse All")
        collapse_all_btn.clicked.connect(self.tree.collapseAll)
        tree_btn_row.addWidget(collapse_all_btn)
        refresh_btn = QPushButton("Refresh Tree (re-open last report)")
        refresh_btn.clicked.connect(self.on_refresh_tree)
        tree_btn_row.addWidget(refresh_btn)

        # Right: details + logger + file actions
        right_col = QVBoxLayout()
        main_row.addLayout(right_col, 1)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        right_col.addWidget(self.detail_text, 2)

        action_row = QHBoxLayout()
        right_col.addLayout(action_row)

        open_html_btn = QPushButton("Open HTML Report")
        open_html_btn.clicked.connect(self.on_open_html)
        action_row.addWidget(open_html_btn)

        open_folder_btn = QPushButton("Open Output Folder")
        open_folder_btn.clicked.connect(self.on_open_folder)
        action_row.addWidget(open_folder_btn)

        open_excel_btn = QPushButton("Open Excel")
        open_excel_btn.clicked.connect(self.on_open_excel)
        action_row.addWidget(open_excel_btn)

        # Logger area
        right_col.addWidget(QLabel("Log / Console:"))
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        right_col.addWidget(self.log_console, 1)

        # Internal state
        self.thread: Optional[AnalyzerThread] = None
        self.last_outdir: Optional[str] = None
        self.last_groups = []

        # If import failed, disable run
        if CVSLogParser is None:
            self.run_btn.setEnabled(False)
            self.status_label.setText(f"cvs_analyzer import failed: {IMPORT_ERROR}")

    @Slot()
    def on_browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select workspace directory", str(Path('.').resolve()))
        if d:
            self.path_edit.setText(d)

    @Slot()
    def on_run(self):
        # Validate path
        path = self.path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "No path", "Please specify a workspace directory.")
            return
        p = Path(path)
        if not p.exists():
            QMessageBox.warning(self, "Path not found", f"Path does not exist:\n{path}")
            return

        # Prepare parameters
        days = int(self.days_spin.value())
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)
        start_str = start_dt.strftime('%Y-%m-%d')
        end_str = end_dt.strftime('%Y-%m-%d')  # the thread will add +1 day

        author = self.author_edit.text().strip() or None
        window = int(self.window_spin.value())

        # UI state
        self.status_label.setText("Starting analysis...")
        self.pb.setVisible(True)
        self.cancel_btn.setEnabled(True)
        self.run_btn.setEnabled(False)
        self.log_console.clear()
        self.tree.clear()
        self.detail_text.clear()

        # Start thread
        self.thread = AnalyzerThread(
            module_path=str(p),
            start_date=start_str,
            end_date=end_str,
            author=author,
            window=window,
            output_filename="cvs_commit_analysis.xlsx"
        )
        self.thread.started_signal.connect(lambda: self.append_log("Worker started."))
        self.thread.log_signal.connect(self.append_log)
        self.thread.finished_signal.connect(self.on_analysis_finished)
        self.thread.error_signal.connect(self.on_analysis_error)
        self.thread.canceled_signal.connect(self.on_analysis_canceled)
        self.thread.start()

    @Slot()
    def on_cancel(self):
        if self.thread and self.thread.isRunning():
            res = QMessageBox.question(self, "Cancel", "Request cancel? This attempts to stop the analysis. Subprocesses may still run.")
            if res == QMessageBox.Yes:
                self.thread.request_cancel()
                self.append_log("Cancel requested...")

    @Slot(object, str)
    def on_analysis_finished(self, groups, outdir):
        self.last_groups = groups or []
        self.last_outdir = outdir or ''
        self.append_log("Worker finished successfully.")
        self.pb.setVisible(False)
        self.cancel_btn.setEnabled(False)
        self.run_btn.setEnabled(True)
        self.status_label.setText("Finished")

        # Populate tree
        self._populate_tree_from_groups(self.last_groups)
        if self.last_outdir:
            self.append_log(f"Output saved to: {self.last_outdir}")

    @Slot()
    def on_analysis_canceled(self):
        self.append_log("Analysis canceled.")
        self.pb.setVisible(False)
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Canceled")

    @Slot(str)
    def on_analysis_error(self, message):
        self.append_log(f"ERROR: {message}")
        QMessageBox.critical(self, "Analysis error", message)
        self.pb.setVisible(False)
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Error")

    def append_log(self, message: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_console.append(f"[{ts}] {message}")

    def _populate_tree_from_groups(self, groups):
        self.tree.clear()
        if not groups:
            QMessageBox.information(self, "No commits", "No commit groups found in the selected range.")
            return

        for idx, g in enumerate(groups, 1):
            # start_time in groups is a datetime object
            st = g.get('start_time')
            if isinstance(st, datetime):
                st_str = st.strftime('%Y-%m-%d %H:%M:%S')
            else:
                st_str = str(st)
            author = g.get('author', '')
            comments = [e.get('comment', '') for e in g.get('entries', []) if e.get('comment')]
            main_comment = max(set(comments), key=comments.count) if comments else ''
            header = f"[{st_str}] {author}  Comment: {main_comment}"
            top = QTreeWidgetItem([header])
            # Add files as children
            for e in g.get('entries', []):
                fname = e.get('file', '')
                rev = e.get('revision', '')
                child_txt = f"-- {fname} (rev {rev})"
                child = QTreeWidgetItem([child_txt])
                top.addChild(child)
            self.tree.addTopLevelItem(top)
            top.setExpanded(True)
        self.tree.expandAll()

    @Slot()
    def on_selection_changed(self):
        it = self.tree.currentItem()
        if not it:
            self.detail_text.clear()
            return
        self.detail_text.setPlainText(it.text(0))

    @Slot()
    def on_open_html(self):
        if not self.last_outdir:
            QMessageBox.information(self, "No output", "Run analysis to generate a report first.")
            return
        html = Path(self.last_outdir) / "cvs_commit_report.html"
        if not html.exists():
            QMessageBox.information(self, "Missing file", f"HTML report not found:\n{html}")
            return
        webbrowser.open(str(html))

    @Slot()
    def on_open_folder(self):
        if not self.last_outdir:
            QMessageBox.information(self, "No output", "Run analysis to generate a report first.")
            return
        p = Path(self.last_outdir)
        if not p.exists():
            QMessageBox.information(self, "Missing folder", f"Output folder not found:\n{p}")
            return
        # Open in platform file explorer
        if sys.platform.startswith("win"):
            os.startfile(str(p))
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", str(p)])
        else:
            subprocess.run(["xdg-open", str(p)])

    @Slot()
    def on_open_excel(self):
        if not self.last_outdir:
            QMessageBox.information(self, "No output", "Run analysis to generate a report first.")
            return
        xlsx = Path(self.last_outdir) / "cvs_commit_analysis.xlsx"
        if not xlsx.exists():
            QMessageBox.information(self, "Missing file", f"Excel file not found:\n{xlsx}")
            return
        # Launch file with default app
        if sys.platform.startswith("win"):
            os.startfile(str(xlsx))
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", str(xlsx)])
        else:
            subprocess.run(["xdg-open", str(xlsx)])

    @Slot()
    def on_refresh_tree(self):
        # Re-load last JSON to refresh tree if analyzer previously wrote it.
        if not self.last_outdir:
            QMessageBox.information(self, "No output", "Run analysis to generate a report first.")
            return
        jsonf = Path(self.last_outdir) / "cvs_analysis_backup.json"
        if not jsonf.exists():
            QMessageBox.information(self, "Missing", f"JSON backup not found:\n{jsonf}")
            return
        try:
            import json
            with open(jsonf, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Convert back to groups with datetime objects
            groups = []
            for g in data:
                ng = g.copy()
                # parse start_time/end_time
                try:
                    ng['start_time'] = datetime.fromisoformat(g['start_time'])
                except Exception:
                    pass
                try:
                    ng['end_time'] = datetime.fromisoformat(g['end_time'])
                except Exception:
                    pass
                # parse entry dates
                ng_entries = []
                for e in g.get('entries', []):
                    ne = e.copy()
                    try:
                        ne['date'] = datetime.fromisoformat(e['date'])
                    except Exception:
                        pass
                    ng_entries.append(ne)
                ng['entries'] = ng_entries
                groups.append(ng)
            self.last_groups = groups
            self._populate_tree_from_groups(groups)
            self.append_log("Tree refreshed from existing JSON backup.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to load JSON backup: {exc}")

def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
