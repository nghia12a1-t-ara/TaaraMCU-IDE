from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

# Add this class for the Find Dialog
class FindDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Find")
        self.setFixedWidth(450)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_find_tab(), "Find")
        self.tab_widget.addTab(self.create_replace_tab(), "Replace")  # Added Replace tab
        self.tab_widget.addTab(self.create_find_in_files_tab(), "Find in Files")

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def create_find_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Find what
        find_layout = QHBoxLayout()
        find_label = QLabel("Find what:")
        self.find_input = QLineEdit()
        self.find_input.textChanged.connect(self.reset_search)
        find_layout.addWidget(find_label)
        find_layout.addWidget(self.find_input)

        # Buttons group
        buttons_layout = QHBoxLayout()

        # Left side buttons
        left_buttons = QVBoxLayout()
        self.find_next_button = QPushButton("Find Next")
        self.find_next_button.clicked.connect(self.find_next)
        self.count_button = QPushButton("Count")
        self.count_button.clicked.connect(self.count_occurrences)
        left_buttons.addWidget(self.find_next_button)
        left_buttons.addWidget(self.count_button)

        # Right side buttons
        right_buttons = QVBoxLayout()
        self.find_all_current_button = QPushButton("Find All in Current Document")
        self.find_all_current_button.clicked.connect(self.find_all_current)
        self.find_all_opened_button = QPushButton("Find All in All Opened Documents")
        self.find_all_opened_button.clicked.connect(self.find_all_opened)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        right_buttons.addWidget(self.find_all_current_button)
        right_buttons.addWidget(self.find_all_opened_button)
        right_buttons.addWidget(self.close_button)

        buttons_layout.addLayout(left_buttons)
        buttons_layout.addLayout(right_buttons)

        # Search options
        options_group = QGroupBox("Search Mode")
        options_layout = QVBoxLayout()

        # Search mode options
        self.normal_mode = QRadioButton("Normal")
        self.normal_mode.setChecked(True)
        self.extended_mode = QRadioButton("Extended (\\n, \\r, \\t, \\0, ...)")
        self.regex_mode = QRadioButton("Regular expression")

        options_layout.addWidget(self.normal_mode)
        options_layout.addWidget(self.extended_mode)
        options_layout.addWidget(self.regex_mode)
        options_group.setLayout(options_layout)

        # Checkboxes
        checks_layout = QVBoxLayout()
        self.backward_check = QCheckBox("Backward direction")
        self.match_case = QCheckBox("Match case")
        self.whole_word = QCheckBox("Match whole word only")
        self.wrap_around = QCheckBox("Wrap around")
        self.wrap_around.setChecked(True)

        checks_layout.addWidget(self.backward_check)
        checks_layout.addWidget(self.match_case)
        checks_layout.addWidget(self.whole_word)
        checks_layout.addWidget(self.wrap_around)

        # Transparency options
        trans_group = QGroupBox("Transparency")
        trans_layout = QVBoxLayout()
        self.transparency_check = QCheckBox("Enable")
        self.on_losing_focus = QRadioButton("On losing focus")
        self.on_losing_focus.setChecked(True)
        self.always = QRadioButton("Always")

        trans_layout.addWidget(self.transparency_check)
        trans_layout.addWidget(self.on_losing_focus)
        trans_layout.addWidget(self.always)
        trans_group.setLayout(trans_layout)

        # Add all to main layout
        layout.addLayout(find_layout)
        layout.addLayout(buttons_layout)
        layout.addWidget(options_group)
        layout.addLayout(checks_layout)
        layout.addWidget(trans_group)
        layout.addStretch()

        tab.setLayout(layout)
        return tab

    def create_replace_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Find and Replace inputs
        find_layout = QHBoxLayout()
        find_label = QLabel("Find what:")
        self.replace_find_input = QLineEdit()
        find_layout.addWidget(find_label)
        find_layout.addWidget(self.replace_find_input)

        replace_layout = QHBoxLayout()
        replace_label = QLabel("Replace with:")
        self.replace_input = QLineEdit()
        replace_layout.addWidget(replace_label)
        replace_layout.addWidget(self.replace_input)

        # Buttons
        buttons_layout = QVBoxLayout()
        self.replace_find_next_btn = QPushButton("Find Next")
        self.replace_find_next_btn.clicked.connect(self.replace_find_next)
        self.replace_button = QPushButton("Replace")
        self.replace_button.clicked.connect(self.replace)
        self.replace_all_button = QPushButton("Replace All")
        self.replace_all_button.clicked.connect(self.replace_all)

        buttons_layout.addWidget(self.replace_find_next_btn)
        buttons_layout.addWidget(self.replace_button)
        buttons_layout.addWidget(self.replace_all_button)

        # Add all to main layout
        layout.addLayout(find_layout)
        layout.addLayout(replace_layout)
        layout.addLayout(buttons_layout)
        layout.addStretch()

        tab.setLayout(layout)
        return tab

    def create_find_in_files_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # Find input
        find_layout = QHBoxLayout()
        find_label = QLabel("Find what:")
        self.find_files_input = QLineEdit()
        find_layout.addWidget(find_label)
        find_layout.addWidget(self.find_files_input)

        # Directory input
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Directory:")
        self.dir_input = QLineEdit()
        self.browse_button = QPushButton("...")
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.browse_button)

        # Filters
        filters_layout = QHBoxLayout()
        filters_label = QLabel("Filters:")
        self.filters_input = QLineEdit()
        self.filters_input.setPlaceholderText("*.txt, *.py")
        filters_layout.addWidget(filters_label)
        filters_layout.addWidget(self.filters_input)

        # Find button
        self.find_files_button = QPushButton("Find All")

        # Add all to main layout
        layout.addLayout(find_layout)
        layout.addLayout(dir_layout)
        layout.addLayout(filters_layout)
        layout.addWidget(self.find_files_button)
        layout.addStretch()

        tab.setLayout(layout)
        return tab

    def reset_search(self):
        editor = self.parent.get_current_editor()
        if editor:
            editor.clearIndicatorRange(0, 0, editor.lines(),
                                    len(editor.text()), 0)

    def find_next(self):
        """Find next occurrence of the search text"""
        editor = self.parent.get_current_editor()
        if not editor:
            return

        text = self.find_input.text()
        if not text:
            return

        # Get current position
        line, index = editor.getCursorPosition()

        # If there's a selection, start from the end of the selection
        if editor.hasSelectedText():
            sel_line, sel_index, _, _ = editor.getSelection()
            if (sel_line, sel_index) == (line, index):
                line, index = editor.getSelection()[2:]

        try:
            # Set search flags
            search_flags = 0
            if self.regex_mode.isChecked():
                search_flags |= QsciScintilla.SCFIND_REGEXP
                search_flags |= QsciScintilla.SCFIND_POSIX  # More standard regex behavior
            if self.match_case.isChecked():
                search_flags |= QsciScintilla.SCFIND_MATCHCASE
            if self.whole_word.isChecked():
                search_flags |= QsciScintilla.SCFIND_WHOLEWORD

            # Set the search flags
            editor.SendScintilla(QsciScintilla.SCI_SETSEARCHFLAGS, search_flags)

            found = editor.findFirst(
                text,
                self.regex_mode.isChecked(),      # Regular expression
                self.match_case.isChecked(),      # Case sensitive
                self.whole_word.isChecked(),      # Whole word
                self.wrap_around.isChecked(),     # Wrap around
                not self.backward_check.isChecked(),  # Forward/backward
                line,
                index,
                True                              # Move cursor and show
            )

            if not found:
                QMessageBox.information(self, "Find", "No more occurrences found.")

        except Exception as e:
            QMessageBox.warning(self, "Regex Error", f"Invalid regular expression: {str(e)}")

    def count_occurrences(self):
        """Count all occurrences of the search text"""
        editor = self.parent.get_current_editor()
        if not editor:
            return

        text = self.find_input.text()
        if not text:
            QMessageBox.information(self, "Count", "Please enter text to search for.")
            return

        # Save current position
        original_line, original_index = editor.getCursorPosition()

        try:
            # Get the full text content
            full_text = editor.text()
            count = 0

            if self.regex_mode.isChecked():
                try:
                    # Set up regex flags
                    flags = re.MULTILINE  # Always use multiline mode
                    if not self.match_case.isChecked():
                        flags |= re.IGNORECASE

                    # Compile and find all matches
                    pattern = re.compile(text, flags)
                    matches = pattern.finditer(full_text)
                    count = sum(1 for _ in matches)

                except re.error as e:
                    QMessageBox.warning(self, "Regex Error", f"Invalid regular expression: {str(e)}")
                    return

            else:
                # Normal search
                if self.whole_word.isChecked():
                    import re
                    pattern = r'\b' + re.escape(text) + r'\b'
                    flags = re.MULTILINE
                    if not self.match_case.isChecked():
                        flags |= re.IGNORECASE
                    count = len(re.findall(pattern, full_text, flags))
                else:
                    if self.match_case.isChecked():
                        count = full_text.count(text)
                    else:
                        count = full_text.lower().count(text.lower())

            # Show result
            QMessageBox.information(self, "Count", f"Found {count} occurrence(s)")

        finally:
            # Restore original position
            editor.setCursorPosition(original_line, original_index)

    def find_all_current(self):
        """Find all occurrences in current document and highlight them"""
        editor = self.parent.get_current_editor()
        if not editor:
            return

        text = self.find_input.text()
        if not text:
            QMessageBox.information(self, "Find All", "Please enter text to search for.")
            return

        # Clear previous highlights
        editor.clearIndicatorRange(0, 0, editor.lines(), len(editor.text()), 0)

        try:
            # Get the full text content
            full_text = editor.text()
            matches = []

            if self.regex_mode.isChecked():
                try:
                    import re
                    # Set up regex flags
                    flags = re.MULTILINE
                    if not self.match_case.isChecked():
                        flags |= re.IGNORECASE

                    pattern = re.compile(text, flags)
                    matches = list(pattern.finditer(full_text))

                except re.error as e:
                    QMessageBox.warning(self, "Regex Error", f"Invalid regular expression: {str(e)}")
                    return
            else:
                # Normal search
                search_text = text
                content = full_text

                if not self.match_case.isChecked():
                    search_text = text.lower()
                    content = full_text.lower()

                start = 0
                while True:
                    index = content.find(search_text, start)
                    if index == -1:
                        break

                    # Check for whole word match if needed
                    if self.whole_word.isChecked():
                        # Check word boundaries
                        before = index == 0 or not content[index-1].isalnum()
                        after = (index + len(search_text) >= len(content) or
                                not content[index + len(search_text)].isalnum())
                        if before and after:
                            matches.append((index, index + len(search_text)))
                    else:
                        matches.append((index, index + len(search_text)))

                    start = index + 1

            # Highlight all matches
            for match in matches:
                if isinstance(match, re.Match):
                    start, end = match.span()
                else:
                    start, end = match

                # Convert string index to line and column
                line_from = full_text.count('\n', 0, start)
                line_to = full_text.count('\n', 0, end)

                # Find column positions
                last_nl = full_text.rfind('\n', 0, start)
                index_from = start - (last_nl + 1 if last_nl != -1 else 0)

                last_nl = full_text.rfind('\n', 0, end)
                index_to = end - (last_nl + 1 if last_nl != -1 else 0)

                # Highlight the match
                editor.fillIndicatorRange(line_from, index_from, line_to, index_to, 0)

            # Show results
            count = len(matches)
            if count > 0:
                QMessageBox.information(self, "Find All", f"Found {count} occurrence(s)")
            else:
                QMessageBox.information(self, "Find All", "No matches found")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"An error occurred: {str(e)}")

    def find_all_opened(self):
        """Find all occurrences in all opened documents"""
        if not self.parent.tabWidget.count():
            return

        text = self.find_input.text()
        if not text:
            return

        total_count = 0
        results = []

        # Search in all tabs
        for i in range(self.parent.tabWidget.count()):
            editor = self.parent.tabWidget.widget(i)
            file_name = self.parent.tabWidget.tabText(i)

            # Save current position
            original_line, original_index = editor.getCursorPosition()

            try:
                # Start from the beginning
                editor.setCursorPosition(0, 0)

                # Set search flags
                search_flags = 0
                if self.regex_mode.isChecked():
                    search_flags |= QsciScintilla.SCFIND_REGEXP
                    search_flags |= QsciScintilla.SCFIND_POSIX
                if self.match_case.isChecked():
                    search_flags |= QsciScintilla.SCFIND_MATCHCASE
                if self.whole_word.isChecked():
                    search_flags |= QsciScintilla.SCFIND_WHOLEWORD

                editor.SendScintilla(QsciScintilla.SCI_SETSEARCHFLAGS, search_flags)

                # Find first occurrence
                found = editor.findFirst(
                    text,
                    self.regex_mode.isChecked(),
                    self.match_case.isChecked(),
                    self.whole_word.isChecked(),
                    True,  # wrap
                    True,  # forward
                    0, 0,  # from start
                    False  # don't move cursor
                )

                count = 0
                while found:
                    # Get the selection range
                    line_from, index_from, line_to, index_to = editor.getSelection()

                    # Highlight the found text
                    editor.fillIndicatorRange(line_from, index_from, line_to, index_to, 0)

                    count += 1
                    found = editor.findNext()

                if count > 0:
                    results.append(f"{file_name}: {count} occurrence(s)")
                    total_count += count

            finally:
                # Restore original position
                editor.setCursorPosition(original_line, original_index)

        # Show results
        if total_count > 0:
            result_text = "Found matches in:\n" + "\n".join(results)
            QMessageBox.information(self, "Find All", f"{result_text}\n\nTotal: {total_count} occurrence(s)")
        else:
            QMessageBox.information(self, "Find All", "No matches found in any open documents")

    def replace_find_next(self):
        """Find the next occurrence of the text to replace."""
        editor = self.parent.get_current_editor()
        if not editor or not self.replace_find_input.text():
            return

        text = self.replace_find_input.text()
        line, index = editor.getCursorPosition()

        # If there's a selection, start from the end of the selection
        if editor.hasSelectedText():
            sel_line, sel_index, _, _ = editor.getSelection()
            if (sel_line, sel_index) == (line, index):
                line, index = editor.getSelection()[2:]

        # Search based on the options from the Find tab
        found = editor.findFirst(
            text,
            self.regex_mode.isChecked(),
            self.match_case.isChecked(),
            self.whole_word.isChecked(),
            self.wrap_around.isChecked(),
            not self.backward_check.isChecked(),
            line,
            index,
            True
        )

        if not found:
            QMessageBox.information(self, "Replace", "No more occurrences found.")

    def replace(self):
        """Replace the current occurrence and find the next one."""
        editor = self.parent.get_current_editor()
        if not editor or not self.replace_find_input.text():
            return

        text = self.replace_find_input.text()
        replacement = self.replace_input.text()

        # If there's a matching selected text, replace it
        if editor.hasSelectedText():
            selected_text = editor.selectedText()
            if (self.match_case.isChecked() and selected_text == text) or \
               (not self.match_case.isChecked() and selected_text.lower() == text.lower()):
                editor.replace(replacement)

        # Find the next occurrence
        self.replace_find_next()

    def replace_all(self):
        """Replace all occurrences in the text."""
        editor = self.parent.get_current_editor()
        if not editor or not self.replace_find_input.text():
            return

        text = self.replace_find_input.text()
        replacement = self.replace_input.text()

        # Start from the beginning of the text
        editor.setCursorPosition(0, 0)
        count = 0

        # Find and replace all
        found = editor.findFirst(
            text,
            self.regex_mode.isChecked(),
            self.match_case.isChecked(),
            self.whole_word.isChecked(),
            False,  # No wrap to avoid looping
            True,   # Forward direction
            0, 0,   # Start from the beginning
            False   # Don't move cursor
        )

        while found:
            # Replace the found text
            editor.replace(replacement)
            count += 1
            found = editor.findNext()  # Find the next occurrence

        QMessageBox.information(self, "Replace All", f"Replaced {count} occurrence(s).")
