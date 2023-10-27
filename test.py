from dotenv import load_dotenv
load_dotenv()

import mongodb_wrappers

wrapper = mongodb_wrappers.MongoDBWrapper()

repo_tool_histories_list = [repo['repo_full_name'] for repo in wrapper.get_repo_tool_histories(projection={'repo_full_name'})]

repo_tool_histories_set = set(repo_tool_histories_list)

print(len(repo_tool_histories_set)/len(repo_tool_histories_list))
