"""
LayoutManager - builds and owns all widget layout for MainWindow.

Extracted from main_window.py to keep that file focused on event wiring.
MainWindow calls LayoutManager.build(main_window) once during __init__,
then accesses widgets via the public attributes below.

Public attributes set after build():
    activity_bar        ActivityBar
    sidebar_stack       QStackedWidget
    project_panel       QWidget  (sidebar index 0)
    project_view        ProjectView
    search_panel        SearchPanel
    git_panel           GitPanel
    debug_sidebar       DebugSidebarPanel
    extensions_panel    ExtensionsPanel
    main_splitter       QSplitter  (horizontal: sidebar | center)
    center_splitter     QSplitter  (horizontal: editor area | right panel)
    tab_widget          QTabWidget
    breadcrumb_bar      BreadcrumbBar
    right_panel         QWidget
    function_list       FunctionList
    terminal            Terminal
    terminal_dock       QDockWidget
    debugger_panel      DebuggerPanel
    debugger_dock       QDockWidget
"""

from PyQt6.QtWidgets import (
    QSplitter, QTabWidget, QDockWidget, QWidget,
    QHBoxLayout, QVBoxLayout, QStackedWidget,
)
from PyQt6.QtCore import Qt

from taara_ide.ui.activity_bar import ActivityBar
from taara_ide.ui.breadcrumb_bar import BreadcrumbBar
from taara_ide.ui.panels.project_view import ProjectView
from taara_ide.ui.panels.function_list import FunctionList
from taara_ide.ui.panels.terminal import Terminal
from taara_ide.ui.panels.debugger_panel import DebuggerPanel
from taara_ide.ui.panels.search_panel import SearchPanel
from taara_ide.ui.panels.git_panel import GitPanel
from taara_ide.ui.panels.extensions_panel import ExtensionsPanel
from taara_ide.ui.panels.debug_sidebar import DebugSidebarPanel


_TAB_BAR_STYLE = """
    QTabBar::tab {
        background: #d8dded;
        padding: 7px 16px;
        border: 1px solid #111;
        border-bottom: none;
    }
    QTabBar::tab:selected {
        background: #e9edd8;
        font-weight: bold;
        border: 1px solid #0259bf;
    }
    QTabBar::tab:hover {
        background: #cfd6b2;
    }
    QTabBar::tab:selected:!active {
        background: #2a2a2a;
    }
"""


class LayoutManager:
    """Builds the complete widget tree for MainWindow."""

    def build(self, window, settings_manager, debug_service) -> None:
        """
        Construct all widgets, attach them to *window*, and populate
        public attributes so MainWindow can reference them.
        """
        self._window = window

        # ── Activity bar ────────────────────────────────────────────────
        self.activity_bar = ActivityBar(window)

        # ── Sidebar (stacked panels) ─────────────────────────────────────
        self.sidebar_stack = QStackedWidget()
        self.sidebar_stack.setMinimumWidth(200)
        self.sidebar_stack.setMaximumWidth(400)

        # Index 0 – Project explorer
        # ProjectView is expensive to construct (first Qt widget init ~600ms).
        # Use a lightweight placeholder; the real widget is swapped in lazily
        # after the window is shown via LayoutManager.finish_deferred(window).
        self.project_panel = QWidget()
        _pl = QVBoxLayout(self.project_panel)
        _pl.setContentsMargins(0, 0, 0, 0)
        self.project_view = None          # filled by finish_deferred()
        self._project_panel_layout = _pl  # kept for deferred swap
        self.sidebar_stack.addWidget(self.project_panel)

        # Index 1 – Search
        self.search_panel = SearchPanel(window)
        self.sidebar_stack.addWidget(self.search_panel)

        # Index 2 – Git
        self.git_panel = GitPanel(window)
        self.sidebar_stack.addWidget(self.git_panel)

        # Index 3 – Debug sidebar
        self.debug_sidebar = DebugSidebarPanel(window)
        self.sidebar_stack.addWidget(self.debug_sidebar)

        # Index 4 – Extensions
        self.extensions_panel = ExtensionsPanel(window)
        self.sidebar_stack.addWidget(self.extensions_panel)

        # ── Editor area ──────────────────────────────────────────────────
        self.breadcrumb_bar = BreadcrumbBar(window)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabBar().setStyleSheet(_TAB_BAR_STYLE)

        editor_area = QWidget()
        _el = QVBoxLayout(editor_area)
        _el.setContentsMargins(0, 0, 0, 0)
        _el.setSpacing(0)
        _el.addWidget(self.breadcrumb_bar)
        _el.addWidget(self.tab_widget)

        # ── Right panel (function list) ──────────────────────────────────
        self.function_list = FunctionList(window)
        self.right_panel = QWidget()
        _rl = QVBoxLayout(self.right_panel)
        _rl.setContentsMargins(0, 0, 0, 0)
        _rl.addWidget(self.function_list)

        right_panel_visible = settings_manager.get_right_panel_width() != 0
        self.right_panel.setVisible(right_panel_visible)

        # ── Splitters ────────────────────────────────────────────────────
        self.center_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.center_splitter.addWidget(editor_area)
        self.center_splitter.addWidget(self.right_panel)
        if right_panel_visible:
            self.center_splitter.setSizes([600, 300])
        else:
            self.center_splitter.setSizes([800, 0])

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(self.sidebar_stack)
        self.main_splitter.addWidget(self.center_splitter)
        self.main_splitter.setSizes([250, 750])

        # ── Central widget ───────────────────────────────────────────────
        central = QWidget()
        _ml = QHBoxLayout(central)
        _ml.setContentsMargins(0, 0, 0, 0)
        _ml.setSpacing(0)
        _ml.addWidget(self.activity_bar)
        _ml.addWidget(self.main_splitter)
        window.setCentralWidget(central)

        # ── Dock widgets ─────────────────────────────────────────────────
        self.terminal = Terminal(window)
        self.terminal_dock = QDockWidget("Terminal", window)
        self.terminal_dock.setObjectName("TerminalDock")
        self.terminal_dock.setWidget(self.terminal)
        self.terminal_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.terminal_dock)
        self.terminal_dock.hide()

        self.debugger_panel = DebuggerPanel(debug_service, window)
        self.debugger_dock = QDockWidget("Debugger", window)
        self.debugger_dock.setObjectName("DebuggerDock")
        self.debugger_dock.setWidget(self.debugger_panel)
        self.debugger_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.debugger_dock)
        self.debugger_dock.hide()

    def finish_deferred(self, window) -> None:
        """
        Build widgets that were deferred to keep initial startup fast.
        Call this via QTimer.singleShot(0, ...) after window.show().
        """
        from PyQt6.QtWidgets import QDockWidget
        self.project_view = ProjectView(window)
        self.project_view.setTitleBarWidget(QWidget())
        self.project_view.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self._project_panel_layout.addWidget(self.project_view)
