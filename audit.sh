#!/bin/bash

GREEN="\e[32m"
RED="\e[31m"
RESET="\e[0m"

read -p "Enter the local reports directory (default: $(pwd)/reports): " REPORTS_DIR
REPORTS_DIR=${REPORTS_DIR:-$(pwd)/reports}

read -p "Enter the remote username: " REMOTE_USER
read -sp "Enter the remote user password: " REMOTE_USER_PASSWORD
echo
read -p "Enter the remote host or IP address: " REMOTE_HOST
read -p "Enter the remote reports directory (default: /tmp/reports): " REMOTE_REPORTS_DIR
REMOTE_REPORTS_DIR=${REMOTE_REPORTS_DIR:-/tmp/reports}

read -p "Enter the OpenSCAP benchmark path on the remote system (default: /usr/share/xml/scap/ssg/content/ssg-debian12-ds.xml): " REMOTE_BENCHMARK
REMOTE_BENCHMARK=${REMOTE_BENCHMARK:-/usr/share/xml/scap/ssg/content/ssg-debian12-ds.xml}

if [ ! -d "$REPORTS_DIR" ]; then
    mkdir "$REPORTS_DIR"
    echo -e "${GREEN}Created folder: $REPORTS_DIR${RESET}"
fi

LYNIS_REPORT_FILE="$REPORTS_DIR/lynis-report.dat"
OSCAP_REPORT_FILE="$REPORTS_DIR/openscap-report.xml"

echo -e "${GREEN}Connecting to $REMOTE_HOST via SSH for Lynis audit.${RESET}"
sshpass -p "$REMOTE_USER_PASSWORD" ssh "$REMOTE_USER@$REMOTE_HOST" bash << EOF
    if [ ! -d "$REMOTE_REPORTS_DIR" ]; then
        mkdir -p "$REMOTE_REPORTS_DIR"
        echo "Created folder: $REMOTE_REPORTS_DIR"
    fi

    echo "$REMOTE_USER_PASSWORD" | sudo -S lynis audit system --report-file "$REMOTE_REPORTS_DIR/lynis-report.dat"
    if [ \$? -eq 0 ]; then
        echo "Lynis audit completed. Report saved to $REMOTE_REPORTS_DIR/lynis-report.dat"
    else
        echo "Lynis audit failed."
        exit 1
    fi

    echo "$REMOTE_USER_PASSWORD" | sudo -S chmod +r "$REMOTE_REPORTS_DIR/lynis-report.dat"
    exit
EOF

if [ ! -d "$REPORTS_DIR" ]; then
    mkdir -p "$REPORTS_DIR"
    echo "Created folder: $REMOTE_REPORTS_DIR"
fi

sudo scp "$REMOTE_USER@$REMOTE_HOST:$REMOTE_REPORTS_DIR/lynis-report.dat" "$REPORTS_DIR"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Downloaded Lynis report to $REPORTS_DIR$LYNIS_REPORT_FILE${RESET}"
else
    echo -e "${RED}Failed to download Lynis report.${RESET}"
    exit 1
fi
sudo ./lynis-report-converter/lynis-report-converter.pl --input "$LYNIS_REPORT_FILE" --json --output "$REPORTS_DIR/lynis-report.json"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Converted Lynis report to json: $REPORTS_DIR/lynis-report.json${RESET}"
else
    echo -e "${RED}Failed to convert Lynis report.${RESET}"
    exit 1
fi

echo -e "${GREEN}Running OpenSCAP audit on remote system.${RESET}"
sudo oscap-ssh "$REMOTE_USER@$REMOTE_HOST" 22 xccdf eval \
    --profile xccdf_org.ssgproject.content_profile_standard \
    --results "$OSCAP_REPORT_FILE" \
    "$REMOTE_BENCHMARK"
if [ $? -eq 0 ] || [ $? -eq 2 ]; then
    echo -e "${GREEN}OpenSCAP audit completed. Report saved to $OSCAP_REPORT_FILE${RESET}"
else
    echo -e "${RED}OpenSCAP audit failed.${RESET}"
fi
sudo oscap-report -f JSON -o "$REPORTS_DIR/openscap-report.json" "$REPORTS_DIR/openscap-report.xml"

echo -e "${GREEN}All reports generated successfully in the $REPORTS_DIR folder.${RESET}"
