// This script will run after the window.pywebview.api is available

let selectedFilePaths = []; // To store paths from Python file dialog
let redactionChoicesInstance = null; // To store the Choices.js instance

window.addEventListener("pywebviewready", async function () {
  const selectFilesBtn = document.getElementById("selectFilesBtn");
  const fileListUI = document.getElementById("fileList");
  const processBtn = document.getElementById("processBtn");
  const statusBar = document.getElementById("statusBar");
  const customKeywordsInput = document.getElementById("customKeywords");
  const outputFormatSelect = document.getElementById("outputFormat");
  const processedFileListUI = document.getElementById("processedFileList");
  const outputSection = document.getElementById("outputSection");
  const resetAppBtn = document.getElementById("resetAppBtn");
  const redactionPatternsSelect = document.getElementById("redactionPatternsSelect");

  const initialFileListMessage =
    '<li class="text-slate-400 italic">Upload documents for processing redactions (Max 5).</li>';
  const initialStatusBarText = "Ready. Select files to begin.";
  const initialStatusBarClasses =
    "p-2.5 bg-slate-800 text-sm text-slate-300 text-center rounded-md border border-slate-700 min-h-[40px] flex items-center justify-center";

  fileListUI.innerHTML = initialFileListMessage;
  statusBar.textContent = initialStatusBarText;
  statusBar.className = initialStatusBarClasses;

  async function initializeRedactionDropdown() {
    try {
      const patterns = await window.pywebview.api.get_available_redaction_patterns();
      if (patterns && redactionPatternsSelect) {
        patterns.forEach(pattern => {
          const option = document.createElement('option');
          option.value = pattern.key;
          option.textContent = pattern.label;
          redactionPatternsSelect.appendChild(option);
        });
        redactionChoicesInstance = new Choices(redactionPatternsSelect, {
          removeItemButton: true,
          searchEnabled: true,
          searchPlaceholderValue: "Search options...",
          placeholder: true,
          placeholderValue: "Select redaction options...",
          shouldSort: false,
          itemSelectText: 'Press to select',
        });
        console.log("Redaction options dropdown initialized.");
      } else {
        console.error("Could not fetch patterns or redactionPatternsSelect element not found.");
        statusBar.textContent = "Error: Could not load redaction types.";
        statusBar.className = "p-2.5 bg-red-700 text-red-100 text-sm text-center rounded-md border border-red-600 min-h-[40px] flex items-center justify-center";
      }
    } catch (error) {
      console.error("Error initializing redaction dropdown:", error);
      statusBar.textContent = "Error loading redaction options.";
      statusBar.className = "p-2.5 bg-red-700 text-red-100 text-sm text-center rounded-md border border-red-600 min-h-[40px] flex items-center justify-center";
    }
  }

  await initializeRedactionDropdown();

  function resetApplicationState() {
    selectedFilePaths = [];
    fileListUI.innerHTML = initialFileListMessage;
    if (redactionChoicesInstance) {
      redactionChoicesInstance.removeActiveItems(); 
      redactionChoicesInstance.setChoiceByValue([]);
    }
    customKeywordsInput.value = "";
    outputFormatSelect.value = "md";
    statusBar.textContent = initialStatusBarText;
    statusBar.className = initialStatusBarClasses;
    outputSection.style.display = "none";
    processedFileListUI.innerHTML = "";
    processBtn.disabled = false;
    processBtn.classList.remove("opacity-50", "cursor-not-allowed");
    statusBar.classList.remove("animate-pulse");
    console.log("Application state reset.");
  }

  if (resetAppBtn) {
    resetAppBtn.addEventListener("click", () => {
      resetApplicationState();
    });
  } else {
    console.error("Reset button (resetAppBtn) not found.");
  }

  selectFilesBtn.addEventListener("click", async () => {
    try {
      let result = await window.pywebview.api.select_files_dialog();
      if (result && result.length > 0) {
        if (result.length > 5) { 
          statusBar.textContent = "Too many files selected. Please select a maximum of 5 files.";
          statusBar.className = "p-2.5 bg-amber-700 text-amber-100 text-sm text-center rounded-md border border-amber-600 min-h-[40px] flex items-center justify-center";
          return; 
        }
        
        selectedFilePaths = result;
        fileListUI.innerHTML = "";
        selectedFilePaths.forEach((path) => {
          const li = document.createElement("li");
          li.className = "py-1 px-2 bg-slate-700 text-slate-200 text-sm";
          li.textContent = path.split(/[\\/]/).pop(); 
          fileListUI.appendChild(li);
        });
        statusBar.textContent = `${selectedFilePaths.length} file(s) selected. Ready to process.`;
        statusBar.className =
          "p-2.5 bg-sky-700 text-sky-100 text-sm text-center rounded-md border border-sky-600 min-h-[40px] flex items-center justify-center";
      } else {
        if (selectedFilePaths.length === 0) { 
          fileListUI.innerHTML = initialFileListMessage;
          statusBar.textContent = initialStatusBarText;
          statusBar.className = initialStatusBarClasses;
        } else {
          statusBar.textContent = `${selectedFilePaths.length} file(s) previously selected. Selection cancelled.`;
          statusBar.className = "p-2.5 bg-sky-700 text-sky-100 text-sm text-center rounded-md border border-sky-600 min-h-[40px] flex items-center justify-center";
        }
      }
    } catch (e) {
      console.error("Error calling select_files_dialog:", e);
      statusBar.textContent = "Error selecting files. Please try again.";
      statusBar.className =
        "p-2.5 bg-red-700 text-red-100 text-sm text-center rounded-md border border-red-600 min-h-[40px] flex items-center justify-center";
    }
  });

  processBtn.addEventListener("click", async () => {
    if (selectedFilePaths.length === 0) {
      statusBar.textContent = "Please select files before processing.";
      statusBar.className =
        "p-2.5 bg-amber-700 text-amber-100 text-sm text-center rounded-md border border-amber-600 min-h-[40px] flex items-center justify-center";
      return;
    }
    // This check is a safeguard; primary check is in selectFilesBtn handler
    if (selectedFilePaths.length > 5) { 
        statusBar.textContent = "Cannot process more than 5 files. Please reduce your selection.";
        statusBar.className = "p-2.5 bg-amber-700 text-amber-100 text-sm text-center rounded-md border border-amber-600 min-h-[40px] flex items-center justify-center";
        return;
    }

    const selectedPatternKeys = redactionChoicesInstance ? redactionChoicesInstance.getValue(true) : [];
    if (selectedPatternKeys.length === 0 && !customKeywordsInput.value.trim()) {
        statusBar.textContent = "Please select at least one redaction option or provide custom keywords.";
        statusBar.className = "p-2.5 bg-amber-700 text-amber-100 text-sm text-center rounded-md border border-amber-600 min-h-[40px] flex items-center justify-center";
        return;
    }

    statusBar.textContent = "Processing... Please wait.";
    statusBar.className =
      "p-2.5 bg-blue-700 text-blue-100 text-sm text-center rounded-md border border-blue-600 min-h-[40px] flex items-center justify-center animate-pulse";
    processBtn.disabled = true;
    processBtn.classList.add("opacity-50", "cursor-not-allowed");
    outputSection.style.display = "none";
    processedFileListUI.innerHTML = "";

    const redactionOptions = {
      selected_patterns: selectedPatternKeys, 
      custom_keywords: customKeywordsInput.value
        .split(",")
        .map((k) => k.trim())
        .filter((k) => k),
    };
    
    const outputFormat = outputFormatSelect.value;

    try {
      let results = await window.pywebview.api.process_files_batch({
        filepaths: selectedFilePaths,
        redaction_options: redactionOptions, 
        output_format: outputFormat,
      });

      if (results && results.length > 0) {
        outputSection.style.display = "block";
        let allSuccessful = true;
        results.forEach((fileResult) => {
          const li = document.createElement("li");
          li.className =
            "processed-file-item flex justify-between items-center py-1.5 px-2 bg-slate-700 text-slate-200"; 
          if (fileResult.error) {
            allSuccessful = false;
            const errorSpan = document.createElement("span");
            errorSpan.textContent = `Error: ${fileResult.original_name || "unknown file"} - ${fileResult.error}`;
            errorSpan.className = "text-red-400 text-xs";
            li.appendChild(errorSpan);
          } else {
            const textSpan = document.createElement("span");
            textSpan.textContent = `${fileResult.original_name} (redacted to .${fileResult.output_format})`;
            textSpan.className = "text-slate-200";
            li.appendChild(textSpan);

            const downloadBtn = document.createElement("button");
            downloadBtn.textContent = "Download";
            downloadBtn.className = 
              "ml-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold py-1 px-2.5 rounded-md focus:outline-none focus:ring-1 focus:ring-teal-500 focus:ring-offset-1 focus:ring-offset-slate-800 transition duration-150";
            downloadBtn.onclick = () => {
              window.pywebview.api
                .save_processed_file(
                  fileResult.output_path,
                  fileResult.original_name,
                  fileResult.output_format,
                )
                .then((saveResult) => {
                  if (saveResult && saveResult.success) {
                    statusBar.textContent = `File '${fileResult.original_name}' saved.`;
                    statusBar.className =
                      "p-2.5 bg-green-700 text-green-100 text-sm text-center rounded-md border border-green-600 min-h-[40px] flex items-center justify-center";
                  } else if (
                    saveResult &&
                    saveResult.message === "Save cancelled."
                  ) {
                    statusBar.textContent = `Save cancelled for '${fileResult.original_name}'.`;
                    statusBar.className =
                      "p-2.5 bg-amber-700 text-amber-100 text-sm text-center rounded-md border border-amber-600 min-h-[40px] flex items-center justify-center";
                  } else {
                    statusBar.textContent = `Error saving '${fileResult.original_name}': ${saveResult.error || "Unknown save error"}`;
                    statusBar.className =
                      "p-2.5 bg-red-700 text-red-100 text-sm text-center rounded-md border border-red-600 min-h-[40px] flex items-center justify-center";
                  }
                });
            };
            li.appendChild(downloadBtn);
          }
          processedFileListUI.appendChild(li);
        });
        if (allSuccessful) {
          statusBar.textContent =
            "Processing complete. All files processed successfully.";
          statusBar.className =
            "p-2.5 bg-green-700 text-green-100 text-sm text-center rounded-md border border-green-600 min-h-[40px] flex items-center justify-center";
        } else {
          statusBar.textContent = "Processing complete. Some files had errors.";
          statusBar.className =
            "p-2.5 bg-amber-700 text-amber-100 text-sm text-center rounded-md border border-amber-600 min-h-[40px] flex items-center justify-center";
        }
      } else {
        if (results === null || (Array.isArray(results) && results.length === 0)) {
             statusBar.textContent = "Processing finished, but no results were returned. Check console for Python errors.";
        } else { 
             statusBar.textContent = "An unexpected issue occurred. No results from processing.";
        }
        statusBar.className = "p-2.5 bg-red-700 text-red-100 text-sm text-center rounded-md border border-red-600 min-h-[40px] flex items-center justify-center";
      }
    } catch (e) {
      console.error("Error calling process_files_batch:", e);
      statusBar.textContent = "Critical error during processing: " + String(e);
      statusBar.className =
        "p-2.5 bg-red-700 text-red-100 text-sm text-center rounded-md border border-red-600 min-h-[40px] flex items-center justify-center";
    } finally {
      processBtn.disabled = false;
      processBtn.classList.remove("opacity-50", "cursor-not-allowed");
      statusBar.classList.remove("animate-pulse");
    }
  });
});