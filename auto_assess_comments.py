from canvasapi import Canvas
import sys
import json

def format_comment(comment, name = None, conjunction = None):
    formatted = comment
    formatted = formatted.replace("%n%", name)

    if conjunction is not None:
        c_tokens = conjunction.split(":")
        if c_tokens[0] == "p":
            formatted = formatted.replace("%p%", (c_tokens[1] + " "))
        elif c_tokens[0] == "m":
            formatted = formatted.replace("%m%", c_tokens[1])

    # clear out all formatters
    formatted = formatted.replace("%m%", "")
    formatted = formatted.replace("%p%", "")
    formatted = formatted.replace("%n%", "")
    # clear out any double spaces
    formatted = formatted.replace("  ", " ")
    # if the first letter is a space, remove that too
    if formatted[0] == " ":
        formatted = formatted.replace(" ", "", 1)

    # capitalise first letter
    first_char = formatted[0]
    upper_first_char = first_char.upper()
    formatted = formatted.replace(first_char, upper_first_char, 1)

    return formatted

canvas = Canvas("https://jmss.instructure.com", "12164~e6cU5awEgsp4MhejWXO5pIyDQVzPBT71P8e10drhReECgQZjIMlPvfffcDIC5Fz9")

if len(sys.argv) == 2:
    config_file = sys.argv[1]
else:
    config_file = "config_comments.json"


config = open(config_file)
c = json.load(config)
course_id = c["course"]
assignment_id = c["assignment"]

course = canvas.get_course(course_id)
assignment = course.get_assignment(assignment_id)

users_list = input("Input a list of user IDs (enter for auto):")
if len(users_list) == 0:
    users = course.get_users(
        enrollment_type=['student'],
        enrollment_state=['active'])
    users = [user.id for user in users]
else:
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
        users = list(users_list.split(","))

for user in users:
    submission = assignment.get_submission(user, include="rubric_assessment")
    username = course.get_user(user).name
    
    print(user, username)
    print(submission)

    try:              
        total = 0

        scores = []
        comment = ""
        first_name = username.split(" ")[0]
            
        for n, rating in enumerate(submission.rubric_assessment.values()):
            points = float(rating["points"])
            total += float(rating["points"])
            
            print (points)

            scores.append(points)

        # TODO: FIX THIS!! Hardcoded at 3 points max right now
        grand_total = len(scores) * 3

        # check for extension tasks
        extension_ids = c["rubric"]["extensions"]
        for n, score in enumerate(scores):
            if n in extension_ids and scores[n] > 0:
                comment += "EXTENSION attempted. Personalise!!\n\n"
                break

        total_qualifier = None
        percentage = float(total)/grand_total * 100.0
        print("Overal percentage:", percentage)

        # determining overall comment
        opening_range = c["rubric"]["opening"].keys()
        for k in opening_range:
            if percentage >= float(k):
                comment += format_comment(c["rubric"]["opening"][k], first_name)
                break

        # rubric comments
        criteria_ids = c["rubric"]["criteria"].keys()
        rubric_positive_comments = []
        rubric_neutral_comments = []
        rubric_constructive_comments = []

        positive_ordinal = 0
        constructive_ordinal = 0

        for criteria_id in criteria_ids:
            if criteria_id not in c["rubric"]["criteria"]:
                continue

            if scores[int(criteria_id)] >= int(c["rubric"]["criteria"][criteria_id]["ranges"][0]):
                if len(c["rubric"]["criteria"][criteria_id]["positives"]) == 0:
                    continue
                rubric_positive_comments.append( \
                    format_comment(c["rubric"]["criteria"][criteria_id]["positives"], first_name, \
                                   c["rubric"]["conjunctions"]["positives"][positive_ordinal]))
                positive_ordinal += 1
                if positive_ordinal >= len(c["rubric"]["conjunctions"]["positives"]):
                    positive_ordinal = len(c["rubric"]["conjunctions"]["positives"]) - 1

            elif scores[int(criteria_id)] >= int(c["rubric"]["criteria"][criteria_id]["ranges"][-1]):
                if len(c["rubric"]["criteria"][criteria_id]["constructives"]) == 0:
                    continue
                rubric_constructive_comments.append( \
                    format_comment(c["rubric"]["criteria"][criteria_id]["constructives"], first_name, \
                                   c["rubric"]["conjunctions"]["constructives"][constructive_ordinal]))
                constructive_ordinal += 1
                if constructive_ordinal >= len(c["rubric"]["conjunctions"]["constructives"]):
                    constructive_ordinal = len(c["rubric"]["conjunctions"]["constructives"]) - 1


        for com in rubric_positive_comments:
            comment += " " + com
        for com in rubric_constructive_comments:
            comment += " " + com

        # summarising comment
        closing_range = c["rubric"]["closing"].keys()
        for k in closing_range:
            if percentage >= float(k):
                comment += " " + format_comment(c["rubric"]["closing"][k], first_name)

        print("Total points: ", total)
        print("Entered points: ", submission.score)
        print(comment)
    
    except Exception as e:
        print(e)


    #submission.edit(submission={"posted_grade":total})
    #submission.edit(submission={"submission_comments":[]})

    #submission.edit(comment={"text_comment":comment})

    input("Press enter for the next student...")

config.close()
'''
total = 0
for rating in submission.rubric_assessment.values():
    total += float(rating["points"])
print(total)
submission.edit(submission={"posted_grade":total})
'''
