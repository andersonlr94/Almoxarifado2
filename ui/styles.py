FUSION_QSS = '''
QMainWindow {
    background-color: #f1f5f9;
}

/* ── Sidebar ── */
QWidget#sidebar {
    background-color: #0f172a;
    border: none;
}

QWidget#sidebarHeader {
    background-color: #0f172a;
    border-bottom: 1px solid #1e293b;
}

QLabel#sidebarTitle {
    color: #f8fafc;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.3px;
}

QLabel#sidebarSubtitle {
    color: #64748b;
    font-size: 11px;
    font-weight: 400;
}

QPushButton#tabButton {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-left: 3px solid transparent;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
    border-radius: 0;
}

QPushButton#tabButton:hover {
    background-color: #1e293b;
    color: #e2e8f0;
}

QPushButton#tabButton:checked {
    background-color: #1e3a5f;
    color: #60a5fa;
    border-left: 3px solid #3b82f6;
    font-weight: 600;
}

/* ── Content Area ── */
QWidget#contentArea {
    background-color: #f1f5f9;
}

/* ── Page Cards ── */
QWidget#pageCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}

QLabel#pageTitle {
    color: #0f172a;
    font-size: 22px;
    font-weight: 700;
    padding: 0;
}

QLabel#pageSubtitle {
    color: #64748b;
    font-size: 14px;
    font-weight: 400;
    padding: 0;
}

QLabel#sectionTitle {
    color: #1e293b;
    font-size: 15px;
    font-weight: 600;
}

QLabel#statusLabel {
    color: #475569;
    font-size: 13px;
    font-weight: 500;
}

/* ── Form Inputs ── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #f8fafc;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    selection-background-color: #3b82f6;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #3b82f6;
    background-color: #ffffff;
}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {
    border: 1px solid #94a3b8;
}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
}

QComboBox {
    padding: 6px 12px;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}

QComboBox:hover {
    border: 1px solid #94a3b8;
}

/* ── Buttons ── */
QPushButton#btnPrimary {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 7px 20px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#btnPrimary:hover {
    background-color: #1d4ed8;
}

QPushButton#btnPrimary:pressed {
    background-color: #1e40af;
}

QPushButton#btnSecondary {
    background-color: #f1f5f9;
    color: #475569;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 7px 20px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#btnSecondary:hover {
    background-color: #e2e8f0;
    color: #1e293b;
}

QPushButton#btnSecondary:checked {
    background-color: #dbeafe;
    color: #2563eb;
    border: 1px solid #bfdbfe;
    font-weight: 600;
}

QPushButton#btnDanger {
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 7px 20px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#btnDanger:hover {
    background-color: #dc2626;
}

QPushButton#btnGhost {
    background-color: transparent;
    color: #64748b;
    border: none;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#btnGhost:hover {
    background-color: #f1f5f9;
    color: #1e293b;
}

QPushButton#btnGhost:checked {
    background-color: #e2e8f0;
    color: #2563eb;
    font-weight: 600;
}

/* ── Tables ── */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #eff6ff;
    selection-color: #1e293b;
    font-size: 13px;
    outline: none;
}

QTableWidget::item {
    border-bottom: 1px solid #f1f5f9;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 8px 12px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
}

QTableWidget::indicator {
    width: 16px;
    height: 16px;
}

/* ── Scrollbars ── */
QScrollBar:vertical {
    background: #f1f5f9;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #f1f5f9;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 4px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #94a3b8;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Status Badges ── */
QLabel#badge {
    background-color: #dbeafe;
    color: #2563eb;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
}

/* ── Segmented Control (filtros) ── */
QPushButton#segmented {
    background-color: #f1f5f9;
    color: #64748b;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton#segmented:hover {
    background-color: #e2e8f0;
    color: #334155;
}

QPushButton#segmented:checked {
    background-color: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
    font-weight: 600;
}
'''
