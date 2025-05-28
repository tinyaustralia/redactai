print("DEBUG: Script starting...") # DEBUG PRINT

import webview
import os
import sys
import re
import shutil
import atexit
import pypandoc

print("DEBUG: Basic imports successful.") # DEBUG PRINT

# Import backend logic
try:
    from redax_logic import process_document_for_redaction, cleanup_temp_dir
    print("DEBUG: Successfully imported from redax_logic.") # DEBUG PRINT
except ImportError as e:
    print(f"DEBUG: ERROR importing from redax_logic: {e}") # DEBUG PRINT
    sys.exit(1) # Exit if core logic can't be imported

APP_NAME = "Redax"
print(f"DEBUG: APP_NAME set to: {APP_NAME}") # DEBUG PRINT

# --- PANDOC PATH CONFIGURATION for macOS ARM (and adaptable for other OS) ---
def configure_pandoc_path():
    print("DEBUG: Entered configure_pandoc_path()") # DEBUG PRINT
    pandoc_executable_name = 'pandoc'
    bundled_pandoc_dir_rel_path = os.path.join('pandoc_native', 'macos_arm')

    if sys.platform == "win32":
        pandoc_executable_name = 'pandoc.exe'
        bundled_pandoc_dir_rel_path = os.path.join('pandoc_native', 'windows')
    elif sys.platform == "linux":
        bundled_pandoc_dir_rel_path = os.path.join('pandoc_native', 'linux')

    if getattr(sys, 'frozen', False):
        print("DEBUG: Running in bundled mode (sys.frozen is True)") # DEBUG PRINT
        if sys.platform == "darwin" and hasattr(sys, '_MEIPASS'):
            bundle_dir = sys._MEIPASS
        else:
            bundle_dir = os.path.dirname(sys.executable)

        pandoc_exec_full_path = os.path.join(bundle_dir, bundled_pandoc_dir_rel_path, pandoc_executable_name)

        print(f"DEBUG: Attempting to use bundled Pandoc. Platform: {sys.platform}") # DEBUG PRINT
        print(f"DEBUG: Bundle directory: {bundle_dir}") # DEBUG PRINT
        print(f"DEBUG: Expected bundled Pandoc path: {pandoc_exec_full_path}") # DEBUG PRINT

        if os.path.exists(pandoc_exec_full_path):
            print(f"DEBUG: Found bundled Pandoc at: {pandoc_exec_full_path}") # DEBUG PRINT
            os.environ['PYPANDOC_PANDOC'] = pandoc_exec_full_path
            if sys.platform != "win32" and not os.access(pandoc_exec_full_path, os.X_OK):
                print(f"DEBUG: WARNING: Bundled Pandoc at {pandoc_exec_full_path} is not executable. Attempting to chmod.") # DEBUG PRINT
                try:
                    os.chmod(pandoc_exec_full_path, 0o755)
                except Exception as e_chmod:
                    print(f"DEBUG: ERROR: Failed to chmod bundled Pandoc: {e_chmod}") # DEBUG PRINT
        else:
            print(f"DEBUG: WARNING: Bundled Pandoc executable not found at: {pandoc_exec_full_path}") # DEBUG PRINT
    else:
        print("DEBUG: Running in development mode (sys.frozen is False). pypandoc will try to find Pandoc in system PATH.") # DEBUG PRINT

    try:
        print("DEBUG: Calling pypandoc.ensure_pandoc_installed()") # DEBUG PRINT
        pypandoc.ensure_pandoc_installed()
        print(f"DEBUG: pypandoc.ensure_pandoc_installed() successful.") # DEBUG PRINT
        pandoc_exe_location = shutil.which(pypandoc.get_pandoc_path())
        print(f"DEBUG: pypandoc effectively found Pandoc at: {pandoc_exe_location if pandoc_exe_location else 'Not resolved by shutil.which (PYPANDOC_PANDOC might be set)'}") # DEBUG PRINT
        print("DEBUG: Exiting configure_pandoc_path() successfully.") # DEBUG PRINT
        return True
    except OSError as e_ose:
        print(f"DEBUG: ERROR: pypandoc could not find or use Pandoc. Error: {e_ose}") # DEBUG PRINT
        print("DEBUG: Exiting configure_pandoc_path() with error.") # DEBUG PRINT
        return False

print("DEBUG: About to call configure_pandoc_path()") # DEBUG PRINT
PANDOC_CONFIGURED_SUCCESSFULLY = configure_pandoc_path()
print(f"DEBUG: PANDOC_CONFIGURED_SUCCESSFULLY = {PANDOC_CONFIGURED_SUCCESSFULLY}") # DEBUG PRINT

