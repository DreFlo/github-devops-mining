# Running

Needs ```.env``` file to work. See ```.env.example``` for variables. 

```bash
usage: main.py [-h] [--delete-tools] [--check-database] [--delete-check-file] [--test-github-api-limits] [--sanity-check] [--interrupt-at INTERRUPT_AT] [--stop-if-no-sample]

Load trees from GitHub repositories into MongoDB

options:
  -h, --help            show this help message and exit
  --delete-tools        Delete all tools from the repo histories collection and exit
  --check-database      Check the database for inconsistencies with check file and exit
  --delete-check-file   Delete the repository check file
  --test-github-api-limits
                        Test the GitHub API limits and exit
  --sanity-check        Perform a sanity check on the database and exit
  --interrupt-at INTERRUPT_AT
                        Interrupt the program at the specified time, format: YYYY-MM-DDTHH:MM
  --stop-if-no-sample   Stop program if no sample of repos can be retrieved
```