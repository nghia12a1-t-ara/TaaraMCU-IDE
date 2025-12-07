"""
Search Panel - VSCode-like search in files functionality
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QTreeWidget, QTreeWidgetItem, QLabel,
    QToolButton, QFrame, QSizePolicy, QProgressBar,
    QMenu, QComboBox, QApplication, QStyledItemDelegate,
    QStyle
)
from PyQt6.QtCore import pyqtSignal as Signal, Qt, QThread, QTimer, QSettings
from PyQt6.QtGui import QIcon, QColor, QFont, QAction, QPainter, QTextDocument, QAbstractTextDocumentLayout, QKeyEvent
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class SearchWorker(QThread):
    """Background worker for searching files"""
    
    result_found = Signal(str, int, str, int, int)  # file_path, line_num, line_text, match_start, match_end
    search_finished = Signal(int, int)  # total_matches, total_files
    progress_update = Signal(int)  # percentage
    
    def __init__(self, project_path: str, pattern: re.Pattern, extensions: set):
        super().__init__()
        self.project_path = project_path
        self.pattern = pattern
        self.extensions = extensions
        self._stop_requested = False
    
    def stop(self):
        self._stop_requested = True
    
    def run(self):
        total_matches = 0
        total_files = 0
        
        # Count total files first for progress
        all_files = []
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'__pycache__', 'node_modules', '.git', 'venv', 'env'}]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in self.extensions or not self.extensions:
                    all_files.append(os.path.join(root, file))
        
        for idx, file_path in enumerate(all_files):
            if self._stop_requested:
                break
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Skip binary files
                    if '\x00' in content[:1024]:
                        continue
                    
                    lines = content.split('\n')
                    file_has_match = False
                    
                    for line_num, line in enumerate(lines, 1):
                        for match in self.pattern.finditer(line):
                            if not file_has_match:
                                total_files += 1
                                file_has_match = True
                            total_matches += 1
                            self.result_found.emit(
                                file_path, 
                                line_num, 
                                line.strip(),
                                match.start(),
                                match.end()
                            )
            except Exception:
                continue
            
            # Update progress
            progress = int((idx + 1) / len(all_files) * 100)
            self.progress_update.emit(progress)
        
        self.search_finished.emit(total_matches, total_files)


class HighlightDelegate(QStyledItemDelegate):
    """Custom delegate to render HTML in tree items for search highlighting"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = QTextDocument()
    
    def paint(self, painter: QPainter, option, index):
        """Paint item with HTML support"""
        # Get the item data
        item_type = index.data(Qt.ItemDataRole.UserRole + 2)
        
        # Only use HTML for match items, not file items
        if item_type != "match":
            super().paint(painter, option, index)
            return
        
        painter.save()
        
        # Draw selection/hover background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#094771"))
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor("#2A2D2E"))
        
        # Setup document for HTML rendering
        self._doc.setDefaultFont(option.font)
        
        html = index.data(Qt.ItemDataRole.UserRole + 3)  # Get HTML from UserRole + 3
        if html:
            self._doc.setHtml(html)
        else:
            self._doc.setPlainText(index.data(Qt.ItemDataRole.DisplayRole) or "")
        
        # Set text color
        self._doc.setDefaultStyleSheet("body { color: #CCCCCC; }")
        
        # Paint the document
        painter.translate(option.rect.topLeft())
        ctx = QAbstractTextDocumentLayout.PaintContext()
        self._doc.documentLayout().draw(painter, ctx)
        
        painter.restore()
    
    def sizeHint(self, option, index):
        """Return size hint for item"""
        item_type = index.data(Qt.ItemDataRole.UserRole + 2)
        if item_type != "match":
            return super().sizeHint(option, index)
        
        self._doc.setDefaultFont(option.font)
        html = index.data(Qt.ItemDataRole.UserRole + 3)
        if html:
            self._doc.setHtml(html)
        else:
            self._doc.setPlainText(index.data(Qt.ItemDataRole.DisplayRole) or "")
        
        return self._doc.size().toSize()


