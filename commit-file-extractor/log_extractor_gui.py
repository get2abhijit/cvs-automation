import re
import tkinter as tk
from tkinter import scrolledtext

def extract_file_info(log_data):
    """
    Extracts file paths and new revision numbers from CVS log data.

    Args:
        log_data (str): The CVS log data as a single string.

    Returns:
        A list of strings, where each string is in the format
        "filepath: new_revision;".
    """
    # The regular expression pattern is designed to find two specific pieces of information:
    # 1. The file path, which is located after " <-- ".
    # 2. The new revision number, which is located after "new revision: ".
    
    # Let's break down the pattern:
    # '--\s+'        - Matches the literal " <-- " (note the whitespace after the arrow).
    # '(.+?)\n'      - This is the first capturing group.
    #                - (.+?) matches any character (.) one or more times (+),
    #                  but non-greedily (?). This ensures it captures the file path
    #                  until it hits the next part of the pattern.
    #                - \n matches the newline character.
    # 'new revision:\s+' - Matches the literal "new revision: ", followed by one or more spaces.
    # '([\d.]+);'      - This is the second capturing group.
    #                - [\d.] matches any digit or a period.
    #                - + matches one or more of the preceding characters.
    #                - ; matches the literal semicolon.
    
    # We use re.DOTALL to allow the '.' in the pattern to match newline characters,
    # which is essential for processing the multi-line log string.
    pattern = re.compile(r'--\s+(.+?)\nnew revision:\s+([\d.]+);', re.DOTALL)
    
    # Find all occurrences of the pattern in the log data.
    matches = pattern.findall(log_data)
    
    results = []
    for file_path, revision in matches:
        # For each match, format the output string and add it to the results list.
        # We also use .strip() to remove any leading/trailing whitespace from the extracted file path.
        results.append(f"{file_path.strip()}: {revision};")

    return results

def run_extraction():
    """
    This function is called when the 'Extract' button is clicked.
    It gets the input text, runs the extraction, and displays the output.
    """
    # Get the text from the input ScrolledText widget
    log_data = input_text_widget.get("1.0", tk.END)
    
    # Clear the previous content from the output ScrolledText widget
    output_text_widget.configure(state=tk.NORMAL)  # Enable editing
    output_text_widget.delete("1.0", tk.END)
    
    # Run the extraction function
    extracted_info = extract_file_info(log_data)
    
    # Format the output as a single string, with each result on a new line
    output_string = "\n".join(extracted_info)
    
    # Insert the new output into the widget
    output_text_widget.insert(tk.END, output_string)
    
    # Disable editing for the output widget
    output_text_widget.configure(state=tk.DISABLED)

# Create the main application window
app = tk.Tk()
app.title("CVS Log Extractor")
app.geometry("800x600")

# Set up the main frame
main_frame = tk.Frame(app, padx=10, pady=10)
main_frame.pack(fill=tk.BOTH, expand=True)

# Create and pack the input label and text widget
input_label = tk.Label(main_frame, text="Paste your CVS log here:", font=("Helvetica", 12))
input_label.pack(anchor="w", pady=(0, 5))
input_text_widget = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, relief=tk.GROOVE, bd=2)
input_text_widget.pack(fill=tk.BOTH, expand=True)

# Create and pack the extraction button
extract_button = tk.Button(main_frame, text="Extract Revisions", font=("Helvetica", 12, "bold"), command=run_extraction)
extract_button.pack(pady=10)

# Create and pack the output label and text widget
output_label = tk.Label(main_frame, text="Extracted Files (copy from here):", font=("Helvetica", 12))
output_label.pack(anchor="w", pady=(5, 5))
output_text_widget = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, relief=tk.GROOVE, bd=2, state=tk.DISABLED)
output_text_widget.pack(fill=tk.BOTH, expand=True)

# Start the application main loop
app.mainloop()
