import re
import sys
import subprocess
from pathlib import Path
import boto3

access_key_pattern = re.compile(r'\bAKIA[\w]{12,}\b')
secret_key_pattern = re.compile(r'\b[A-Za-z0-9\/+]{40,}\b')

def verify_aws_credentials(access_key, secret_key):
    try:
        client = boto3.client('sts', aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        client.get_caller_identity()
        return True
    except Exception as e:
        return False
    
def extract_code_block_and_line_numbers(repo_path, file_path, commit, access_key_regex, secret_key_regex):
    try:
        file_content = subprocess.check_output(
            ['git', '-C', str(repo_path), 'show', f'{commit}:{file_path}'],
            text=True
        )
    except subprocess.CalledProcessError:
        return "Could not extract code block due to error.", 0, 0, None, None

    lines = file_content.split('\n')
    access_key_line_num = secret_key_line_num = None
    for i, line in enumerate(lines):
        if access_key_regex.search(line):
            access_key_line_num = i + 1  # 1-indexed line number
        if secret_key_regex.search(line):
            secret_key_line_num = i + 1
        if access_key_line_num and secret_key_line_num:
            break  # Found both, stop searching

    if not access_key_line_num or not secret_key_line_num:
        return "Credentials not found in file.", 0, 0, None, None

    # Determine the code block start and end line numbers
    start_line = min(access_key_line_num, secret_key_line_num) - 3
    end_line = max(access_key_line_num, secret_key_line_num) + 3

    # Make sure that the start and end line numbers are within the bounds of the file
    start = max(0, start_line - 1)
    end = min(len(lines), end_line)

    # Prepend line numbers to each line in the code block
    '''Example: 
    1: line1
    2: line2
    3: line3
    '''
    numbered_code_block = "\n".join([f"{i+1}: {line}" for i, line in enumerate(lines[start:end], start)])

    return numbered_code_block, start + 1, end, access_key_line_num, secret_key_line_num


def detect_secrets_in_commit(repo_path, commit, processed_commits, branch_info=""):
    if commit in processed_commits:
        # Skip commit if it has already been processed
        return
    
    # Mark the commit as processed to avoid duplicate processing
    processed_commits.add(commit)

    try:
        # Get the commit metadata like author, date, message, etc.
        custom_format = "%H|%an|%aI|%s|%B"
        commit_metadata = subprocess.check_output(
            ['git', '-C', str(repo_path), 'show', commit, '--format=' + custom_format, '--no-abbrev', '-z'],
            text=True
        )
        # Extract commit metadata, -z flag is used to handle multi-line commit messages
        commit_id, author, author_date, subject, body = commit_metadata.strip('\x00').split('|', 4)
    except subprocess.CalledProcessError:
        return

    # Split the commit output into individual file changes, skipping the metadata
    file_changes = body.split('diff --git')[1:]
    for change in file_changes:
        if '+++ b/' not in change:
            continue
        file_path_match = re.search(r'\+\+\+ b/(.*)', change)
        if not file_path_match:
            continue
        
        ''' Extract the file path from the diff output
        Example:
        +++ b/path/to/file -> path/to/file
        '''
        file_path = file_path_match.group(1)
        '''
        Extract the code block containing the AWS credentials and the line numbers where they are found
        '''
        code_block, block_start, block_end, access_key_line, secret_key_line = \
            extract_code_block_and_line_numbers(repo_path, file_path, commit, access_key_pattern, secret_key_pattern)

        if access_key_line and secret_key_line:
            access_key, secret_key = "", ""  # Initialize variables to hold the credential values
            for line in code_block.split('\n'):
                if access_key_pattern.search(line):
                    access_key = access_key_pattern.search(line).group(0)
                if secret_key_pattern.search(line):
                    secret_key = secret_key_pattern.search(line).group(0)

            if access_key and secret_key:
                is_valid = verify_aws_credentials(access_key, secret_key)

                # Print out the findings
                print(f"Branch: {branch_info}\nCommit ID: {commit_id}\nAuthor: {author}\nDate: {author_date}\nMessage: {subject}")
                print(f"File: {file_path}\nAccess Key Line: {access_key_line}, Secret Key Line: {secret_key_line}")
                print(f"Verified credentials: {'Yes' if is_valid else 'No'}\nCode Block:\n{code_block}\n{'-'*60}\n")

# Process all branches in the repository to find AWS credentials
def process_branches(repo_path, branches, processed_commits):
    for branch in branches:
        branch = branch.strip('* ').strip().replace('remotes/origin/', '')

        # Get all commits in the branch
        commits = subprocess.check_output(['git', '-C', str(repo_path), 'log', branch, '--pretty=%H'], text=True).splitlines()
        branch_info = f"{branch}"
        for commit in commits:
            detect_secrets_in_commit(repo_path, commit, processed_commits, branch_info)

# Process the reflog to find any commits that may have been "lost" (e.g. due to a rebase)
def process_reflog(repo_path, processed_commits):

    # Get all commits in the reflog
    reflog_entries = subprocess.check_output(['git', '-C', str(repo_path), 'reflog', '--pretty=%H'], text=True).splitlines()
    for commit in reflog_entries:
        detect_secrets_in_commit(repo_path, commit, processed_commits, "Reflog Commit")

def find_aws_credentials(repo_path):

    # Resolve the repository path to an absolute path
    repo_path = Path(repo_path).resolve()

    # Ensure we have the latest info from all branches
    subprocess.run(['git', '-C', str(repo_path), 'fetch', '--all'], check=True)

    # Keep track of processed commits to avoid duplicate processing
    processed_commits = set()

    # Get the list of all branches in the repository
    branches = subprocess.check_output(['git', '-C', str(repo_path), 'branch', '-a'], text=True).splitlines()
    process_branches(repo_path, branches, processed_commits)
    process_reflog(repo_path, processed_commits)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 detect.py <path_to_git_repo>")
        sys.exit(1)

    repo_path = sys.argv[1]
    find_aws_credentials(repo_path)