class SearchLineEdit(QLineEdit):
    """QLineEdit with search history support using up/down arrows"""
    
    MAX_HISTORY = 50
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: List[str] = []
        self._history_index = -1
        self._current_text = ""
        self._load_history()
    
    def _load_history(self):
        """Load search history from settings"""
        settings = QSettings("TaaraIDE", "TaaraIDE")
        history = settings.value("search/history", [])
        if isinstance(history, list):
            self._history = history[:self.MAX_HISTORY]
        else:
            self._history = []
    
    def _save_history(self):
        """Save search history to settings"""
        settings = QSettings("TaaraIDE", "TaaraIDE")
        settings.setValue("search/history", self._history[:self.MAX_HISTORY])
    
    def add_to_history(self, text: str):
        """Add search term to history"""
        if not text or not text.strip():
            return
        
        # Remove if already exists (to move to top)
        if text in self._history:
            self._history.remove(text)
        
        # Insert at beginning
        self._history.insert(0, text)
        
        # Limit size
        self._history = self._history[:self.MAX_HISTORY]
        
        # Reset index
        self._history_index = -1
        
        # Save to settings
        self._save_history()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle up/down arrow keys for history navigation"""
        if event.key() == Qt.Key.Key_Up:
            self._navigate_history(-1)  # Go back in history
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Down:
            self._navigate_history(1)  # Go forward in history
            event.accept()
            return
        
        super().keyPressEvent(event)
    
    def _navigate_history(self, direction: int):
        """Navigate through search history"""
        if not self._history:
            return
        
        # Save current text if starting navigation
        if self._history_index == -1:
            self._current_text = self.text()
        
        # Calculate new index
        new_index = self._history_index + direction
        
        # Going down past -1 restores current text
        if new_index < -1:
            new_index = -1
        elif new_index >= len(self._history):
            new_index = len(self._history) - 1
        
        self._history_index = new_index
        
        # Set text based on index
        if self._history_index == -1:
            self.setText(self._current_text)
        else:
            self.setText(self._history[self._history_index])
        
        # Move cursor to end
        self.setCursorPosition(len(self.text()))
    
    def reset_history_index(self):
        """Reset history navigation index"""
        self._history_index = -1
        self._current_text = ""


class SearchPanel(QWidget):
    """VSCode-like panel for searching in files"""
    
    # Signals
    file_requested = Signal(str, int)  # file_path, line_number
    search_term_changed = Signal(str, bool, bool, bool)  # term, case_sensitive, whole_word, regex
    
    # Common code extensions
    CODE_EXTENSIONS = {
        '.c', '.h', '.cpp', '.hpp', '.cc', '.cxx',
        '.py', '.pyw', '.pyi',
        '.js', '.jsx', '.ts', '.tsx',
        '.java', '.kt', '.scala',
        '.go', '.rs', '.rb',
        '.html', '.htm', '.css', '.scss', '.sass', '.less',
        '.json', '.xml', '.yaml', '.yml', '.toml',
        '.md', '.txt', '.rst', '.log',
        '.sh', '.bash', '.zsh', '.bat', '.cmd', '.ps1',
        '.sql', '.php', '.swift', '.m', '.mm',
        '.asm', '.s', '.S',
        '.mk', '.cmake', '.Makefile',
        '.gitignore', '.env', '.ini', '.cfg', '.conf'
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_path = None
        self._search_worker: Optional[SearchWorker] = None
        self._results: Dict[str, List[Tuple[int, str, int, int]]] = {}
        self._file_items: Dict[str, QTreeWidgetItem] = {}
        self._is_replace_visible = False
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the VSCode-like search panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main container with padding
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(8)
        
        # Search section
        self._setup_search_section(container_layout)
        
        # Replace section (collapsible)
        self._setup_replace_section(container_layout)
        
        # Filters section
        self._setup_filters_section(container_layout)
        
        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumHeight(3)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.hide()
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: transparent;
            }
            QProgressBar::chunk {
                background: #007ACC;
            }
        """)
        container_layout.addWidget(self._progress_bar)
        
        # Results section
        self._setup_results_section(container_layout)
        
        layout.addWidget(container)
        
        # Apply styling
        self._apply_styling()
    
    def _setup_search_section(self, layout: QVBoxLayout):
        """Setup search input with options"""
        search_container = QFrame()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)
        
        # Toggle replace button
        self._toggle_replace_btn = QToolButton()
        self._toggle_replace_btn.setText("▶")
        self._toggle_replace_btn.setFixedSize(20, 24)
        self._toggle_replace_btn.setToolTip("Toggle Replace")
        self._toggle_replace_btn.clicked.connect(self._toggle_replace)
        search_layout.addWidget(self._toggle_replace_btn)
        
        # Search input with options inside
        search_input_container = QFrame()
        search_input_container.setObjectName("searchInputContainer")
        search_input_layout = QHBoxLayout(search_input_container)
        search_input_layout.setContentsMargins(8, 4, 4, 4)
        search_input_layout.setSpacing(4)
        
        self._search_input = SearchLineEdit()
        self._search_input.setPlaceholderText("Search")
        self._search_input.setFrame(False)
        self._search_input.returnPressed.connect(self._do_search)
        search_input_layout.addWidget(self._search_input)
        
        # Search options buttons (inside input)
        self._case_btn = QToolButton()
        self._case_btn.setText("Aa")
        self._case_btn.setCheckable(True)
        self._case_btn.setToolTip("Match Case (Alt+C)")
        self._case_btn.setFixedSize(24, 20)
        search_input_layout.addWidget(self._case_btn)
        self._case_btn.clicked.connect(self._do_search)
        
        self._word_btn = QToolButton()
        self._word_btn.setText("ab")
        self._word_btn.setCheckable(True)
        self._word_btn.setToolTip("Match Whole Word (Alt+W)")
        self._word_btn.setFixedSize(24, 20)
        search_input_layout.addWidget(self._word_btn)
        self._word_btn.clicked.connect(self._do_search)
        
        self._regex_btn = QToolButton()
        self._regex_btn.setText(".*")
        self._regex_btn.setCheckable(True)
        self._regex_btn.setToolTip("Use Regular Expression (Alt+R)")
        self._regex_btn.setFixedSize(24, 20)
        search_input_layout.addWidget(self._regex_btn)
        self._regex_btn.clicked.connect(self._do_search)
        
        search_layout.addWidget(search_input_container, 1)
        
        layout.addWidget(search_container)
    
    def _setup_replace_section(self, layout: QVBoxLayout):
        """Setup replace input section"""
        self._replace_container = QFrame()
        self._replace_container.hide()
        replace_layout = QHBoxLayout(self._replace_container)
        replace_layout.setContentsMargins(24, 0, 0, 0)
        replace_layout.setSpacing(4)
        
        # Replace input
        replace_input_container = QFrame()
        replace_input_container.setObjectName("replaceInputContainer")
        replace_input_layout = QHBoxLayout(replace_input_container)
        replace_input_layout.setContentsMargins(8, 4, 4, 4)
        replace_input_layout.setSpacing(4)
        
        self._replace_input = QLineEdit()
        self._replace_input.setPlaceholderText("Replace")
        self._replace_input.setFrame(False)
        replace_input_layout.addWidget(self._replace_input)
        
        # Preserve case option
        self._preserve_case_btn = QToolButton()
        self._preserve_case_btn.setText("AB")
        self._preserve_case_btn.setCheckable(True)
        self._preserve_case_btn.setToolTip("Preserve Case")
        self._preserve_case_btn.setFixedSize(24, 20)
        replace_input_layout.addWidget(self._preserve_case_btn)
        
        replace_layout.addWidget(replace_input_container, 1)
        
        # Replace buttons
        self._replace_btn = QToolButton()
        self._replace_btn.setText("⟳")
        self._replace_btn.setToolTip("Replace (Ctrl+Shift+1)")
        self._replace_btn.setFixedSize(24, 24)
        self._replace_btn.clicked.connect(self._replace_next)
        replace_layout.addWidget(self._replace_btn)
        
        self._replace_all_btn = QToolButton()
        self._replace_all_btn.setText("⟳⟳")
        self._replace_all_btn.setToolTip("Replace All (Ctrl+Alt+Enter)")
        self._replace_all_btn.setFixedSize(28, 24)
        self._replace_all_btn.clicked.connect(self._replace_all)
        replace_layout.addWidget(self._replace_all_btn)
        
        layout.addWidget(self._replace_container)
    
    def _setup_filters_section(self, layout: QVBoxLayout):
        """Setup files to include/exclude filters"""
        self._filters_container = QFrame()
        filters_layout = QVBoxLayout(self._filters_container)
        filters_layout.setContentsMargins(24, 4, 0, 0)
        filters_layout.setSpacing(4)
        
        # Toggle filters button and label
        filters_header = QHBoxLayout()
        self._toggle_filters_btn = QToolButton()
        self._toggle_filters_btn.setText("...")
        self._toggle_filters_btn.setToolTip("Toggle Search Details")
        self._toggle_filters_btn.setFixedSize(24, 20)
        self._toggle_filters_btn.setCheckable(True)
        self._toggle_filters_btn.clicked.connect(self._toggle_filters)
        filters_header.addWidget(self._toggle_filters_btn)
        filters_header.addStretch()
        filters_layout.addLayout(filters_header)
        
        # Filters inputs (hidden by default)
        self._filters_inputs = QWidget()
        self._filters_inputs.hide()
        filters_inputs_layout = QVBoxLayout(self._filters_inputs)
        filters_inputs_layout.setContentsMargins(0, 4, 0, 0)
        filters_inputs_layout.setSpacing(4)
        
        # Files to include
        self._include_input = QLineEdit()
        self._include_input.setPlaceholderText("files to include (e.g., *.c, *.h)")
        filters_inputs_layout.addWidget(self._include_input)
        
        # Files to exclude
        self._exclude_input = QLineEdit()
        self._exclude_input.setPlaceholderText("files to exclude (e.g., *test*, build/)")
        filters_inputs_layout.addWidget(self._exclude_input)
        
        filters_layout.addWidget(self._filters_inputs)
        
        layout.addWidget(self._filters_container)
    
    def _setup_results_section(self, layout: QVBoxLayout):
        """Setup results tree"""
        # Results header
        results_header = QHBoxLayout()
        
        self._results_label = QLabel("RESULTS")
        self._results_label.setObjectName("resultsLabel")
        results_header.addWidget(self._results_label)
        
        results_header.addStretch()
        
        # Action buttons
        self._collapse_all_btn = QToolButton()
        self._collapse_all_btn.setText("⊟")
        self._collapse_all_btn.setToolTip("Collapse All")
        self._collapse_all_btn.setFixedSize(20, 20)
        self._collapse_all_btn.clicked.connect(self._collapse_all)
        results_header.addWidget(self._collapse_all_btn)
        
        self._expand_all_btn = QToolButton()
        self._expand_all_btn.setText("⊞")
        self._expand_all_btn.setToolTip("Expand All")
        self._expand_all_btn.setFixedSize(20, 20)
        self._expand_all_btn.clicked.connect(self._expand_all)
        results_header.addWidget(self._expand_all_btn)
        
        self._clear_btn = QToolButton()
        self._clear_btn.setText("✕")
        self._clear_btn.setToolTip("Clear Search Results")
        self._clear_btn.setFixedSize(20, 20)
        self._clear_btn.clicked.connect(self._clear_results)
        results_header.addWidget(self._clear_btn)
        
        layout.addLayout(results_header)
        
        # Results tree
        self._results_tree = QTreeWidget()
        self._results_tree.setHeaderHidden(True)
        self._results_tree.setIndentation(16)
        self._results_tree.setAnimated(True)
        self._results_tree.setExpandsOnDoubleClick(False)
        self._results_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._results_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._results_tree.customContextMenuRequested.connect(self._show_context_menu)
        
        self._highlight_delegate = HighlightDelegate(self._results_tree)
        self._results_tree.setItemDelegate(self._highlight_delegate)
        
        layout.addWidget(self._results_tree, 1)
        
        # Status bar
        self._status_label = QLabel("")
        self._status_label.setObjectName("statusLabel")
        layout.addWidget(self._status_label)
    
    def _connect_signals(self):
        """Connect signals"""
        # Debounce search on text change
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
        self._search_input.textChanged.connect(lambda: self._search_timer.start(300))
    
    def _apply_styling(self):
        """Apply VSCode-like styling"""
        self.setStyleSheet("""
            QWidget {
                background-color: #252526;
                color: #CCCCCC;
            }
            
            QFrame#searchInputContainer, QFrame#replaceInputContainer {
                background-color: #3C3C3C;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
            }
            
            QFrame#searchInputContainer:focus-within, QFrame#replaceInputContainer:focus-within {
                border-color: #007ACC;
            }
            
            QLineEdit {
                background: transparent;
                border: none;
                color: #CCCCCC;
                font-size: 13px;
                padding: 2px;
            }
            
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                color: #CCCCCC;
                font-size: 11px;
            }
            
            QToolButton:hover {
                background-color: #4D4D4D;
            }
            
            QToolButton:checked {
                background-color: #094771;
                border-color: #007ACC;
            }
            
            QToolButton:pressed {
                background-color: #3D3D3D;
            }
            
            QLabel#resultsLabel {
                color: #BBBBBB;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 0;
            }
            
            QLabel#statusLabel {
                color: #858585;
                font-size: 12px;
                padding: 4px 0;
            }
            
            QTreeWidget {
                background-color: #252526;
                border: none;
                outline: none;
                font-size: 13px;
            }
            
            QTreeWidget::item {
                padding: 2px 4px;
                border-radius: 2px;
            }
            
            QTreeWidget::item:hover {
                background-color: #2A2D2E;
            }
            
            QTreeWidget::item:selected {
                background-color: #094771;
            }
            
            QTreeWidget::branch {
                background: transparent;
            }
            
            QTreeWidget::branch:has-children:closed {
                image: url(none);
                border-image: none;
            }
            
            QTreeWidget::branch:has-children:open {
                image: url(none);
                border-image: none;
            }
            
            QScrollBar:vertical {
                background: #252526;
                width: 10px;
                margin: 0;
            }
            
            QScrollBar::handle:vertical {
                background: #424242;
                min-height: 20px;
                border-radius: 5px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #4F4F4F;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
    
    def _toggle_replace(self):
        """Toggle replace section visibility"""
        self._is_replace_visible = not self._is_replace_visible
        self._replace_container.setVisible(self._is_replace_visible)
        self._toggle_replace_btn.setText("▼" if self._is_replace_visible else "▶")
    
    def _toggle_filters(self):
        """Toggle filters section visibility"""
        is_visible = self._toggle_filters_btn.isChecked()
        self._filters_inputs.setVisible(is_visible)
    
    def set_project_path(self, path: str):
        """Set the project path for searching"""
        self._project_path = path
    
    def _get_search_extensions(self) -> set:
        """Get file extensions to search based on include filter"""
        include_text = self._include_input.text().strip()
        if not include_text:
            return self.CODE_EXTENSIONS
        
        extensions = set()
        for pattern in include_text.split(','):
            pattern = pattern.strip()
            if pattern.startswith('*.'):
                ext = pattern[1:]  # Get .ext
                extensions.add(ext)
            elif pattern.startswith('.'):
                extensions.add(pattern)
        
        return extensions if extensions else self.CODE_EXTENSIONS
    
    def _should_exclude(self, file_path: str) -> bool:
        """Check if file should be excluded"""
        exclude_text = self._exclude_input.text().strip()
        if not exclude_text:
            return False
        
        rel_path = os.path.relpath(file_path, self._project_path) if self._project_path else file_path
        
        for pattern in exclude_text.split(','):
            pattern = pattern.strip()
            if not pattern:
                continue
            
            # Simple glob matching
            if pattern.startswith('*') and pattern.endswith('*'):
                if pattern[1:-1] in rel_path:
                    return True
            elif pattern.endswith('/') or pattern.endswith('\\'):
                if rel_path.startswith(pattern.rstrip('/\\')):
                    return True
            elif pattern.startswith('*'):
                if rel_path.endswith(pattern[1:]):
                    return True
            elif pattern.endswith('*'):
                if rel_path.startswith(pattern[:-1]):
                    return True
            elif pattern in rel_path:
                return True
        
        return False
    
    def _do_search(self):
        """Start search operation"""
        query = self._search_input.text().strip()
        
        if not query:
            self._clear_results()
            self.search_term_changed.emit("", False, False, False)
            return
        
        self._search_input.add_to_history(query)
        self._search_input.reset_history_index()
        
        # Stop previous search
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.stop()
            self._search_worker.wait()
        
        # Clear previous results
        self._results_tree.clear()
        self._results.clear()
        self._file_items.clear()
        
        # Build pattern
        case_sensitive = self._case_btn.isChecked()
        whole_word = self._word_btn.isChecked()
        use_regex = self._regex_btn.isChecked()
        
        self.search_term_changed.emit(query, case_sensitive, whole_word, use_regex)
        
        if use_regex:
            try:
                pattern = re.compile(query, 0 if case_sensitive else re.IGNORECASE)
            except re.error as e:
                self._status_label.setText(f"Invalid regex: {e}")
                return
        else:
            if whole_word:
                query_pattern = r'\b' + re.escape(query) + r'\b'
            else:
                query_pattern = re.escape(query)
            pattern = re.compile(query_pattern, 0 if case_sensitive else re.IGNORECASE)
        
        # Start search worker
        extensions = self._get_search_extensions()
        self._search_worker = SearchWorker(self._project_path, pattern, extensions)
        self._search_worker.result_found.connect(self._on_result_found)
        self._search_worker.search_finished.connect(self._on_search_finished)
        self._search_worker.progress_update.connect(self._on_progress_update)
        
        self._progress_bar.setValue(0)
        self._progress_bar.show()
        self._status_label.setText("Searching...")
        
        self._search_worker.start()
    
    def _on_result_found(self, file_path: str, line_num: int, line_text: str, match_start: int, match_end: int):
        """Handle search result found"""
        if self._should_exclude(file_path):
            return
        
        # Get or create file item
        if file_path not in self._file_items:
            rel_path = os.path.relpath(file_path, self._project_path)
            file_item = QTreeWidgetItem()
            file_item.setText(0, f"📄 {rel_path}")
            file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            file_item.setData(0, Qt.ItemDataRole.UserRole + 2, "file")
            file_item.setForeground(0, QColor("#E8AB6B"))
            self._results_tree.addTopLevelItem(file_item)
            self._file_items[file_path] = file_item
            self._results[file_path] = []
        
        file_item = self._file_items[file_path]
        self._results[file_path].append((line_num, line_text, match_start, match_end))
        
        # Create match item with highlighted text
        match_item = QTreeWidgetItem()
        
        search_text = self._search_input.text().strip()
        highlighted_html = self._create_highlighted_html(line_num, line_text, search_text)
        
        # Plain text for accessibility/fallback
        display_text = f"  {line_num}: {line_text[:120]}"
        if len(line_text) > 120:
            display_text += "..."
        
        match_item.setText(0, display_text)
        match_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
        match_item.setData(0, Qt.ItemDataRole.UserRole + 1, line_num)
        match_item.setData(0, Qt.ItemDataRole.UserRole + 2, "match")
        match_item.setData(0, Qt.ItemDataRole.UserRole + 3, highlighted_html)
        match_item.setForeground(0, QColor("#CCCCCC"))
        
        file_item.addChild(match_item)
        
        # Update file item count
        match_count = file_item.childCount()
        rel_path = os.path.relpath(file_path, self._project_path)
        file_item.setText(0, f"📄 {rel_path} ({match_count})")
        
        # Auto expand
        file_item.setExpanded(True)
    
    def _on_progress_update(self, progress: int):
        """Update progress bar"""
        self._progress_bar.setValue(progress)
    
    def _on_search_finished(self, total_matches: int, total_files: int):
        """Handle search completion"""
        self._progress_bar.hide()
        
        if total_matches == 0:
            self._status_label.setText("No results found")
        else:
            self._status_label.setText(f"{total_matches} results in {total_files} files")
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle single click - expand/collapse for files"""
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 2)
        if item_type == "file":
            item.setExpanded(not item.isExpanded())
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double click on result item - open file"""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        line_num = item.data(0, Qt.ItemDataRole.UserRole + 1)
        
        if file_path:
            self.file_requested.emit(file_path, line_num or 1)
    
    def _show_context_menu(self, position):
        """Show context menu for results"""
        item = self._results_tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Open file action
        open_action = menu.addAction("Open File")
        open_action.triggered.connect(lambda: self._open_file(item))
        
        menu.addSeparator()
        
        # Copy path action
        copy_path_action = menu.addAction("Copy Path")
        copy_path_action.triggered.connect(lambda: self._copy_path(file_path))
        
        # Copy relative path action
        copy_rel_path_action = menu.addAction("Copy Relative Path")
        copy_rel_path_action.triggered.connect(lambda: self._copy_relative_path(file_path))
        
        menu.addSeparator()
        
        # Dismiss result
        dismiss_action = menu.addAction("Dismiss")
        dismiss_action.triggered.connect(lambda: self._dismiss_result(item))
        
        menu.exec(self._results_tree.mapToGlobal(position))
    
    def _open_file(self, item: QTreeWidgetItem):
        """Open file from context menu"""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        line_num = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if file_path:
            self.file_requested.emit(file_path, line_num or 1)
    
    def _copy_path(self, file_path: str):
        """Copy absolute path to clipboard"""
        if file_path:
            QApplication.clipboard().setText(file_path)
    
    def _copy_relative_path(self, file_path: str):
        """Copy relative path to clipboard"""
        if file_path and self._project_path:
            rel_path = os.path.relpath(file_path, self._project_path)
            QApplication.clipboard().setText(rel_path)
    
    def _dismiss_result(self, item: QTreeWidgetItem):
        """Remove item from results"""
        parent = item.parent()
        if parent:
            parent.removeChild(item)
            if parent.childCount() == 0:
                index = self._results_tree.indexOfTopLevelItem(parent)
                self._results_tree.takeTopLevelItem(index)
        else:
            index = self._results_tree.indexOfTopLevelItem(item)
            self._results_tree.takeTopLevelItem(index)
    
    def _collapse_all(self):
        """Collapse all results"""
        self._results_tree.collapseAll()
    
    def _expand_all(self):
        """Expand all results"""
        self._results_tree.expandAll()
    
    def _clear_results(self):
        """Clear all search results"""
        self._results_tree.clear()
        self._results.clear()
        self._file_items.clear()
        self._status_label.setText("")
        self.search_term_changed.emit("", False, False, False)
    
    def _replace_next(self):
        """Replace next occurrence"""
        # TODO: Implement replace next
        pass
    
    def _replace_all(self):
        """Replace all occurrences"""
        # TODO: Implement replace all
        pass
    
    def focus_search(self):
        """Focus the search input"""
        self._search_input.setFocus()
        self._search_input.selectAll()
    
    def _create_highlighted_html(self, line_num: int, line_text: str, search_text: str) -> str:
        """Create HTML string with highlighted search matches"""
        import html
        
        # Truncate if needed
        max_len = 120
        truncated = len(line_text) > max_len
        display_text = line_text[:max_len] if truncated else line_text
        
        # Escape HTML entities
        escaped_text = html.escape(display_text)
        escaped_search = html.escape(search_text)
        
        # Build highlighted HTML
        case_sensitive = self._case_btn.isChecked()
        use_regex = self._regex_btn.isChecked()
        whole_word = self._word_btn.isChecked()
        
        if use_regex:
            try:
                import re
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = search_text
                if whole_word:
                    pattern = rf'\b{pattern}\b'
                
                def highlight_match(m):
                    return f'<span style="background-color:#613214; color:#FFCC00;">{html.escape(m.group())}</span>'
                
                highlighted = re.sub(pattern, highlight_match, display_text, flags=flags)
                # Re-escape any unescaped parts
                # This is tricky with regex, so we use a simpler approach
                escaped_text = highlighted
            except:
                # Fallback to plain text on regex error
                pass
        else:
            # Simple string replacement with highlighting
            if case_sensitive:
                parts = escaped_text.split(escaped_search)
                highlight_span = f'<span style="background-color:#613214; color:#FFCC00;">{escaped_search}</span>'
                escaped_text = highlight_span.join(parts)
            else:
                # Case insensitive highlighting
                import re
                pattern = re.escape(search_text)
                if whole_word:
                    pattern = rf'\b{pattern}\b'
                
                def highlight_match(m):
                    return f'<span style="background-color:#613214; color:#FFCC00;">{html.escape(m.group())}</span>'
                
                escaped_text = re.sub(pattern, highlight_match, display_text, flags=re.IGNORECASE)
        
        suffix = "..." if truncated else ""
        return f'<span style="color:#858585;">  {line_num}: </span><span style="color:#CCCCCC;">{escaped_text}{suffix}</span>'
