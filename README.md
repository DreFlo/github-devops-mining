# Running

Needs ```.env``` file to work. See ```.env.example``` for variables. 

```bash
usage: tree_collection_loader.py [-h] [--delete-trees] [--check-database] [--delete-check-file] [filter_file_path]

Load trees from GitHub repositories into MongoDB

positional arguments:
  filter_file_path     Path for JSON file with filter for the repositories to load trees from, if not specified all repositories will be used

options:
  -h, --help           show this help message and exit
  --delete-trees       Delete all trees from the trees collection and exit
  --check-database     Check the database for inconsistencies with checkfile and exit
  --delete-check-file  Delete the repository check file
```