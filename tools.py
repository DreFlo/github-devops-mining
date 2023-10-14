# Adapted from Hugo's work
import requests 
import json
import time
import base64
from re import search, IGNORECASE

from github_api_wrappers import *

sleep = 2

Maven = "Maven"
Kubernetes = "Kubernetes"

repos_filename = [("Travis","\.travis\.yml"),
                        ("Gradle","Build\.gradle"),
                        ("Rake","Rakefile"),
                        ("Jenkins","Jenkinsfile"),
                        ("Rancher","Kube_config_rancher-cluster\.yml"),
                        ("Docker","Dockerfile"),
                        ("Progress Cheff","Metadata\.rb"),
                        ("Puppet","Site\.pp"),
                        ("Nagios","Nagios\.cfg"),
                        ("Prometheus","Prometheus\.yml"),
                        ("Maven","pom\.xml"),
                        ("CircleCI","circleci"),
                        ('Kubernetes',"deployment\.yml"),
                        ('Kubernetes',"service\.yml")]
    
repos_code = [("JUnit","org\.junit\.runner\.JUnitCore"),
                    ("Selenium","org\.seleniumhq\.selenium"),
                    ("Mesos","org\.apache.mesos")]

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

def find_repo_trees_tools(trees,max_file_calls=10):
    tools_history = [] # [{'date' : $date, 'sha' : $sha, 'tools' : [$tool1, $tool2, ...]}]

    for tree in trees:
        
        tools = set()

        count_file_calls = 0

        for f in tree['tree']:
            tool = check_file_names(repos_filename,f["path"])
            
            if tool != None:
            
               
                tools.add(tool)
            
                if (tool == Maven) and (count_file_calls < max_file_calls):
                    
                    count_file_calls += 1

                    contents = decoded_base_64(f["url"])
                    tool = check_file_contents(repos_code,contents)
            
                    if tool != None:
                        
                        tools.add(tool)

        tools_history.append({'date' : tree['date'], 'sha' : tree['sha'], 'tools' : list(tools)})
    
    return tools_history