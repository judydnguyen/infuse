Generate a dependency lock file for this Python project.

The project files are located in `/app`. You must:
	•	Read `main.py`, `utils.py`, and `requirements.txt` in full to identify all required dependencies
	•	Determine the exact installed versions of each dependency (e.g., using `pip freeze`)
	•	Produce a lock file that captures the pinned versions of all packages listed in `requirements.txt`

Output requirements:
	•	Write the lock file to `/app/requirements.lock`
	•	Each entry must pin to an exact version using `==` (e.g., `requests==2.31.0`)
	•	Include only packages from `requirements.txt` (transitive dependencies are optional)
	•	The file must be sorted alphabetically by package name (case-insensitive)
	•	No blank lines or comments

Constraints:
	•	Do not modify `main.py`, `utils.py`, or `requirements.txt`
	•	Do not add packages not present in `requirements.txt`
	•	Do not use version ranges (`>=`, `<=`, `~=`, etc.) — exact pins only