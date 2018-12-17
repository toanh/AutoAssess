from canvasapi import Canvas
import requests
import zipfile
import os
import shutil
import subprocess
from subprocess import run, PIPE
import json

import sys

def evaluate_assignment(filename, input_str = None, output_str = None, delimiter = ':'):

    p = run(['python', filename], stdout=PIPE, stderr=PIPE,
            input=input_str, encoding='ascii')

    if len(p.stderr) > 0:
        return 0
    output = p.stdout
    

    # parsing the output
    answer = output.split(delimiter)[-1].lstrip()
    
    print(answer)

    if answer == output_str:
        return 1
    else:
        return 0

if len(sys.argv) == 2:
    config_file = sys.argv[1]    
else:
    config_file = "config.json"

inputs = []
outputs = []

with open(config_file) as config:
    c = json.load(config)
    course_id = c["course"]
    assignment_id = c["assignment"]
    directory = c["directory"]
    includes = c["includes"]
    includes = includes.split(",")
    execute = c["execute"]
    test_cases = c["testcases"]

print (course_id, assignment_id)

canvas = Canvas("https://jmss.instructure.com", "12164~e6cU5awEgsp4MhejWXO5pIyDQVzPBT71P8e10drhReECgQZjIMlPvfffcDIC5Fz9")

course = canvas.get_course(course_id)
assignment = course.get_assignment(assignment_id)

users_list = input("Input a list of user IDs (enter for auto):")
if len(users_list) == 0:    
    users = course.get_users(
        enrollment_type=['student'],
        enrollment_state=['active'])
    
    #users = course.get_users()
    users = [user.id for user in users]
    print(users)
else:
    # a ',' means process all remaining students in the canvas roster AFTER the last student in the
    # user supplied list
    if users_list[-1] == ",":
        users_temp = course.get_users(
            enrollment_type=['student'],
            enrollment_state=['active'])
        users_temp = [user.id for user in users_temp]    
        users = list(users_list.split(","))
        del users[-1]
        last_user = users[-1]
        i = 0
        while i < len(users_temp):
            if users_temp[i] != int(last_user):
                del users_temp[i]
            else:
                del users_temp[i]
                break
        users += users_temp
    else:
        # no trailing ',' means just process those students in the user supplied list
        users = list(users_list.split(","))
    
for user in users:
    submission = assignment.get_submission(user, include="rubric_assessment")
    username = course.get_user(user).name
    
    print(user, username)
    print(submission)

    if submission.score is not None and len(str(submission.score)) > 0:
        print("Already graded...", end="")
        if submission.grade_matches_current_submission is not None and \
            submission.grade_matches_current_submission == False:
            answer = input("\nNew submission detected, re-grade?[y/n]")
            if answer.lower() != "y":
                print("Skipping")
                continue
        else:
            print("Skipping")
            continue

    try:              
        total = 0
        comment = ""
        first_name = username.split(" ")[0]

        for file in submission.attachments:
            username = course.get_user(user).name
            print("Processing submission for user: " + username)
            
            # downloads the attachments
            url = file['url']
            r = requests.get(url, allow_redirects=True)

            if len(directory) == 0:
                # creates the directory to extract
                dir_name = username.split(".")[0] 
                if os.path.exists(dir_name):
                    shutil.rmtree(dir_name)
                    while os.path.exists(dir_name):
                        pass
                os.mkdir(dir_name)
            else:
                dir_name = directory

            exec_file = file['display_name']
            full_path = dir_name + "/" + exec_file
            
            open(full_path, 'wb').write(r.content)

            #zf = zipfile.ZipFile(file['display_name'])            
            #zf.extractall(dir_name)

            if full_path[-4:].lower() == ".zip":
               zf = zipfile.ZipFile(full_path)
               zf.extractall(dir_name)

            if len(execute) > 0:
                full_path = dir_name + "/" + execute
                if not os.path.exists(full_path):
                    if input(full_path + " does not exist for execution. Would you like to execute the default submission [y/n]?").lower() == "y":
                        full_path = dir_name + "/" + file['display_name']
                        
                    else:
                        print("Not auto assessing...")
                        continue
                exec_file = execute
            
            for include in includes:
                if len(include) > 0:
                    shutil.copy(include, dir_name)
            
            print(file['url'])

            if len(test_cases) > 0:
                score = 0
                for n, t in enumerate(test_cases):
                    returned_score = evaluate_assignment(full_path, t[0], t[1])
                    if returned_score == 0:
                        print("Failed test case: ", n + 1)
                    else:
                        print("Passed test case: ", n + 1)
                    score += returned_score
                if score == len(test_cases):
                    score = 1
                else:
                    score = 0                
                print("score: ", score)    
                submission.edit(submission={"posted_grade":score})
            else:
                print("Executing: ", full_path)
                run(['python', exec_file], cwd = dir_name)

    except Exception as e:
        print(e)
        print("Error with extracting submission for student " + str(user))
                
    #submission.edit(submission={"submission_comments":[]})
    #submission.edit(comment={"text_comment":"A good effort."})
    input("Press enter for the next student...")

input("All done! Press enter to exit")

'''
total = 0
for rating in submission.rubric_assessment.values():
    total += float(rating["points"])
print(total)
submission.edit(submission={"posted_grade":total})
'''
