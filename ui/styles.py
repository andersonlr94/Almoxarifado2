FUSION_QSS = '''
QMainWindow {
    background-color: #f8fafc;
}

/* ── Sidebar ── */
QWidget#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #eef1f6;
}

QPushButton#sidebarToggle {
    background-color: transparent;
    color: #6366f1;
    border: 1.5px solid #e5e7eb;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
}

QPushButton#sidebarToggle:hover {
    background-color: #eef2ff;
    border-color: #c7d2fe;
    color: #4f46e5;
}

QPushButton#sidebarToggle:pressed {
    background-color: #c7d2fe;
}

QWidget#sidebarHeader {
    background-color: #ffffff;
    border-bottom: 1px solid #eef1f6;
}

QLabel#sidebarTitle {
    color: #1e1b4b;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.2px;
}

QLabel#sidebarSubtitle {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 400;
}

QPushButton#tabButton {
    background-color: transparent;
    color: #64748b;
    border: none;
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 500;
    text-align: left;
    margin: 1px 8px;
}

QPushButton#tabButton:hover {
    background-color: #f5f3ff;
    color: #6366f1;
}

QPushButton#tabButton:checked {
    background-color: #eef2ff;
    color: #4f46e5;
    font-weight: 600;
    border-left: none;
    margin-left: 8px;
}

QPushButton#tabSubButton {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    padding: 8px 16px 8px 28px;
    font-size: 12px;
    font-weight: 400;
    text-align: left;
    margin: 1px 12px;
}

QPushButton#tabSubButton:hover {
    background-color: #faf5ff;
    color: #7c3aed;
}

QPushButton#tabSubButton:checked {
    background-color: #f3e8ff;
    color: #7c3aed;
    font-weight: 600;
    border-left: none;
}

/* ── Content Area ── */
QWidget#contentArea {
    background-color: #f8fafc;
}

/* ── Page Cards ── */
QWidget#pageCard {
    background-color: #ffffff;
    border: 1px solid #eef1f6;
    border-radius: 16px;
}

QLabel#pageTitle {
    color: #1e1b4b;
    font-size: 22px;
    font-weight: 700;
    padding: 0;
}

QLabel#pageSubtitle {
    color: #94a3b8;
    font-size: 14px;
    font-weight: 400;
    padding: 0;
}

QLabel#sectionTitle {
    color: #374151;
    font-size: 15px;
    font-weight: 600;
}

QLabel#statusLabel {
    color: #6b7280;
    font-size: 13px;
    font-weight: 500;
}

/* ── Form Inputs ── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {
    background-color: #ffffff;
    color: #374151;
    border: 1.5px solid #e5e7eb;
    border-radius: 10px;
    padding: 7px 14px;
    font-size: 13px;
    selection-background-color: #6366f1;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {
    border: 1.5px solid #6366f1;
    background-color: #ffffff;
}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover, QPlainTextEdit:hover {
    border: 1.5px solid #c4b5fd;
}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
    background-color: #f9fafb;
    color: #9ca3af;
}

QComboBox {
    padding: 7px 14px;
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
    border: 1.5px solid #c4b5fd;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 4px;
    selection-background-color: #eef2ff;
    selection-color: #1e1b4b;
    outline: none;
}

QComboBox QAbstractItemView::item {
    padding: 7px 14px;
    border-radius: 6px;
    min-height: 24px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #f5f3ff;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #eef2ff;
    color: #4f46e5;
    font-weight: 600;
}

QComboBox QListView {
    border-radius: 10px;
}

QComboBox QAbstractItemView QScrollBar:vertical {
    width: 6px;
    border-radius: 3px;
}

QComboBox QAbstractItemView QScrollBar::handle:vertical {
    background: #d1d5db;
    border-radius: 3px;
    min-height: 20px;
}

QComboBox QAbstractItemView QScrollBar::add-line:vertical,
QComboBox QAbstractItemView QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Date Edit ── */
QDateEdit {
    background-color: #ffffff;
    color: #374151;
    border: 1.5px solid #e5e7eb;
    border-radius: 8px;
    padding: 3px 6px;
    font-size: 13px;
    selection-background-color: #6366f1;
}

QDateEdit:focus {
    border: 1.5px solid #6366f1;
    background-color: #ffffff;
}

QDateEdit:hover {
    border: 1.5px solid #c4b5fd;
}

QDateEdit::drop-down {
    border: none;
    padding-right: 2px;
    width: 16px;
}

QDateEdit::down-arrow {
    width: 10px;
    height: 10px;
}

/* ── Calendar Popup ── */
QCalendarWidget {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
}

QCalendarWidget QToolButton {
    color: #374151;
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 4px 8px;
    font-size: 13px;
    font-weight: 600;
}

QCalendarWidget QToolButton:hover {
    background-color: #f5f3ff;
}

QCalendarWidget QToolButton::menu-indicator {
    image: none;
}

QCalendarWidget QAbstractItemView {
    background-color: #ffffff;
    selection-background-color: #6366f1;
    selection-color: #ffffff;
    color: #374151;
    font-size: 12px;
    outline: none;
}

QCalendarWidget QAbstractItemView:disabled {
    color: #d1d5db;
}

QCalendarWidget QAbstractItemView:alternate {
    background-color: #f9fafb;
}

/* ── Clear Button ── */
QPushButton#btnClear {
    background-color: #f9fafb;
    color: #9ca3af;
    border: 1.5px solid #e5e7eb;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
    padding: 0;
}

QPushButton#btnClear:hover {
    background-color: #fef2f2;
    color: #f87171;
    border-color: #fecaca;
}

QPushButton#btnClear:pressed {
    background-color: #fee2e2;
    color: #ef4444;
}

/* ── Buttons ── */
QPushButton#btnPrimary {
    background-color: #6366f1;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#btnPrimary:hover {
    background-color: #4f46e5;
}

QPushButton#btnPrimary:pressed {
    background-color: #4338ca;
}

QPushButton#btnSecondary {
    background-color: #f9fafb;
    color: #6b7280;
    border: 1.5px solid #e5e7eb;
    border-radius: 10px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#btnSecondary:hover {
    background-color: #f3f4f6;
    color: #374151;
    border-color: #d1d5db;
}

QPushButton#btnSecondary:checked {
    background-color: #eef2ff;
    color: #4f46e5;
    border: 1.5px solid #c7d2fe;
    font-weight: 600;
}

QPushButton#btnDanger {
    background-color: #f43f5e;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#btnDanger:hover {
    background-color: #e11d48;
}

QPushButton#btnGhost {
    background-color: transparent;
    color: #9ca3af;
    border: none;
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#btnGhost:hover {
    background-color: #f5f3ff;
    color: #6366f1;
}

QPushButton#btnGhost:checked {
    background-color: #eef2ff;
    color: #4f46e5;
    font-weight: 600;
}

/* ── Gradient Buttons ── */
QPushButton#btnGradientIndigo {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#btnGradientIndigo:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
}

QPushButton#btnGradientIndigo:pressed {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #6d28d9);
}

QPushButton#btnGradientGreen {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #06b6d4);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#btnGradientGreen:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #0891b2);
}

QPushButton#btnGradientGreen:pressed {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #0e7490);
}

QPushButton#btnGradientOrange {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f59e0b, stop:1 #f97316);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#btnGradientOrange:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d97706, stop:1 #ea580c);
}

QPushButton#btnGradientOrange:pressed {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b45309, stop:1 #c2410c);
}

QPushButton#btnGradientRose {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f43f5e, stop:1 #e11d48);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#btnGradientRose:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e11d48, stop:1 #be123c);
}

QPushButton#btnGradientRose:pressed {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #be123c, stop:1 #9f1239);
}

QPushButton#btnGradientTeal {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #14b8a6, stop:1 #0ea5e9);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#btnGradientTeal:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d9488, stop:1 #0284c7);
}

QPushButton#btnGradientTeal:pressed {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f766e, stop:1 #0369a1);
}

QPushButton#btnGradientPurple {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #a855f7, stop:1 #ec4899);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#btnGradientPurple:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9333ea, stop:1 #db2777);
}

QPushButton#btnGradientPurple:pressed {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7e22ce, stop:1 #be185d);
}

QPushButton#btnGradientChartreuse {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #84cc16, stop:1 #22c55e);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#btnGradientChartreuse:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #65a30d, stop:1 #16a34a);
}

QPushButton#btnGradientChartreuse:pressed {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4d7c0f, stop:1 #15803d);
}

QPushButton#btnGradientAmber {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #fbbf24, stop:1 #f59e0b);
    color: #1e1b4b;
    border: none;
    border-radius: 10px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#btnGradientAmber:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f59e0b, stop:1 #d97706);
    color: #ffffff;
}

QPushButton#btnGradientAmber:pressed {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d97706, stop:1 #b45309);
}

/* ── Stat Cards ── */
QWidget#statCard {
    background-color: #ffffff;
    border: 1px solid #eef1f6;
    border-radius: 14px;
}

QLabel#statLabel {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}

QLabel#statValue {
    color: #1e1b4b;
    font-size: 18px;
    font-weight: 700;
}

/* ── Status Tabs (Prog. Agulhas) ── */
QPushButton#statusTab {
    background-color: transparent;
    color: #94a3b8;
    border: 1.5px solid transparent;
    border-radius: 10px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton#statusTab:hover {
    background-color: #f9fafb;
    border-color: #e5e7eb;
}

QPushButton#statusTab:checked {
    background-color: #eef2ff;
    border-color: #c7d2fe;
    font-weight: 600;
}

/* ── Field Labels ── */
QLabel#fieldLabel {
    color: #6b7280;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    padding-left: 2px;
}

QLabel#infoValue {
    color: #6366f1;
    font-size: 13px;
    font-weight: 600;
}

/* ── Tables ── */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #eef1f6;
    border-radius: 12px;
    gridline-color: #f3f4f6;
    selection-background-color: #eef2ff;
    selection-color: #1e1b4b;
    font-size: 13px;
    outline: none;
}

QTableWidget::item {
    border-bottom: 1px solid #f3f4f6;
}

QHeaderView::section {
    background-color: #f9fafb;
    color: #9ca3af;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    padding: 10px 14px;
    border: none;
    border-bottom: 1.5px solid #e5e7eb;
}

QTableWidget::indicator {
    width: 16px;
    height: 16px;
}

/* ── Scrollbars ── */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #d1d5db;
    border-radius: 3px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #9ca3af;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal {
    background: #d1d5db;
    border-radius: 3px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #9ca3af;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Status Badges ── */
QLabel#badge {
    background-color: #eef2ff;
    color: #4f46e5;
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 12px;
    font-weight: 600;
}

/* ── Segmented Control (filtros) ── */
QPushButton#segmented {
    background-color: #f9fafb;
    color: #9ca3af;
    border: 1.5px solid #e5e7eb;
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton#segmented:hover {
    background-color: #f3f4f6;
    color: #6b7280;
}

QPushButton#segmented:checked {
    background-color: #6366f1;
    color: #ffffff;
    border-color: #6366f1;
    font-weight: 600;
}

/* ── Edit Mode Button (Controle Pedidos) ── */
QPushButton#btnEditMode {
    background-color: #f9fafb;
    color: #6b7280;
    border: 1.5px solid #e5e7eb;
    border-radius: 10px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#btnEditMode:hover {
    background-color: #f3f4f6;
    color: #374151;
    border-color: #d1d5db;
}

QPushButton#btnEditMode:checked {
    background-color: #10b981;
    color: #ffffff;
    border: 1.5px solid #059669;
    font-weight: 600;
}

QPushButton#btnEditMode:checked:hover {
    background-color: #059669;
}

/* ── Specific Table for Digitar AE page ── */
QTableWidget#tabelaDigitarAE {
    font-size: 11px;
}

QTableWidget#tabelaDigitarAE QHeaderView::section {
    font-size: 10px;
    padding: 4px 6px;
}

/* ── Specific Table for Itens com Estoque Zero page ── */
QTableWidget#tabelaItensZero {
    font-size: 11px;
}

QTableWidget#tabelaItensZero QHeaderView::section {
    font-size: 10px;
    padding: 4px 6px;
}
'''