REDACTION_PATTERNS_PYTHON = {
    "redact_credit_cards": r"\b(?:(?:\d[ -]*?){13,16}|(?:\d{4}[ ]){3}\d{4}|\d{13,16})\b",
    "redact_email_address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b",
    "redact_ips": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
    "redact_au_tfn": r"\b\d{3}\s?\d{3}\s?\d{3}\b",
    "redact_au_medicare": r"\b[2-6]\d{3}\s?\d{5}\s?\d\b",
    "redact_dob": r"\b(?:(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})|(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}))\b",
    "redact_au_abn": r"\b\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b",
    "redact_au_tel": r"\b(?:(?:\+?61\s?)?\\(?0?[23478]\\\\)?\s?\d{4}\s?\d{4}|1[389]\s?\d{2}\s?\d{2}\s?\d{2}|1300\s?\d{3}\s?\d{3})\b",
    "redact_au_bsb": r"\b(?:BSB\s*[:\\\\-]?\s*)?(?:\\\\d{3}[-\\\\s]?\\\\d{3}|\\\\d{6})\b",
    "redact_au_account_number": r"\b(?:Acct\s*[:\\\\-]?\s*|Account\s*No\s*[:\\\\-]?\s*)?\\\\d{5,9}\b",
    "redact_au_mobile": r"\b(?:04|\\\\+?61\s*4|0011\s*61\s*4)(?:\\\\d{2}\s?\\\\d{3}\s?\\\\d{3}|\\\\d{8})\b",
    "redact_credential_lines": "KEYWORD_LINE_REDACTION_PLACEHOLDER" # Special case, handled by a boolean flag in logic
}
print("DEBUG: REDACTION_PATTERNS_PYTHON defined.") # DEBUG PRINT

class Api:
    print("DEBUG: Api class definition starting.") # DEBUG PRINT

    def _generate_label_from_key(self, key):
        # "redact_credit_cards" -> "Redact Credit Cards"
        # "redact_credential_lines" -> "Redact Credential Lines"
        parts = key.split('_')
        label_parts = []
        if parts[0].lower() == "redact":
            label_parts.append("Redact")
            remaining_parts = parts[1:]
        else: # If "redact_" prefix is missing, prepend "Redact"
            label_parts.append("Redact")
            remaining_parts = parts
        
        for part in remaining_parts:
            if part.upper() in ["AU", "IP", "IPS", "TFN", "ABN", "BSB", "DOB"]: # Preserve common acronyms
                label_parts.append(part.upper())
            else:
                label_parts.append(part.capitalize())
        
        return " ".join(label_parts)


    def get_available_redaction_patterns(self):
        print("DEBUG: Api.get_available_redaction_patterns called") # DEBUG PRINT
        patterns_for_js = []
        for key in REDACTION_PATTERNS_PYTHON.keys():
            patterns_for_js.append({
                "key": key,
                "label": self._generate_label_from_key(key)
            })
        # Ensure "Redact Credential Lines" is distinct if logic changes later
        # For now, _generate_label_from_key handles it.
        print(f"DEBUG: Returning patterns for JS: {patterns_for_js}") # DEBUG PRINT
        return patterns_for_js

    def select_files_dialog(self):
        print("DEBUG: Api.select_files_dialog called") # DEBUG PRINT
        file_types = ('All supported types (*.docx;*.xlsx;*.pptx;*.rtf;*.md;*.txt)',
                      'Word documents (*.docx)', 'Markdown files (*.md)', 'Text files (*.txt)',
                      'Rich Text Format (*.rtf)','Excel workbooks (*.xlsx)',
                      'PowerPoint presentations (*.pptx)', 'All files (*.*)')
        if webview.windows:
            print("DEBUG: webview.windows exists, calling create_file_dialog") # DEBUG PRINT
            result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=file_types)
            print(f"DEBUG: File dialog result: {result}") # DEBUG PRINT
            return list(result) if result else []
        print("DEBUG: webview.windows does not exist.") # DEBUG PRINT
        return []

    def process_files_batch(self, params):
        print(f"DEBUG: Api.process_files_batch called with params: {params}") # DEBUG PRINT
        if not PANDOC_CONFIGURED_SUCCESSFULLY and not shutil.which("pandoc"):
            print("DEBUG: Pandoc not configured in process_files_batch") # DEBUG PRINT
            return [{"error": "Pandoc is not configured. Cannot process files."}]

        filepaths = params.get('filepaths', [])
        # Expected: {'selected_patterns': ["key1", "key2"], 'custom_keywords': ["keyword1"]}
        redaction_options_js = params.get('redaction_options', {}) 
        output_format = params.get('output_format', 'md')

        selected_pattern_keys = redaction_options_js.get('selected_patterns', [])
        custom_keywords = redaction_options_js.get('custom_keywords', [])
        
        # Determine if credential line redaction is enabled based on its presence in selected_pattern_keys
        redact_credential_lines_enabled = "redact_credential_lines" in selected_pattern_keys
        
        print(f"DEBUG: Selected pattern keys from JS: {selected_pattern_keys}") # DEBUG PRINT
        print(f"DEBUG: Custom keywords from JS: {custom_keywords}") # DEBUG PRINT
        print(f"DEBUG: Redact credential lines enabled: {redact_credential_lines_enabled}") # DEBUG PRINT

        active_patterns_compiled = []
        for key in selected_pattern_keys:
            if key == "redact_credential_lines":
                # This specific pattern is handled by the `redact_credential_lines_enabled` boolean flag,
                # which is passed to `process_document_for_redaction`. No regex compilation needed here.
                print(f"DEBUG: Skipping regex compilation for '{key}', handled by flag.") # DEBUG PRINT
                continue 
            
            if key in REDACTION_PATTERNS_PYTHON:
                pattern_str = REDACTION_PATTERNS_PYTHON[key]
                # This check is a safeguard in case a pattern other than "redact_credential_lines"
                # is mistakenly assigned the placeholder value.
                if pattern_str == "KEYWORD_LINE_REDACTION_PLACEHOLDER":
                    print(f"DEBUG: Warning: Pattern value for '{key}' is the placeholder but key is not 'redact_credential_lines'. Skipping compilation.") # DEBUG PRINT
                    continue
                try:
                    active_patterns_compiled.append(re.compile(pattern_str))
                    print(f"DEBUG: Compiled regex for pattern key: {key}") # DEBUG PRINT
                except re.error as e_regex:
                    print(f"DEBUG: Warning: Invalid regex for {key}: {pattern_str}. Error: {e_regex}")
            else:
                print(f"DEBUG: Warning: Unknown pattern key selected from JS: {key}")


        results_for_js = []
        for path in filepaths:
            if path:
                result = process_document_for_redaction(
                    path,
                    active_patterns_compiled, # Compiled regexes (excluding credential_lines pattern itself)
                    custom_keywords,
                    output_format,
                    redact_credential_lines_enabled=redact_credential_lines_enabled # Boolean flag for credential line redaction
                )
                if 'original_name' not in result and 'error' in result: # Add original_name for error reporting if missing
                    result['original_name'] = os.path.basename(path)
                results_for_js.append(result)
        print(f"DEBUG: Api.process_files_batch results: {results_for_js}") # DEBUG PRINT
        return results_for_js

    def save_processed_file(self, temp_file_path, original_name, output_format):
        print(f"DEBUG: Api.save_processed_file called with: {temp_file_path}, {original_name}, {output_format}") # DEBUG PRINT
        if not temp_file_path or not os.path.exists(temp_file_path):
            print(f"DEBUG: Error: Temporary file for download '{temp_file_path}' not found.")
            return {"error": "Processed file not found on server."}

        suggested_filename = f"{os.path.splitext(original_name)[0]}_redacted.{output_format}"

        if webview.windows:
            try:
                print(f"DEBUG: Calling create_file_dialog for SAVE_DIALOG with suggested_filename: {suggested_filename}") # DEBUG PRINT
                save_path_tuple = webview.windows[0].create_file_dialog(webview.SAVE_DIALOG, directory=os.path.expanduser('~'), save_filename=suggested_filename)
                save_path = save_path_tuple[0] if isinstance(save_path_tuple, tuple) and save_path_tuple else save_path_tuple
                print(f"DEBUG: Save dialog result: {save_path}") # DEBUG PRINT

                if save_path:
                    shutil.copy(temp_file_path, save_path)
                    print(f"DEBUG: File saved to: {save_path}")
                    return {"success": True, "path": save_path}
                else:
                    print("DEBUG: Save dialog cancelled by user.")
                    return {"success": False, "message": "Save cancelled."}
            except Exception as e:
                print(f"DEBUG: Error saving file via dialog: {e}")
                return {"error": str(e)}
        print("DEBUG: webview.windows does not exist in save_processed_file.") # DEBUG PRINT
        return {"error": "No active window to show save dialog."}
    print("DEBUG: Api class definition finished.") # DEBUG PRINT


