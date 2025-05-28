print("DEBUG: Script starting...")

import webview
import os
import sys
import re
import shutil
import atexit
import pypandoc
import platform
import requests
import zipfile
import tarfile # Kept for potential future macOS Intel archives if they are .tar.gz
import stat # For setting executable permissions
# import json # Removed as it's not currently used

try:
    from redax_logic import process_document_for_redaction, cleanup_temp_dir
    print("DEBUG: Successfully imported from redax_logic.")
except ImportError as e:
    print(f"DEBUG: ERROR importing from redax_logic: {e}")
    sys.exit(1)

APP_NAME = "Redax"
PANDOC_VERSION_TAG = "3.1.13" # Specify a recent, known good Pandoc version
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PANDOC_NATIVE_DIR = os.path.join(BASE_DIR, 'pandoc_native')
# Store initial Pandoc status message
initial_pandoc_status_message = ""

print(f"DEBUG: APP_NAME set to: {APP_NAME}")
print(f"DEBUG: BASE_DIR: {BASE_DIR}")
print(f"DEBUG: PANDOC_NATIVE_DIR: {PANDOC_NATIVE_DIR}")

def get_pandoc_arch_details_macos():
    """Determines Pandoc architecture details based on macOS machine type."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    print(f"DEBUG: System: {system}, Machine: {machine}")

    if system == "darwin": # macOS
        # Pandoc 3.x releases for macOS:
        # arm64: pandoc-{version}-arm64-macOS.zip (contains binary in bin/pandoc)
        # x86_64: pandoc-{version}-x86_64-macOS.zip (contains binary in bin/pandoc)
        if "arm" in machine or "aarch64" in machine:
            return "macos_arm", f"pandoc-{PANDOC_VERSION_TAG}-arm64-macOS.zip", "pandoc"
        else: # Intel macOS
            return "macos_intel", f"pandoc-{PANDOC_VERSION_TAG}-x86_64-macOS.zip", "pandoc"
    print(f"DEBUG: System {system} is not macOS, Pandoc download for bundled version will be skipped.")
    return None, None, None

def download_file_with_progress(url, dest_path):
    print(f"INFO: Downloading Pandoc from {url} to {dest_path}")
    # The GUI won't show this progress directly, but it's good for terminal logs
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded_size += len(chunk)
                progress = (downloaded_size / total_size) * 100 if total_size > 0 else 0
                # Simple terminal progress
                sys.stdout.write(f"\rDEBUG: Downloading... {progress:.1f}% completed")
                sys.stdout.flush()
        sys.stdout.write("\n") # New line after progress
        print(f"DEBUG: Download successful: {dest_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: ERROR downloading {url}: {e}")
        return False

def extract_archive_macos(archive_path, extract_to_dir, pandoc_exe_name_in_archive):
    print(f"DEBUG: Extracting {archive_path} to {extract_to_dir}")
    # For macOS .zip from Pandoc 3.x, pandoc is usually in pandoc-{version}/bin/pandoc or bin/pandoc
    pandoc_binary_paths_in_archive = [
        f"pandoc-{PANDOC_VERSION_TAG}/bin/{pandoc_exe_name_in_archive}", # Primary structure
        f"bin/{pandoc_exe_name_in_archive}", # If only bin/ is top-level in zip
        pandoc_exe_name_in_archive # If it's directly in the root (less likely for Pandoc releases)
    ]
    
    try:
        if archive_path.endswith(".zip"):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                found_pandoc_member = None
                for member_name in zip_ref.namelist():
                    for target_path in pandoc_binary_paths_in_archive:
                        if member_name.endswith(target_path): 
                            found_pandoc_member = member_name
                            break
                    if found_pandoc_member:
                        break
                
                if found_pandoc_member:
                    zip_ref.extract(found_pandoc_member, extract_to_dir)
                    extracted_file_path = os.path.join(extract_to_dir, found_pandoc_member)
                    final_pandoc_path = os.path.join(extract_to_dir, pandoc_exe_name_in_archive)
                    
                    if os.path.abspath(extracted_file_path) != os.path.abspath(final_pandoc_path):
                        os.makedirs(os.path.dirname(final_pandoc_path), exist_ok=True)
                        shutil.move(extracted_file_path, final_pandoc_path)
                    
                    if "/" in found_pandoc_member:
                        top_extracted_folder_name = found_pandoc_member.split('/')[0]
                        path_to_remove = os.path.join(extract_to_dir, top_extracted_folder_name)
                        # Ensure we are not trying to remove the extract_to_dir itself if pandoc was at root of a versioned folder
                        if os.path.isdir(path_to_remove) and os.path.abspath(path_to_remove) != os.path.abspath(extract_to_dir) and os.path.abspath(path_to_remove) != os.path.abspath(os.path.dirname(final_pandoc_path)) :
                            print(f"DEBUG: Cleaning up extracted folder: {path_to_remove}")
                            shutil.rmtree(path_to_remove, ignore_errors=True)
                            
                    print(f"DEBUG: Extracted Pandoc to: {final_pandoc_path}")
                    return final_pandoc_path
                else:
                    print(f"DEBUG: ERROR: Pandoc executable not found in ZIP archive {archive_path} using patterns: {pandoc_binary_paths_in_archive}")
                    return None
        else:
            print(f"DEBUG: ERROR: Unsupported archive format for macOS: {archive_path}")
            return None
    except Exception as e:
        print(f"DEBUG: ERROR extracting {archive_path}: {e}")
        return None

def ensure_pandoc_downloaded_macos():
    global initial_pandoc_status_message
    print("DEBUG: Entered ensure_pandoc_downloaded_macos()")
    os_subdir, pandoc_archive_name, pandoc_exe_name = get_pandoc_arch_details_macos()

    if not os_subdir:
        initial_pandoc_status_message = "Pandoc download skipped: Not a supported macOS system for this script."
        print(f"DEBUG: {initial_pandoc_status_message}")
        return None

    local_pandoc_dir = os.path.join(PANDOC_NATIVE_DIR, os_subdir)
    local_pandoc_exe_path = os.path.join(local_pandoc_dir, pandoc_exe_name)
    
    os.makedirs(local_pandoc_dir, exist_ok=True)
    print(f"DEBUG: Ensured local Pandoc directory: {local_pandoc_dir}")

    if os.path.exists(local_pandoc_exe_path):
        initial_pandoc_status_message = f"Using existing local Pandoc: {os_subdir}"
        print(f"DEBUG: {initial_pandoc_status_message} at {local_pandoc_exe_path}")
        return local_pandoc_exe_path

    initial_pandoc_status_message = f"Pandoc for {os_subdir} not found. Attempting download..."
    print(f"DEBUG: {initial_pandoc_status_message}")
    
    pandoc_download_url = f"https://github.com/jgm/pandoc/releases/download/{PANDOC_VERSION_TAG}/{pandoc_archive_name}"
    
    temp_dir_for_download = os.path.join(PANDOC_NATIVE_DIR, "temp_download")
    os.makedirs(temp_dir_for_download, exist_ok=True)
    downloaded_archive_path = os.path.join(temp_dir_for_download, pandoc_archive_name)

    if not download_file_with_progress(pandoc_download_url, downloaded_archive_path):
        initial_pandoc_status_message = "Pandoc download failed."
        shutil.rmtree(temp_dir_for_download, ignore_errors=True)
        return None

    initial_pandoc_status_message = "Pandoc downloaded. Extracting..."
    print(f"DEBUG: {initial_pandoc_status_message}")

    extracted_pandoc_path_in_temp = extract_archive_macos(downloaded_archive_path, temp_dir_for_download, pandoc_exe_name)

    final_status_path = None
    if extracted_pandoc_path_in_temp and os.path.exists(extracted_pandoc_path_in_temp):
        print(f"DEBUG: Moving {extracted_pandoc_path_in_temp} to {local_pandoc_exe_path}")
        try:
            os.makedirs(os.path.dirname(local_pandoc_exe_path), exist_ok=True)
            shutil.move(extracted_pandoc_path_in_temp, local_pandoc_exe_path)
            
            print(f"DEBUG: Setting executable permission for {local_pandoc_exe_path}")
            current_permissions = os.stat(local_pandoc_exe_path).st_mode
            os.chmod(local_pandoc_exe_path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            
            initial_pandoc_status_message = f"Pandoc for {os_subdir} installed successfully."
            print(f"DEBUG: {initial_pandoc_status_message}")
            final_status_path = local_pandoc_exe_path
        except Exception as e:
            initial_pandoc_status_message = f"Error installing Pandoc: {e}"
            print(f"DEBUG: {initial_pandoc_status_message}")
    else:
        initial_pandoc_status_message = "Failed to extract Pandoc from archive."
        print(f"DEBUG: {initial_pandoc_status_message}")
    
    shutil.rmtree(temp_dir_for_download, ignore_errors=True) 
    return final_status_path

def configure_pandoc_path():
    global initial_pandoc_status_message
    print("DEBUG: Entered configure_pandoc_path()")
    
    if platform.system().lower() == "darwin":
        downloaded_pandoc_path = ensure_pandoc_downloaded_macos()
        if downloaded_pandoc_path and os.path.exists(downloaded_pandoc_path):
            print(f"DEBUG: Using downloaded/local Pandoc for macOS at: {downloaded_pandoc_path}")
            os.environ['PYPANDOC_PANDOC'] = downloaded_pandoc_path
            try:
                pypandoc.ensure_pandoc_installed(delete_installer=False) 
                print(f"DEBUG: pypandoc confirmed usability of: {downloaded_pandoc_path}")
                # initial_pandoc_status_message is already set by ensure_pandoc_downloaded_macos
                return True
            except OSError as e_init:
                initial_pandoc_status_message = f"Local Pandoc unusable: {e_init}. Trying system PATH."
                print(f"DEBUG: {initial_pandoc_status_message}")
        else:
            # initial_pandoc_status_message would have been set by ensure_pandoc_downloaded_macos
            print(f"DEBUG: Local Pandoc setup failed. Current status: {initial_pandoc_status_message}. Trying system PATH.")
    else:
        initial_pandoc_status_message = f"Not macOS ({platform.system()}). Checking system PATH for Pandoc."
        print(f"DEBUG: {initial_pandoc_status_message}")

    print("DEBUG: Checking for Pandoc in system PATH as fallback.")
    try:
        if 'PYPANDOC_PANDOC' in os.environ:
            del os.environ['PYPANDOC_PANDOC'] 
        
        pypandoc.ensure_pandoc_installed(delete_installer=False)
        pandoc_exe_location = shutil.which(pypandoc.get_pandoc_path())
        if not pandoc_exe_location: 
             pandoc_exe_location = shutil.which('pandoc')
        
        if pandoc_exe_location:
            initial_pandoc_status_message = "Pandoc ready (system PATH)."
            print(f"DEBUG: pypandoc found Pandoc in system PATH at: {pandoc_exe_location}")
        else:
            initial_pandoc_status_message = "Pandoc found by pypandoc (system), path not resolved by shutil.which."
            print(f"DEBUG: {initial_pandoc_status_message}")

        print("DEBUG: Exiting configure_pandoc_path() successfully (using system Pandoc).")
        return True
    except OSError as e_ose:
        initial_pandoc_status_message = f"Pandoc not found or unusable on system PATH: {e_ose}"
        print(f"DEBUG: {initial_pandoc_status_message}")
        print("DEBUG: Exiting configure_pandoc_path() with error (Pandoc not found).")
        return False


print("DEBUG: About to call configure_pandoc_path()")
PANDOC_CONFIGURED_SUCCESSFULLY = configure_pandoc_path()
print(f"DEBUG: PANDOC_CONFIGURED_SUCCESSFULLY = {PANDOC_CONFIGURED_SUCCESSFULLY}")
print(f"DEBUG: Initial Pandoc Status for GUI: {initial_pandoc_status_message}")

REDACTION_PATTERNS_PYTHON = {
    "redact_credit_cards": r"\b(?:(?:\d[ -]*?){13,16}|(?:\d{4}[ ]){3}\d{4}|\d{13,16})\b",
    "redact_email_address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b",
    "redact_ips": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
    "redact_au_tfn": r"\b\d{3}\s?\d{3}\s?\d{3}\b",
    "redact_au_medicare": r"\b[2-6]\d{3}\s?\d{5}\s?\d\b",
    "redact_dob": r"\b(?:(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})|(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}))\b",
    "redact_au_abn": r"\b\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b",
    "redact_au_tel": r"\b(?:(?:\+?61\s?)?\\(?0?[23478]\\\\)?\s?\d{4}\s?\d{4}|1[389]\s?\d{2}\s?\d{2}\s?\d{2}|1300\s?\d{3}\s?\d{3})\b",
    "redact_au_bsb": r"\b(?:BSB\s*[:\\\\\\\\-]?\s*)?(?:\\\\\\\\d{3}[-\\\\\\\\s]?\\\\\\\\d{3}|\\\\\\\\d{6})\b",
    "redact_au_account_number": r"\b(?:Acct\s*[:\\\\\\\\-]?\s*|Account\s*No\s*[:\\\\\\\\-]?\s*)?\\\\\\\\d{5,9}\b",
    "redact_au_mobile": r"\b(?:04|\\\\\\\\+?61\s*4|0011\s*61\s*4)(?:\\\\\\\\d{2}\s?\\\\\\\\d{3}\s?\\\\\\\\d{3}|\\\\\\\\d{8})\b",
    "redact_credential_lines": "KEYWORD_LINE_REDACTION_PLACEHOLDER"
}
print("DEBUG: REDACTION_PATTERNS_PYTHON defined.")

class Api:
    print("DEBUG: Api class definition starting.")

    def get_initial_status(self):
        """Returns the initial Pandoc setup status message for the GUI."""
        print(f"DEBUG: Api.get_initial_status called, returning: {initial_pandoc_status_message}")
        return {"pandoc_status": initial_pandoc_status_message, "pandoc_ready": PANDOC_CONFIGURED_SUCCESSFULLY}

    def _generate_label_from_key(self, key):
        parts = key.split('_')
        label_parts = []
        if parts[0].lower() == "redact":
            label_parts.append("Redact")
            remaining_parts = parts[1:]
        else:
            label_parts.append("Redact")
            remaining_parts = parts
        
        for part in remaining_parts:
            if part.upper() in ["AU", "IP", "IPS", "TFN", "ABN", "BSB", "DOB"]:
                label_parts.append(part.upper())
            else:
                label_parts.append(part.capitalize())
        return " ".join(label_parts)

    def get_available_redaction_patterns(self):
        print("DEBUG: Api.get_available_redaction_patterns called")
        patterns_for_js = []
        for key in REDACTION_PATTERNS_PYTHON.keys():
            patterns_for_js.append({
                "key": key,
                "label": self._generate_label_from_key(key)
            })
        print(f"DEBUG: Returning patterns for JS: {patterns_for_js}")
        return patterns_for_js

    def select_files_dialog(self):
        print("DEBUG: Api.select_files_dialog called")
        file_types = ('All supported types (*.docx;*.xlsx;*.pptx;*.rtf;*.md;*.txt)',
                      'Word documents (*.docx)', 'Markdown files (*.md)', 'Text files (*.txt)',
                      'Rich Text Format (*.rtf)','Excel workbooks (*.xlsx)',
                      'PowerPoint presentations (*.pptx)', 'All files (*.*)')
        if webview.windows: 
            print("DEBUG: webview.windows exists, calling create_file_dialog")
            result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=file_types)
            print(f"DEBUG: File dialog result: {result}")
            return list(result) if result else []
        print("DEBUG: webview.windows does not exist.")
        return []

    def process_files_batch(self, params):
        print(f"DEBUG: Api.process_files_batch called with params: {params}")
        if not PANDOC_CONFIGURED_SUCCESSFULLY:
            error_message = f"Pandoc setup failed or incomplete ({initial_pandoc_status_message}). Cannot process files."
            print(f"DEBUG: {error_message}")
            return [{"error": error_message, "original_name": "Processing Error"}]

        filepaths = params.get('filepaths', [])
        redaction_options_js = params.get('redaction_options', {}) 
        output_format = params.get('output_format', 'md')

        selected_pattern_keys = redaction_options_js.get('selected_patterns', [])
        custom_keywords = redaction_options_js.get('custom_keywords', [])
        
        redact_credential_lines_enabled = "redact_credential_lines" in selected_pattern_keys
        
        print(f"DEBUG: Selected pattern keys from JS: {selected_pattern_keys}")
        print(f"DEBUG: Custom keywords from JS: {custom_keywords}")
        print(f"DEBUG: Redact credential lines enabled: {redact_credential_lines_enabled}")

        active_patterns_compiled = []
        for key in selected_pattern_keys:
            if key == "redact_credential_lines":
                continue 
            
            if key in REDACTION_PATTERNS_PYTHON:
                pattern_str = REDACTION_PATTERNS_PYTHON[key]
                if pattern_str == "KEYWORD_LINE_REDACTION_PLACEHOLDER":
                    print(f"DEBUG: Warning: Pattern value for '{key}' is placeholder. Skipping.")
                    continue
                try:
                    active_patterns_compiled.append(re.compile(pattern_str))
                    print(f"DEBUG: Compiled regex for pattern key: {key}")
                except re.error as e_regex:
                    print(f"DEBUG: Warning: Invalid regex for {key}: {pattern_str}. Error: {e_regex}")
            else:
                print(f"DEBUG: Warning: Unknown pattern key selected from JS: {key}")

        results_for_js = []
        for path in filepaths:
            if path:
                result = process_document_for_redaction(
                    path,
                    active_patterns_compiled,
                    custom_keywords,
                    output_format,
                    redact_credential_lines_enabled=redact_credential_lines_enabled
                )
                if 'original_name' not in result and 'error' in result:
                    result['original_name'] = os.path.basename(path)
                results_for_js.append(result)
        print(f"DEBUG: Api.process_files_batch results: {results_for_js}")
        return results_for_js

    def save_processed_file(self, temp_file_path, original_name, output_format):
        print(f"DEBUG: Api.save_processed_file called with: {temp_file_path}, {original_name}, {output_format}")
        if not temp_file_path or not os.path.exists(temp_file_path):
            print(f"DEBUG: Error: Temporary file for download '{temp_file_path}' not found.")
            return {"error": "Processed file not found on server."}

        suggested_filename = f"{os.path.splitext(original_name)[0]}_redacted.{output_format}"

        if webview.windows:
            try:
                print(f"DEBUG: Calling create_file_dialog for SAVE_DIALOG with suggested_filename: {suggested_filename}")
                save_path_tuple = webview.windows[0].create_file_dialog(webview.SAVE_DIALOG, directory=os.path.expanduser('~'), save_filename=suggested_filename)
                save_path = save_path_tuple[0] if isinstance(save_path_tuple, tuple) and save_path_tuple else save_path_tuple
                print(f"DEBUG: Save dialog result: {save_path}")

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
        print("DEBUG: webview.windows does not exist in save_processed_file.")
        return {"error": "No active window to show save dialog."}
    print("DEBUG: Api class definition finished.")


def main():
    print("DEBUG: main() function called.")
    if not PANDOC_CONFIGURED_SUCCESSFULLY:
        print(f"DEBUG: CRITICAL: Pandoc setup failed ({initial_pandoc_status_message}). GUI will reflect this.")

    print("DEBUG: Creating Api instance.")
    api = Api()
    gui_dir = os.path.join(BASE_DIR, 'gui')
    html_file = os.path.join(gui_dir, "index.html")
    print(f"DEBUG: HTML file path: {html_file}")

    if not os.path.exists(html_file):
        print(f"DEBUG: ERROR: HTML file not found at {html_file}. Exiting.")
        return

    print("DEBUG: Creating webview window.")
    try:
        window = webview.create_window(
            APP_NAME,
            f'file://{html_file}', 
            js_api=api,
            width=1000, 
            height=720, 
            resizable=True 
        )
        print("DEBUG: webview window created. Calling webview.start().")
        webview.start(debug=True) 
        print("DEBUG: webview.start() finished (window closed).")
    except Exception as e_webview:
        print(f"DEBUG: ERROR during webview create_window or start: {e_webview}")


if __name__ == '__main__':
    print("DEBUG: Script __main__ block starting.")
    atexit.register(cleanup_temp_dir) 
    print("DEBUG: cleanup_temp_dir registered with atexit.")
    main()
    print("DEBUG: Script __main__ block finished.")
