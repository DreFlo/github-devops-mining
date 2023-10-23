# Adapted from Hugo's work
import requests 
import json
import time
import base64
from concurrent.futures import ThreadPoolExecutor
from re import search, IGNORECASE

from github_api_wrappers import *

sleep = 0
sleep_code = 1
workers = 200
workers_git = 32

Maven = "Maven"
Kubernetes = "Kubernetes"
GitHubActions = "GitHubActions"

repos_filename = [("Agola","\.agola"),
                  ("AppVeyor","appveyor\.yml"),
                  ("ArgoCD","argo\-cd"),
                  ("Bytebase","air\.toml"),
                ("Cartographer","cartographer\.yaml"),
                ("CircleCI","circleci"),
                ("Cloud 66 Skycap","cloud66"),
                ("Cloudbees Codeship","codeship\-services\.yml"),
                ("Devtron","devtron\-ci\.yaml"),
                ("Flipt","flipt\.yml"),
                ("GitLab","gitlab\-ci\.yml"),
                ("Google Cloud Build","cloudbuild\.yaml"),
                ("Helmwave","helmwave\.yml"),
                ("Travis","\.travis\.yml"),
                ("Jenkins","Jenkinsfile"),
                ("JenkinsX","jx\-requirements\.yml"),
                ("JenkinsX","buildPack\/pipeline\.yml"),
                ("JenkinsX","jenkins\-x\.yml"),
                ("Keptn","charts\/keptn\/"),
                ("Liquibase","liquibase\.properties"),
                ("Mergify","mergify"),
                ("OctopusDeploy"," \.octopus"),
                ("OpenKruise","charts\/kruise\/"),
                ("OpsMx","charts\/isdargo\/"),
                ("Ortelius","component\.toml"),
                ("Screwdriver","screwdriver\.yaml"),
                ("Semaphore","\.semaphore\/semaphore\.yaml"),
                ("TeamCity","\.teamcity"),
                ("werf","werf\.yaml"),
                ("Woodpecker CI", "\.woodpecker\.yml")]

repos_code_yml = [("Codefresh","DaemonSet"),
                ("Codefresh","StatefulSet"),
                 ("XL Deploy","apiVersion\: \(xl-deploy\|xl\)"),
                ("Drone","kind\:"),
                ("Flagger","flagger"),
                ("Harness.io","featureFlags\:"),
                ("Flux","fluxcd"),
                ("GoCD","stages\:"),
                ("Concourse","resources\:"),
                  ("Kubernetes","apiVersion\:"),
                  ("GitHubActions","jobs\:"),
                  ("AWS CodePipeline","roleArn"),
                   ]

def check_file_names(filestools,filename):
    
    for (tool,name) in filestools:
        if search(name,filename,IGNORECASE):
            return tool

    return None

def check_file_extension(toolsextensions,filename):

    for(tool,extension) in toolsextensions:
        if search(extension, filename,IGNORECASE):
            return tool
    
    return None

def check_file_contents(toolcontents,filecontents):

    for(tool,content) in toolcontents:
        if search(content,filecontents,IGNORECASE):
            return tool
        
    return None

def checkExtension(extension,filename):

    if search(extension,filename):
        return True

    return False

def checkExtensionTree(extension,tree):
    
    for f in tree['tree']:
        if checkExtension(extension,f["path"]):
            return True
        
    return False

def check_tools(reponame,repos_code,extension):
    
    tools = set()

    for t in repos_code:
        time.sleep(sleep_code)
        if len(get_content_repositories(t[1],reponame,extension)) > 0:
            tools.add(t[0])

    return tools

def check_tools_read_file(reponame,repos_code,tree,branch,extension):

    tools = set()


    ###with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    ###results = pool.map(tester, urls)~


    with ThreadPoolExecutor(max_workers=workers) as executor:

        tasks = []

        for f in tree['tree']:

            if checkExtension(extension,f["path"]):
                t = executor.submit(get_raw_file,reponame,branch,f["path"])
                tasks.append(t)

        for t in tasks:
            
            
            rawf = t.result()

            for r in repos_code:
                    
                    if check_file_contents([r] ,rawf):
                        tools.add(r[0])

    return tools

def count_extension(tree,extension):
    
    count = 0
    for f in tree['tree']:
        if checkExtension(extension,f["path"]):
            count += 1

    return count

def find_tools_inside_files(repo_full_name, repo_default_branch,tree):

    tools = set()
          
    if checkExtensionTree("\.yml",tree) or checkExtensionTree("\.yaml",tree):
        
        new_tools = check_tools_read_file(repo_full_name,repos_code_yml,tree,repo_default_branch,"\.yml")
        tools = tools.union(new_tools)

        new_tools = check_tools_read_file(repo_full_name,repos_code_yml,tree,repo_default_branch,"\.yaml")
        tools = tools.union(new_tools)

    return tools

def find_repo_trees_tools(repo_full_name, default_branch, trees):
    tools_history = [] # [{'date' : $date, 'sha' : $sha, 'tools' : [$tool1, $tool2, ...]}]

    for tree in trees:
        
        tools = set()

        if not 'tree' in tree: 
            tools_history.append({'date' : tree['date'], 'sha' : tree['sha'], 'tools' : list(tools), 'warning' : 'No tree found'})
            continue

        for f in tree['tree']:
            tool = check_file_names(repos_filename,f["path"])
                
            if tool != None:
                
                tools.add(tool)

        new_tools = find_tools_inside_files(repo_full_name, default_branch,tree)

        tools = tools.union(new_tools)

        tools_history.append({'date' : tree['date'], 'sha' : tree['sha'], 'tools' : list(tools)})
    
    return tools_history
        
    
