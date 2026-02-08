from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QDateTimeEdit,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

import pyqtgraph as pg
import pyqtgraph.exporters

from .settings import load_settings, save_settings


class CustomDateAxisItem(pg.DateAxisItem):
    def tickStrings(self, values, scale, spacing):  # type: ignore[override]
        strings = []
        for value in values:
            dt = datetime.fromtimestamp(value)
            strings.append(f"{dt.year}. {dt.month}.{dt.day} {dt.hour:02d}:{dt.minute:02d}")
        return strings


class HistoryWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SCM10 Temperature History")
        self.settings = load_settings()
        self.auto_scale = True
        self.data_loaded = False
        self._build_ui()
        self._apply_settings_to_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        main_layout = QVBoxLayout(central)

        control_layout = QGridLayout()

        time_group = QGroupBox("Time Range")
        time_form = QFormLayout()
        self.start_time = QDateTimeEdit()
        self.start_time.setCalendarPopup(True)
        self.start_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_time = QDateTimeEdit()
        self.end_time.setCalendarPopup(True)
        self.end_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_now = QPushButton("End = Now")
        self.end_now.clicked.connect(self._set_end_now)
        end_row = QHBoxLayout()
        end_row.addWidget(self.end_time)
        end_row.addWidget(self.end_now)
        end_container = QWidget()
        end_container.setLayout(end_row)
        time_form.addRow("Start", self.start_time)
        time_form.addRow("End", end_container)
        time_group.setLayout(time_form)
        control_layout.addWidget(time_group, 0, 0)

        file_group = QGroupBox("Log Files")
        file_form = QFormLayout()
        self.log_folder = QLineEdit()
        self.log_browse = QPushButton("Browse")
        self.log_browse.clicked.connect(self._browse_log_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.log_folder)
        folder_row.addWidget(self.log_browse)
        folder_container = QWidget()
        folder_container.setLayout(folder_row)
        file_form.addRow("Log Folder", folder_container)
        file_group.setLayout(file_form)
        control_layout.addWidget(file_group, 0, 1)

        scale_group = QGroupBox("Y Scale")
        scale_form = QFormLayout()
        self.y_min = QDoubleSpinBox()
        self.y_min.setRange(-1e6, 1e6)
        self.y_min.setDecimals(3)
        self.y_min.setSuffix(" K")
        self.y_min.valueChanged.connect(self._disable_auto_scale)
        self.y_max = QDoubleSpinBox()
        self.y_max.setRange(-1e6, 1e6)
        self.y_max.setDecimals(3)
        self.y_max.setSuffix(" K")
        self.y_max.valueChanged.connect(self._disable_auto_scale)
        self.scale_auto = QPushButton("Auto")
        self.scale_auto.clicked.connect(self._enable_auto_scale)
        scale_form.addRow("Min", self.y_min)
        scale_form.addRow("Max", self.y_max)
        scale_form.addRow("", self.scale_auto)
        scale_group.setLayout(scale_form)
        control_layout.addWidget(scale_group, 0, 2)

        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout()
        self.plot_button = QPushButton("Plot")
        self.plot_button.clicked.connect(self._plot_history)
        self.save_button = QPushButton("Save Figure")
        self.save_button.clicked.connect(self._save_figure)
        action_layout.addWidget(self.plot_button)
        action_layout.addWidget(self.save_button)
        action_group.setLayout(action_layout)
        control_layout.addWidget(action_group, 0, 3)

        main_layout.addLayout(control_layout)

        self.plot_widget = pg.PlotWidget(axisItems={"bottom": CustomDateAxisItem()})
        self.plot_widget.setBackground("w")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("bottom", "Time", color="k")
        self.plot_widget.setLabel("left", "Temperature", units="K", color="k")
        self.curve = self.plot_widget.plot([], [], pen=pg.mkPen(color="#0055aa", width=2))
        main_layout.addWidget(self.plot_widget, 1)

        self.status_label = QLabel("Select a log folder and time range.")
        main_layout.addWidget(self.status_label)

        self.setCentralWidget(central)

    def _apply_settings_to_ui(self) -> None:
        folder = self.settings.get("history", {}).get("log_folder", "")
        self.log_folder.setText(folder)
        now = QDateTime.currentDateTime()
        self.end_time.setDateTime(now)
        self.start_time.setDateTime(now.addDays(-1))

    def _set_end_now(self) -> None:
        self.end_time.setDateTime(QDateTime.currentDateTime())

    def _browse_log_folder(self) -> None:
        start_path = self.log_folder.text().strip() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Log Folder", start_path)
        if folder:
            self.log_folder.setText(folder)
            self._store_log_folder(folder)

    def _store_log_folder(self, folder: str) -> None:
        self.settings.setdefault("history", {})["log_folder"] = folder
        save_settings(self.settings)

    def _disable_auto_scale(self) -> None:
        self.auto_scale = False

    def _enable_auto_scale(self) -> None:
        self.auto_scale = True
        if self.data_loaded:
            self.plot_widget.enableAutoRange(axis="y", enable=True)

    def _plot_history(self) -> None:
        folder = self.log_folder.text().strip()
        if not folder:
            QMessageBox.warning(self, "Missing Folder", "Please select a log folder.")
            return
        self._store_log_folder(folder)
        start_dt = self.start_time.dateTime().toPython()
        end_dt = self.end_time.dateTime().toPython()
        if start_dt >= end_dt:
            QMessageBox.warning(self, "Invalid Range", "Start time must be before end time.")
            return

        log_files = self._select_log_files(Path(folder), start_dt, end_dt)
        if not log_files:
            QMessageBox.information(self, "No Files", "No log files found in the selected range.")
            self.curve.setData([], [])
            self.status_label.setText("No log data to display.")
            self.data_loaded = False
            return

        times, temps = self._load_data(log_files, start_dt, end_dt)
        if not times:
            QMessageBox.information(self, "No Data", "No data points found in the selected range.")
            self.curve.setData([], [])
            self.status_label.setText("No log data to display.")
            self.data_loaded = False
            return

        self.curve.setData(times, temps)
        self.plot_widget.enableAutoRange(axis="x", enable=True)
        if self.auto_scale:
            self.plot_widget.enableAutoRange(axis="y", enable=True)
        else:
            if self.y_min.value() >= self.y_max.value():
                QMessageBox.warning(
                    self, "Invalid Y Scale", "Minimum must be less than maximum."
                )
                self.plot_widget.enableAutoRange(axis="y", enable=True)
            else:
                self.plot_widget.setYRange(self.y_min.value(), self.y_max.value())
        self.status_label.setText(
            f"Loaded {len(times)} points from {len(log_files)} file(s)."
        )
        self.data_loaded = True

    def _select_log_files(
        self, folder: Path, start_dt: datetime, end_dt: datetime
    ) -> list[Path]:
        if not folder.exists():
            return []
        candidates = []
        for path in folder.glob("scm10_log_*.csv"):
            timestamp = self._parse_log_timestamp(path.name)
            if timestamp is None:
                continue
            candidates.append((timestamp, path))
        candidates.sort(key=lambda item: item[0])

        selected = [path for timestamp, path in candidates if start_dt <= timestamp <= end_dt]
        previous = [path for timestamp, path in candidates if timestamp < start_dt]
        if previous:
            selected.insert(0, previous[-1])
        return selected

    def _parse_log_timestamp(self, filename: str) -> Optional[datetime]:
        if not filename.startswith("scm10_log_") or not filename.endswith(".csv"):
            return None
        raw = filename[len("scm10_log_") : -len(".csv")]
        try:
            return datetime.strptime(raw, "%Y%m%d_%H%M%S")
        except ValueError:
            return None

    def _load_data(
        self, files: Iterable[Path], start_dt: datetime, end_dt: datetime
    ) -> tuple[list[float], list[float]]:
        times: list[float] = []
        temps: list[float] = []
        for path in files:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    reader = csv.DictReader(handle)
                    for row in reader:
                        timestamp_iso = row.get("timestamp_iso")
                        temperature_str = row.get("temperature_k")
                        if not timestamp_iso or not temperature_str:
                            continue
                        try:
                            timestamp = datetime.fromisoformat(timestamp_iso)
                            temperature = float(temperature_str)
                        except ValueError:
                            continue
                        if timestamp < start_dt or timestamp > end_dt:
                            continue
                        times.append(timestamp.timestamp())
                        temps.append(temperature)
            except OSError:
                continue
        return times, temps

    def _save_figure(self) -> None:
        if not self.data_loaded:
            QMessageBox.information(self, "No Data", "Plot data before saving the figure.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Figure",
            "temperature_history.png",
            "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)",
        )
        if not filename:
            return
        exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
        exporter.export(filename)
        self.status_label.setText(f"Saved figure to {filename}.")


def run_history_app() -> int:
    app = QApplication(sys.argv)
    font = app.font()
    if font.pointSize() > 0:
        font.setPointSize(font.pointSize() + 1)
        app.setFont(font)
    window = HistoryWindow()
    window.resize(1100, 800)
    window.show()
    return app.exec()
