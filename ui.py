"""Example for how to use the `qspreadsheet` package."""

import sys
import logging
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QPoint, QSettings, QSize, QThread, Signal, QObject, Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QProgressBar,
    QTextEdit,
)

import red_pdf
from version import __version__

logger = logging.getLogger("red_pdf")


class ProcessWorker(QObject):
    """Worker to run PDF processing in a background thread."""
    progress = Signal(int)  # progress percentage
    status = Signal(str)    # status message
    finished = Signal(bool, str)  # (success, message)
    
    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.stop_requested = False
        
    def progress_callback(self, message: str, progress: int = 0):
        if progress < 1:
            progress = 1
        elif progress > 99:
            progress = 99
            
        self.status.emit(message)
        self.progress.emit(progress)
        self.progress
    
    def run(self):
        """Execute PDF processing."""
        try:
            if self.stop_requested:
                self.finished.emit(False, "Processing cancelled by user.")
                return
                
            self.status.emit(f"Processing folder: {self.folder_path}")
            self.progress.emit(0)
            
            # Call the main processing function
            result = red_pdf.main(self.folder_path, progress_callback=self.progress_callback)

            if self.stop_requested:
                self.status.emit("Processing cancelled.")
                self.finished.emit(False, "Processing was cancelled.")
                return
            
            self.progress.emit(100)
            self.status.emit("Processing complete!")
            self.finished.emit(True, result)
        except Exception as e:
            self.status.emit(f"Error: {str(e)}")
            self.finished.emit(False, f"Error: {str(e)}")


class MainWindow(QMainWindow):
    """Main GUI Window."""

    def __init__(self, parent: QWidget | None = None):
        """Create MainWindow object.

        Args:
            parent (qt.QWidget, optional): Window's parent. Defaults to None.
        """
        super(MainWindow, self).__init__(parent)
        self._window_settings = QSettings(
            QSettings.Format.IniFormat,
            QSettings.Scope.UserScope,
            'red',
            'red_pdf'
        )
        self._settings_group = self.__class__.__name__
        self._default_size = QSize(800, 400)
        self.setMinimumSize(QSize(600, 300))
        self.worker_thread = None
        
        central_widget = QWidget(self)
        central_layout = QVBoxLayout(central_widget)
        central_widget.setLayout(central_layout)
        
        # Folder picker section
        folder_layout = QHBoxLayout()
        folder_label = QLabel("PDF Folder:")
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select a folder containing PDFs...")
        self.folder_input.setReadOnly(True)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.pick_folder)
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(self.browse_button)
        central_layout.addLayout(folder_layout)
        
        # Status display
        self.status_label = QLabel("Ready")
        central_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        central_layout.addWidget(self.progress_bar)
        
        # Spacer to push results display down
        central_layout.addSpacing(20)
        
        # Results display
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setMaximumHeight(80)
        self.results_display.setPlaceholderText("Results will appear here...")
        central_layout.addWidget(self.results_display)
        
        # Add stretch to push start button to bottom
        central_layout.addStretch()
        
        # Start button at bottom
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.start_button = QPushButton("Start Processing")
        self.start_button.clicked.connect(self.on_start_clicked)
        self.start_button.setMinimumWidth(120)
        button_layout.addWidget(self.start_button)
        button_layout.addStretch()
        central_layout.addLayout(button_layout)
        
        self.setCentralWidget(central_widget)
        self.setWindowTitle('Red PDF')
        
        # Set window icon (if icon file exists)
        icon_path = "logo.ico"
        icon = QIcon(icon_path)
        if not icon.isNull():
            self.setWindowIcon(icon)
        
        # Add status bar with version (right-aligned)
        version_label = QLabel(f"v{__version__}")
        version_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.statusBar().addPermanentWidget(version_label)
        
        self.load_settings()

    def closeEvent(self, event: QCloseEvent):
        """Handles the close event for this window

        Args:
            event (qt.QCloseEvent): close event.
        """
        # Check if thread is still running
        if self.worker_thread and self.worker_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Processing in Progress",
                "Processing is still running. Do you want to cancel and close?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            # Signal worker to stop
            if hasattr(self, 'worker'):
                self.worker.stop_requested = True
            self.worker_thread.quit()
            self.worker_thread.wait(2000)  # Wait max 2 seconds

        self.save_settings()
        event.accept()

    def save_settings(self):
        """Save window settings like size and position.

        Args:
            settings (qt.QSettings): Window settings.
        """
        settings = self._window_settings
        settings.beginGroup(self._settings_group)
        settings.setValue('size', self.size())
        settings.setValue('pos', self.pos())
        settings.setValue('pos', self.pos())
        settings.setValue('folder_input', self.folder_input.text().strip())
        settings.endGroup()

    def load_settings(self):
        """Load window settings like size and position.

        Args:
            settings (QSettings): Window settings.
        """
        settings = self._window_settings
        settings.beginGroup(self._settings_group)
        self.resize(QSize(settings.value('size', self._default_size)))  # type: ignore
        self.move(QPoint(settings.value('pos', QPoint(200, 200))))  # type: ignore
        self.folder_input.setText(settings.value('folder_input', ''))
        settings.endGroup()

    def pick_folder(self):
        """Open a folder picker dialog and set the selected path."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with PDFs",
            "",
            QFileDialog.ShowDirsOnly
        )
        if folder:
            self.folder_input.setText(folder)

    def on_start_clicked(self):
        """Handle the Start Processing button click."""
        folder = self.folder_input.text().strip()
        if not folder:
            QMessageBox.warning(self, "Error", "Please select a folder first.")
            return
        
        # Disable button and create worker thread
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting processing...")
        self.results_display.clear()
        
        # Create worker and thread
        self.worker = ProcessWorker(folder)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_processing_finished)
        
        # Start the thread
        self.worker_thread.start()

    def on_processing_finished(self, success: bool, message: str):
        """Handle processing completion."""
        self.start_button.setEnabled(True)
        
        if success:
            # Display results path in the text box
            folder = self.folder_input.text().strip()
            results_path = f"{folder}/results.csv"
            self.results_display.setText(f"Results saved to:\n{results_path}")
            QMessageBox.information(self, "Success", "Successfully processed PDFs.")
        else:
            QMessageBox.critical(self, "Error", message)
        
        # Clean up thread
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()


def main():
    """Entry point for this script."""
    app = QApplication.instance() or QApplication(sys.argv)

    window = MainWindow()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    logging.basicConfig(
        handlers=[RotatingFileHandler("app.log", maxBytes=500_000, backupCount=3)],
        level=logging.DEBUG,
        format="%(asctime)s - %(message)s"
    )
    logging.getLogger("pytesseract").setLevel(logging.WARNING)
    main()