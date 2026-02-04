from __future__ import annotations

import re
import sys
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import pyqtgraph as pg

from .alarm import AlarmManager, AlarmSettings
from .comms import (
    EthernetConfig,
    EthernetConnection,
    SerialConfig,
    SerialConnection,
    available_serial_ports,
)
from .emailer import EmailConfig
from .logger import DataLogger
from .protocol import parse_temperature
from .settings import decode_terminator, encode_terminator, load_settings, save_settings

try:
    import keyring  # type: ignore
except Exception:
    keyring = None


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SCM10 Temperature Monitor")

        self.settings = load_settings()
        self.connection = None
        self.logger = None
        self.read_timer = QTimer(self)
        self.read_timer.timeout.connect(self._poll_temperature)
        self.reading_active = False
        self.start_time = None
        self.time_data = []
        self.temp_data = []
        self.alarm_manager = AlarmManager()
        self.keyring_service = self.settings.get("email", {}).get("keyring_service", "SCM10_T_monitor")

        self._build_ui()
        self._apply_settings_to_ui()
        self._refresh_ports()

    def _build_ui(self) -> None:
        central = QWidget()
        main_layout = QHBoxLayout(central)
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)

        # Connection group
        self.connection_group = QGroupBox("Connection")
        conn_layout = QGridLayout()

        self.connection_type = QComboBox()
        self.connection_type.addItems(["Ethernet", "RS232 (USB)"])
        self.connection_type.currentIndexChanged.connect(self._on_connection_type_changed)
        conn_layout.addWidget(QLabel("Type"), 0, 0)
        conn_layout.addWidget(self.connection_type, 0, 1)

        # Stacked widget for connection details
        self.conn_stack = QStackedWidget()

        # Ethernet widget
        eth_widget = QWidget()
        eth_form = QFormLayout(eth_widget)
        self.eth_ip = QLineEdit()
        self.eth_port = QSpinBox()
        self.eth_port.setRange(1, 65535)
        eth_form.addRow("IP Address", self.eth_ip)
        eth_form.addRow("Port", self.eth_port)

        # Serial widget
        serial_widget = QWidget()
        serial_form = QFormLayout(serial_widget)
        self.serial_port = QComboBox()
        self.serial_refresh = QPushButton("Refresh")
        self.serial_refresh.clicked.connect(self._refresh_ports)
        port_row = QHBoxLayout()
        port_row.addWidget(self.serial_port)
        port_row.addWidget(self.serial_refresh)
        port_container = QWidget()
        port_container.setLayout(port_row)
        self.serial_baud = QComboBox()
        self.serial_baud.addItems(["9600", "19200", "57600", "115200"])
        serial_form.addRow("COM Port", port_container)
        serial_form.addRow("Baud", self.serial_baud)

        self.conn_stack.addWidget(eth_widget)
        self.conn_stack.addWidget(serial_widget)
        conn_layout.addWidget(self.conn_stack, 1, 0, 1, 2)

        # Advanced protocol settings
        self.terminator = QLineEdit()
        self.idn_query = QLineEdit()
        self.temp_query = QLineEdit()
        adv_form = QFormLayout()
        adv_form.addRow("Terminator", self.terminator)
        adv_form.addRow("IDN Query", self.idn_query)
        adv_form.addRow("Temp Query", self.temp_query)
        adv_widget = QWidget()
        adv_widget.setLayout(adv_form)
        conn_layout.addWidget(adv_widget, 2, 0, 1, 2)

        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self._test_connection)
        self.save_config_button = QPushButton("Save Config")
        self.save_config_button.clicked.connect(self._save_config)
        self.status_label = QLabel("Disconnected")
        conn_layout.addWidget(self.test_button, 3, 0)
        conn_layout.addWidget(self.save_config_button, 3, 1)
        conn_layout.addWidget(self.status_label, 4, 0, 1, 2)

        self.connection_group.setLayout(conn_layout)
        left_layout.addWidget(self.connection_group)

        # Readout group
        self.readout_group = QGroupBox("Readout")
        read_layout = QGridLayout()

        self.read_toggle = QPushButton("Start Reading")
        self.read_toggle.setCheckable(True)
        self.read_toggle.clicked.connect(self._toggle_reading)
        self.read_period = QDoubleSpinBox()
        self.read_period.setRange(0.1, 60.0)
        self.read_period.setSingleStep(0.1)
        self.read_period.setSuffix(" s")
        self.read_period.valueChanged.connect(self._update_timer_interval)

        self.current_temp = QLabel("-- K")
        self.current_temp.setStyleSheet("color: #c00000; font-size: 26px; font-weight: 600;")

        self.log_folder = QLineEdit()
        self.log_browse = QPushButton("Browse")
        self.log_browse.clicked.connect(self._browse_log_folder)
        log_row = QHBoxLayout()
        log_row.addWidget(self.log_folder)
        log_row.addWidget(self.log_browse)
        log_container = QWidget()
        log_container.setLayout(log_row)

        read_layout.addWidget(self.read_toggle, 0, 0)
        read_layout.addWidget(QLabel("Period"), 0, 1)
        read_layout.addWidget(self.read_period, 0, 2)
        read_layout.addWidget(QLabel("Current"), 0, 3)
        read_layout.addWidget(self.current_temp, 0, 4)
        read_layout.addWidget(QLabel("Log Folder"), 1, 0)
        read_layout.addWidget(log_container, 1, 1, 1, 4)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("w")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("bottom", "Time", units="s")
        self.plot_widget.setLabel("left", "Temperature", units="K")
        self.plot_curve = self.plot_widget.plot([], [], pen=pg.mkPen(color=(10, 60, 200), width=2))
        read_layout.addWidget(self.plot_widget, 2, 0, 1, 5)

        self.readout_group.setLayout(read_layout)
        right_layout.addWidget(self.readout_group)

        # Alarm group
        self.alarm_group = QGroupBox("Alarm")
        alarm_layout = QGridLayout()
        self.alarm_enabled = QCheckBox("Enable Alarm")
        alarm_layout.addWidget(self.alarm_enabled, 0, 0, 1, 2)

        self.low_enabled = QCheckBox("Low Threshold")
        self.low_threshold = QDoubleSpinBox()
        self.low_threshold.setRange(-273.15, 2000.0)
        self.low_threshold.setDecimals(3)
        self.low_threshold.setSuffix(" K")

        self.high_enabled = QCheckBox("High Threshold")
        self.high_threshold = QDoubleSpinBox()
        self.high_threshold.setRange(-273.15, 2000.0)
        self.high_threshold.setDecimals(3)
        self.high_threshold.setSuffix(" K")

        alarm_layout.addWidget(self.low_enabled, 1, 0)
        alarm_layout.addWidget(self.low_threshold, 1, 1)
        alarm_layout.addWidget(self.high_enabled, 2, 0)
        alarm_layout.addWidget(self.high_threshold, 2, 1)

        self.beep_enabled = QCheckBox("Beep")
        self.email_enabled = QCheckBox("Email")
        alarm_layout.addWidget(self.beep_enabled, 3, 0)
        alarm_layout.addWidget(self.email_enabled, 3, 1)

        self.email_min_interval = QSpinBox()
        self.email_min_interval.setRange(1, 1440)
        self.email_min_interval.setSuffix(" min")
        alarm_layout.addWidget(QLabel("Email Min Interval"), 4, 0)
        alarm_layout.addWidget(self.email_min_interval, 4, 1)

        # Email settings
        email_box = QGroupBox("Email Settings")
        email_form = QFormLayout()
        self.smtp_host = QLineEdit()
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_tls = QCheckBox("Use TLS")
        self.smtp_user = QLineEdit()
        self.smtp_pass = QLineEdit()
        self.smtp_pass.setEchoMode(QLineEdit.Password)
        self.remember_password = QCheckBox("Remember Password (encrypted)")
        if not keyring:
            self.remember_password.setEnabled(False)
            self.remember_password.setToolTip("Keyring unavailable on this system")
        self.email_from = QLineEdit()
        self.email_to = QPlainTextEdit()
        self.email_to.setPlaceholderText("user1@example.com; user2@example.com")
        self.email_to.setFixedHeight(70)
        self.email_subject = QLineEdit()
        email_form.addRow("SMTP Host", self.smtp_host)
        email_form.addRow("SMTP Port", self.smtp_port)
        email_form.addRow("TLS", self.smtp_tls)
        email_form.addRow("Username", self.smtp_user)
        email_form.addRow("Password", self.smtp_pass)
        email_form.addRow("", self.remember_password)
        email_form.addRow("From", self.email_from)
        email_form.addRow("To", self.email_to)
        email_form.addRow("Subject", self.email_subject)
        email_box.setLayout(email_form)
        alarm_layout.addWidget(email_box, 5, 0, 1, 2)

        self.alarm_group.setLayout(alarm_layout)
        left_layout.addWidget(self.alarm_group)
        left_layout.addStretch(1)

        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready")
        self.status_state = QLabel("Disconnected")
        self.statusBar().addPermanentWidget(self.status_state)
        self._set_connection_status(False, "Disconnected")

    def _apply_settings_to_ui(self) -> None:
        conn_type = self.settings["connection"]["type"]
        self.connection_type.setCurrentIndex(0 if conn_type == "ethernet" else 1)
        self.eth_ip.setText(self.settings["connection"]["ethernet"]["ip"])
        self.eth_port.setValue(int(self.settings["connection"]["ethernet"]["port"]))
        self.serial_baud.setCurrentText(str(self.settings["connection"]["serial"]["baud"]))

        self.terminator.setText(self.settings["protocol"]["terminator"])
        self.idn_query.setText(self.settings["protocol"]["idn_query"])
        self.temp_query.setText(self.settings["protocol"]["temp_query"])

        self.read_period.setValue(float(self.settings["readout"]["period_s"]))
        self.log_folder.setText(self.settings["readout"]["log_folder"])

        alarm = self.settings["alarm"]
        self.alarm_enabled.setChecked(alarm["enabled"])
        self.low_enabled.setChecked(alarm["low_enabled"])
        self.low_threshold.setValue(float(alarm["low_threshold"]))
        self.high_enabled.setChecked(alarm["high_enabled"])
        self.high_threshold.setValue(float(alarm["high_threshold"]))
        self.beep_enabled.setChecked(alarm["beep_enabled"])
        self.email_enabled.setChecked(alarm["email_enabled"])
        self.email_min_interval.setValue(int(alarm["email_min_interval_min"]))

        email = self.settings["email"]
        self.smtp_host.setText(email["smtp_host"])
        self.smtp_port.setValue(int(email["smtp_port"]))
        self.smtp_tls.setChecked(bool(email["use_tls"]))
        self.smtp_user.setText(email["username"])
        self.smtp_pass.setText(email["password"])
        self.remember_password.setChecked(bool(email.get("remember_password", False)))
        self.email_from.setText(email["from_addr"])
        to_addrs = email.get("to_addrs")
        if isinstance(to_addrs, list):
            to_text = ";\n".join(to_addrs)
        else:
            to_text = str(email.get("to_addr", "")) if email.get("to_addr") else ""
        self.email_to.setPlainText(to_text)
        self.email_subject.setText(email["subject"])

        self._on_connection_type_changed()
        self._load_password_from_keyring()

    def _collect_settings_from_ui(self) -> None:
        conn_type = "ethernet" if self.connection_type.currentIndex() == 0 else "serial"
        self.settings["connection"]["type"] = conn_type
        self.settings["connection"]["ethernet"]["ip"] = self.eth_ip.text().strip()
        self.settings["connection"]["ethernet"]["port"] = int(self.eth_port.value())
        self.settings["connection"]["serial"]["port"] = self.serial_port.currentText().strip()
        self.settings["connection"]["serial"]["baud"] = int(self.serial_baud.currentText())

        self.settings["protocol"]["terminator"] = self.terminator.text().strip()
        self.settings["protocol"]["idn_query"] = self.idn_query.text().strip()
        self.settings["protocol"]["temp_query"] = self.temp_query.text().strip()

        self.settings["readout"]["period_s"] = float(self.read_period.value())
        self.settings["readout"]["log_folder"] = self.log_folder.text().strip()

        self.settings["alarm"]["enabled"] = self.alarm_enabled.isChecked()
        self.settings["alarm"]["low_enabled"] = self.low_enabled.isChecked()
        self.settings["alarm"]["low_threshold"] = float(self.low_threshold.value())
        self.settings["alarm"]["high_enabled"] = self.high_enabled.isChecked()
        self.settings["alarm"]["high_threshold"] = float(self.high_threshold.value())
        self.settings["alarm"]["beep_enabled"] = self.beep_enabled.isChecked()
        self.settings["alarm"]["email_enabled"] = self.email_enabled.isChecked()
        self.settings["alarm"]["email_min_interval_min"] = int(self.email_min_interval.value())

        self.settings["email"]["smtp_host"] = self.smtp_host.text().strip()
        self.settings["email"]["smtp_port"] = int(self.smtp_port.value())
        self.settings["email"]["use_tls"] = self.smtp_tls.isChecked()
        self.settings["email"]["username"] = self.smtp_user.text().strip()
        # Do not persist plaintext password in the config file.
        self.settings["email"]["password"] = ""
        self.settings["email"]["from_addr"] = self.email_from.text().strip()
        self.settings["email"]["to_addrs"] = self._parse_recipients(self.email_to.toPlainText())
        self.settings["email"]["subject"] = self.email_subject.text().strip()
        self.settings["email"]["remember_password"] = self.remember_password.isChecked()

    def _on_connection_type_changed(self) -> None:
        self.conn_stack.setCurrentIndex(self.connection_type.currentIndex())

    def _refresh_ports(self) -> None:
        ports = available_serial_ports()
        current = self.serial_port.currentText()
        self.serial_port.clear()
        self.serial_port.addItems(ports)
        if current in ports:
            self.serial_port.setCurrentText(current)
        elif ports:
            self.serial_port.setCurrentIndex(0)

    def _parse_recipients(self, text: str) -> list[str]:
        parts = re.split(r"[;\n]+", text)
        return [part.strip() for part in parts if part.strip()]

    def _save_config(self) -> None:
        self._collect_settings_from_ui()
        self._persist_password_to_keyring()
        save_settings(self.settings)
        self.statusBar().showMessage(f"Config saved to {self._config_path_display()}")

    def _load_password_from_keyring(self) -> None:
        if not keyring or not self.remember_password.isChecked():
            return
        username = self.smtp_user.text().strip()
        if not username:
            return
        try:
            stored = keyring.get_password(self.keyring_service, username)
        except Exception:
            stored = None
        if stored:
            self.smtp_pass.setText(stored)

    def _persist_password_to_keyring(self) -> None:
        if not keyring:
            if self.remember_password.isChecked():
                self.statusBar().showMessage("Keyring unavailable: password not saved")
            return
        username = self.smtp_user.text().strip()
        if not username:
            return
        if self.remember_password.isChecked() and self.smtp_pass.text():
            try:
                keyring.set_password(self.keyring_service, username, self.smtp_pass.text())
            except Exception:
                self.statusBar().showMessage("Failed to save password to keyring")
        else:
            try:
                keyring.delete_password(self.keyring_service, username)
            except Exception:
                pass

    def _config_path_display(self) -> str:
        from .settings import config_path

        return str(config_path())

    def _set_connection_status(self, connected: bool, text: str) -> None:
        color = "#1a7f37" if connected else "#b42318"
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 16px;")
        if hasattr(self, "status_state"):
            self.status_state.setText(text)
            self.status_state.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 16px;")

    def _browse_log_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Log Folder")
        if folder:
            self.log_folder.setText(folder)

    def _update_timer_interval(self) -> None:
        if self.reading_active:
            interval_ms = int(self.read_period.value() * 1000)
            self.read_timer.setInterval(interval_ms)

    def _make_connection(self):
        conn_type = "ethernet" if self.connection_type.currentIndex() == 0 else "serial"
        if conn_type == "ethernet":
            config = EthernetConfig(
                ip=self.eth_ip.text().strip(),
                port=int(self.eth_port.value()),
                timeout_s=float(self.settings["connection"]["ethernet"]["timeout_s"]),
            )
            return EthernetConnection(config)
        config = SerialConfig(
            port=self.serial_port.currentText().strip(),
            baud=int(self.serial_baud.currentText()),
            timeout_s=float(self.settings["connection"]["serial"]["timeout_s"]),
        )
        return SerialConnection(config)

    def _test_connection(self) -> None:
        self._collect_settings_from_ui()
        terminator = decode_terminator(self.settings["protocol"]["terminator"])
        conn = self._make_connection()
        try:
            conn.open()
            response = conn.query(self.settings["protocol"]["idn_query"], terminator)
            self._set_connection_status(True, "Connected")
            self.statusBar().showMessage(f"Connection test succeeded: {response}")
        except Exception as exc:
            self._set_connection_status(False, "Disconnected")
            self.statusBar().showMessage(f"Connection test failed: {exc}")
        finally:
            conn.close()

    def _toggle_reading(self) -> None:
        if self.read_toggle.isChecked():
            self._start_reading()
        else:
            self._stop_reading()

    def _start_reading(self) -> None:
        if self.reading_active:
            return
        self._collect_settings_from_ui()
        terminator = decode_terminator(self.settings["protocol"]["terminator"])
        self.connection = self._make_connection()
        try:
            self.connection.open()
        except Exception as exc:
            self.read_toggle.setChecked(False)
            self._set_connection_status(False, "Disconnected")
            self.statusBar().showMessage(f"Failed to open connection: {exc}")
            return
        self._set_connection_status(True, "Connected")

        log_folder_text = self.log_folder.text().strip()
        if not log_folder_text:
            log_folder_text = str(Path.cwd() / "logs")
            self.log_folder.setText(log_folder_text)
        self.logger = DataLogger(Path(log_folder_text))
        log_path = self.logger.start()

        self.start_time = time.monotonic()
        self.time_data = []
        self.temp_data = []
        self.plot_curve.setData(self.time_data, self.temp_data)
        self.reading_active = True
        self.read_toggle.setText("Stop Reading")
        self.read_toggle.setStyleSheet(
            "background-color: #c00000; color: #ffffff; font-weight: 600;"
        )

        interval_ms = int(self.read_period.value() * 1000)
        self.read_timer.setInterval(interval_ms)
        self.read_timer.start()
        self.statusBar().showMessage(f"Reading started. Logging to {log_path}")

        # Prime a read immediately
        self._poll_temperature()

    def _stop_reading(self) -> None:
        if not self.reading_active:
            return
        self.read_timer.stop()
        self.reading_active = False
        self.read_toggle.setText("Start Reading")
        self.read_toggle.setStyleSheet("")
        self.current_temp.setText("-- K")
        if self.connection:
            self.connection.close()
            self.connection = None
        self._set_connection_status(False, "Disconnected")
        if self.logger:
            self.logger.close()
            self.logger = None
        self.alarm_manager.reset()
        self.statusBar().showMessage("Reading stopped")

    def _poll_temperature(self) -> None:
        if not self.connection:
            return
        terminator = decode_terminator(self.settings["protocol"]["terminator"])
        command = self.settings["protocol"]["temp_query"]
        try:
            response = self.connection.query(command, terminator)
            temperature = parse_temperature(response)
        except Exception as exc:
            self.statusBar().showMessage(f"Read failed: {exc}")
            return

        elapsed = time.monotonic() - self.start_time if self.start_time else 0.0
        timestamp_iso = datetime.now().isoformat(timespec="seconds")

        self.time_data.append(elapsed)
        self.temp_data.append(temperature)

        max_points = int(self.settings["readout"].get("max_points", 3600))
        if len(self.time_data) > max_points:
            self.time_data = self.time_data[-max_points:]
            self.temp_data = self.temp_data[-max_points:]

        self.plot_curve.setData(self.time_data, self.temp_data)
        self.current_temp.setText(f"{temperature:.3f} K")

        if self.logger:
            self.logger.log(timestamp_iso, elapsed, temperature)

        alarm_settings = AlarmSettings(
            enabled=self.alarm_enabled.isChecked(),
            low_enabled=self.low_enabled.isChecked(),
            low_threshold=float(self.low_threshold.value()),
            high_enabled=self.high_enabled.isChecked(),
            high_threshold=float(self.high_threshold.value()),
            beep_enabled=self.beep_enabled.isChecked(),
            email_enabled=self.email_enabled.isChecked(),
            email_min_interval_min=int(self.email_min_interval.value()),
        )
        email_config = EmailConfig(
            smtp_host=self.smtp_host.text().strip(),
            smtp_port=int(self.smtp_port.value()),
            use_tls=self.smtp_tls.isChecked(),
            username=self.smtp_user.text().strip(),
            password=self.smtp_pass.text(),
            from_addr=self.email_from.text().strip(),
            to_addrs=self._parse_recipients(self.email_to.toPlainText()),
            subject=self.email_subject.text().strip() or "SCM10 Alarm",
        )
        self.alarm_manager.evaluate(temperature, alarm_settings, email_config)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt naming
        self._collect_settings_from_ui()
        # Keep terminator escaped in settings for readability.
        self.settings["protocol"]["terminator"] = encode_terminator(
            decode_terminator(self.settings["protocol"]["terminator"])
        )
        self._persist_password_to_keyring()
        save_settings(self.settings)
        self._stop_reading()
        event.accept()


def run_app() -> int:
    app = QApplication(sys.argv)
    font = app.font()
    if font.pointSize() > 0:
        font.setPointSize(font.pointSize() + 1)
        app.setFont(font)
    window = MainWindow()
    window.resize(1100, 800)
    window.show()
    return app.exec()
