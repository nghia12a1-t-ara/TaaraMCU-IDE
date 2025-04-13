import os
import platform

class LanguageDetector:
    @staticmethod
    def detect_language(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".c":
            return "c"
        elif ext in [".cpp", ".cc", ".cxx"]:
            return "cpp"
        elif ext == ".py":
            return "python"
        else:
            return "unknown"


class CodeCompiler:
    def __init__(self, terminal):
        self.terminal = terminal
        self.last_command = ""
        self.output_binary = ""
        self.compile_flags = []
        self.custom_output_path = None

    def set_compile_flags(self, flags: list[str]):
        self.compile_flags = flags

    def set_output_path(self, output_path: str):
        self.custom_output_path = output_path

    def _get_output_name(self, file_path):
        if self.custom_output_path:
            return self.custom_output_path
        base_dir = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        ext = ".exe" if platform.system() == "Windows" else ""
        return os.path.join(base_dir, base_name + ext)

    def compile(self, file_path, on_finished=None):
        lang = LanguageDetector.detect_language(file_path)
        output_name = self._get_output_name(file_path)
        self.output_binary = output_name

        if lang == "c":
            args = [f"\"{file_path}\"", "-o", f"\"{output_name}\""] + self.compile_flags
            self.last_command = f"gcc {' '.join(args)}"
            self.terminal.execute_specific_command("gcc", args, on_finished)

        elif lang == "cpp":
            args = [f"\"{file_path}\"", "-o", f"\"{output_name}\""] + self.compile_flags
            self.last_command = f"g++ {' '.join(args)}"
            self.terminal.execute_specific_command("g++", args, on_finished)

        elif lang == "python":
            self.terminal.add_log("Debug", "No need to compile Python.")
            if on_finished:
                on_finished()

        else:
            self.terminal.add_log("Error", f"Unsupported language: {file_path}")

    def run(self, file_path, on_finished=None):
        lang = LanguageDetector.detect_language(file_path)
        if lang in ["c", "cpp"]:
            binary_path = self._get_output_name(file_path)
            self.last_command = f"\"{binary_path}\""
            self.terminal.execute_specific_command(binary_path, [], on_finished)

        elif lang == "python":
            self.last_command = f"python \"{file_path}\""
            self.terminal.execute_specific_command("python", [f"\"{file_path}\""], on_finished)

        else:
            self.terminal.add_log("Error", f"Unsupported language: {file_path}")

    def compile_and_run(self, file_path, on_finished=None):
        self.compile(file_path, on_finished=lambda _: self.run(file_path, on_finished))

    def clean(self, file_path):
        lang = LanguageDetector.detect_language(file_path)
        output = self._get_output_name(file_path)
        if lang in ["c", "cpp"]:
            if os.path.exists(output):
                try:
                    os.remove(output)
                    self.terminal.add_log("Info", f"Cleaned: {output}")
                except Exception as e:
                    self.terminal.add_log("Error", f"Failed to delete {output}: {e}")
            else:
                self.terminal.add_log("Debug", f"No binary to clean: {output}")
        else:
            self.terminal.add_log("Debug", "Nothing to clean for this language.")
