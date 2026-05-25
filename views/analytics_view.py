"""
Libralex Information System
views/analytics_view.py

Frontend component rendering advanced metrics, KPI blocks, and catalog
item performance rankings for the Librarian/Admin landing dashboard tab.
"""
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPushButton
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class AnalyticsDashboard(QWidget):
    def __init__(self, admin_controller, parent=None):
        super().__init__(parent)
        self.ctrl = admin_controller

        self._init_view()
        self._build_ui()

    def _init_view(self):
        self.setObjectName("AnalyticsDashboard")
        self.setStyleSheet("""
            QWidget#AnalyticsDashboard { background-color: #F7F4EF; }
            QLabel#dashTitle { font-size: 18px; font-weight: 700; color: #1B2A4A; }
            QLabel#sectionLabel { font-size: 14px; font-weight: 600; color: #4A5568; margin-top: 10px; }
            QPushButton#btnRefresh { 
                background-color: #1B2A4A; color: #FFFFFF; border: none; 
                border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 600; 
            }
            QPushButton#btnRefresh:hover { background-color: #2A3F6F; }
            QTableWidget { 
                background-color: #FFFFFF; border: 1px solid #E0D9CF; 
                border-radius: 8px; gridline-color: #F0EBE3;
                alternate-background-color: #FAF8F5;
            }
            QTableWidget::item { padding: 6px 10px; color: #1B2A4A; font-size: 12px; }
            QHeaderView::section { 
                background-color: #F0EBE3; color: #4A5568; 
                font-weight: 600; font-size: 11px; padding: 8px; border: none; 
                border-bottom: 1px solid #D1C9BC;
            }
        """)

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(14)

        # --- Top Header Panel ---
        header_layout = QHBoxLayout()
        title = QLabel("📈 System Analytics & Overview")
        title.setObjectName("dashTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.btn_refresh = QPushButton("🔄 Refresh Analytics")
        self.btn_refresh.setObjectName("btnRefresh")
        self.btn_refresh.clicked.connect(self.refresh_analytics)
        header_layout.addWidget(self.btn_refresh)
        root_layout.addLayout(header_layout)

        # --- KPI Cards Row ---
        kpi_container = QHBoxLayout()
        kpi_container.setSpacing(12)

        self.card_users = self._create_kpi_card("Total Registered Users", "0", "#1B2A4A")
        self.card_books = self._create_kpi_card("Cataloged Items", "0", "#1E7E34")
        self.card_borrows = self._create_kpi_card("Active Loans", "0", "#B7791F")
        self.card_reviews = self._create_kpi_card("Pending Moderation", "0", "#C0392B")

        kpi_container.addWidget(self.card_users['frame'])
        kpi_container.addWidget(self.card_books['frame'])
        kpi_container.addWidget(self.card_borrows['frame'])
        kpi_container.addWidget(self.card_reviews['frame'])
        root_layout.addLayout(kpi_container)

        # --- Leaderboard Section ---
        table_label = QLabel("🏆 Top Rated Resources (Catalog Performance)")
        table_label.setObjectName("sectionLabel")
        root_layout.addWidget(table_label)

        self.table = self._build_table()
        root_layout.addWidget(self.table, stretch=1)

        # --- Bottom Status Bar ---
        self.lbl_status = QLabel("Engine connected. Ready.")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #7A8499; font-style: italic;")
        root_layout.addWidget(self.lbl_status)

    def _create_kpi_card(self, title: str, initial_val: str, accent_color: str) -> dict:
        """Generates a styled tracking card object component."""
        frame = QFrame()
        frame.setMinimumSize(160, 85)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid #E0D9CF;
                border-radius: 8px;
                border-top: 4px solid {accent_color};
            }}
        """)
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(12, 10, 12, 10)
        vbox.setSpacing(2)

        lbl_title = QLabel(title.upper())
        lbl_title.setStyleSheet("font-size: 10px; color: #7A8499; font-weight: 700; border: none;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        lbl_val = QLabel(initial_val)
        lbl_val.setStyleSheet(f"font-size: 26px; font-weight: 700; color: {accent_color}; border: none;")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_val)
        return {"frame": frame, "value_label": lbl_val}

    def _build_table(self) -> QTableWidget:
        cols = ["Book Title", "Author", "Average Assessment", "Approved Feedback Items"]
        table = QTableWidget(0, len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)

        # Column width policies
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        return table

    def refresh_analytics(self):
        """Pulls updated transactional statistics from the database controller layer."""
        self.lbl_status.setText("Polling engine data arrays...")
        try:
            result = self.ctrl.get_dashboard_stats()
            if not result.get("success"):
                self.lbl_status.setText(f"Error: {result.get('message')}")
                return

            # Map core metrics directly to UI card elements
            metrics = result.get("metrics", {})
            self.card_users["value_label"].setText(str(metrics.get("total_users", 0)))
            self.card_books["value_label"].setText(str(metrics.get("total_books", 0)))
            self.card_borrows["value_label"].setText(str(metrics.get("active_borrows", 0)))
            self.card_reviews["value_label"].setText(str(metrics.get("pending_reviews", 0)))

            # Populate Top Rated Books Grid
            top_books = result.get("top_books", [])
            self.table.setRowCount(0)

            for book in top_books:
                row = self.table.rowCount()
                self.table.insertRow(row)

                # Title & Author strings
                self.table.setItem(row, 0, QTableWidgetItem(book.get("title", "Unknown Title")))
                self.table.setItem(row, 1, QTableWidgetItem(book.get("author", "Unknown Author")))

                # Format Score output alignment
                score_val = book.get('avg_rating', 0.0)
                score_item = QTableWidgetItem(f"⭐ {score_val} / 5.0")
                self.table.setItem(row, 2, score_item)

                # Feed count items
                count_item = QTableWidgetItem(f"{book.get('review_count', 0)} post(s)")
                self.table.setItem(row, 3, count_item)

            self.table.resizeRowsToContents()
            self.lbl_status.setText("Metrics refreshed successfully against backend database clusters.")
        except Exception as exc:
            logger.exception("UI render refresh exception encountered.")
            self.lbl_status.setText(f"Exception failure: {str(exc)}")