def main():
    print("DEBUG: main() function called.") # DEBUG PRINT
    if not PANDOC_CONFIGURED_SUCCESSFULLY and not shutil.which("pandoc"): # Check again based on PATH if initial config failed
        print("DEBUG: CRITICAL: Pandoc is not available in main(). Document conversion will fail.")

    print("DEBUG: Creating Api instance.") # DEBUG PRINT
    api = Api()
    gui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gui')
    html_file = os.path.join(gui_dir, "index.html")
    print(f"DEBUG: HTML file path: {html_file}")

    if not os.path.exists(html_file):
        print(f"DEBUG: ERROR: HTML file not found at {html_file}. Exiting.") # DEBUG PRINT
        return # Exit if HTML file is missing

    print("DEBUG: Creating webview window.") # DEBUG PRINT
    try:
        window = webview.create_window(
            APP_NAME,
            f'file://{html_file}',
            js_api=api,
            width=1000,
            height=700,
            resizable=False
        )
        print("DEBUG: webview window created. Calling webview.start().") # DEBUG PRINT
        webview.start(debug=True)
        print("DEBUG: webview.start() finished (window closed).") # DEBUG PRINT
    except Exception as e_webview:
        print(f"DEBUG: ERROR during webview create_window or start: {e_webview}") # DEBUG PRINT


if __name__ == '__main__':
    print("DEBUG: Script __main__ block starting.") # DEBUG PRINT
    atexit.register(cleanup_temp_dir)
    print("DEBUG: cleanup_temp_dir registered with atexit.") # DEBUG PRINT
    main()
    print("DEBUG: Script __main__ block finished.") # DEBUG PRINT