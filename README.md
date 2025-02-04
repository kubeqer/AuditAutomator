# Automated Audit Report Processor

This project automates the process of gathering audit reports from remote machines and generating a polished audit report in PDF format. It retrieves raw audit data from tools such as Lynis and OpenSCAP, converts these reports to JSON using external converters, processes the data (including comparing findings via cosine similarity), and then generates a final PDF audit report.

## Prerequisites

Before using this program, ensure that you have prepared your audit reports using the following tools. **These tools must be installed in the program directory:**

1. **Lynis Report Converter**  
   - Repository: [lynis-report-converter](https://github.com/d4t4king/lynis-report-converter)  
   - This tool converts the raw Lynis audit report (a `.dat` file) into JSON format.

2. **OpenSCAP Report Converter**  
   - Repository: [openscap-report](https://github.com/OpenSCAP/openscap-report)  
   - This tool converts the raw OpenSCAP audit report (XML format) into JSON format.

## Overview

The project automates the following tasks:

1. **Remote Audit Execution & Conversion:**  
   A shell script connects to a remote machine via SSH, runs Lynis and OpenSCAP audits, downloads the raw reports to a local directory, and converts them to JSON using the pre-installed converters.

2. **Data Processing:**  
   The program reads the generated JSON reports and processes the data by computing cosine similarities between audit findings. For each OpenSCAP rule, the program finds the best matching candidate from the Lynis details and suggestions. If the cosine similarity exceeds 0.5, the pair is considered a verified match; otherwise, the OpenSCAP rule is marked as unpaired. Any remaining unpaired Lynis records are also flagged as unpaired.

3. **Report Generation:**  
   A final PDF audit report is generated that includes:
   - A main page with the report date.
   - A section for each unique audit finding.  
     For Lynis records, if a record (identified by its `lynis_json_id`) has already been printed, it is skipped. Additionally, the report uses the `long_description` if available; otherwise, it falls back to the short description (`desc`). For clarity, if a Lynis record contains a `field` attribute, that value is appended to the service name in the header.

## Installation

1. **Clone the repository**

2. **Install the required Python packages**:

   ```bash
   pip install -r requirements.txt
3.  **Install the external converters in your program directory:**
     - **lynis-report-converter:** Follow the instructions on lynis-report-converter GitHub.
      - **openscap-report:** Follow the instructions on openscap-report GitHub.

## Usage

The project is designed to automate the entire audit process. It performs the following steps:

- **Run the Shell Script:**
Execute the provided shell script (audit.sh) to collect audit data from a remote machine, download the raw reports, and convert them to JSON.

- **Process and Generate the PDF Audit Report:**
Once the JSON reports are generated, run the main Python program (main.py) to process the audit data, compute comparisons, store the results in the database, and generate a final PDF report.
