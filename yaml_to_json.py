from utils import read_yaml
import json
import re
from datetime import datetime


def get_date_difference(start_date: str, end_date: str) -> str:
    try:
        # Convert the date strings to datetime objects
        date1 = datetime.strptime(start_date, "%Y.%m")
        date2 = datetime.strptime(end_date, "%Y.%m")

        # Calculate the difference in years
        year_difference = abs(date1.year - date2.year)
        month_difference = abs(date1.month - date2.month)

        if year_difference >= 1:
            formatted_result = "{:.1f}".format(year_difference + month_difference / 12) + " years"
        else:
            formatted_result = str(month_difference) + " months"
        return str(formatted_result)
    except ValueError:
        return ""  # Handle invalid date strings gracefully


def format_date(date: str) -> str:
    tmp_date = datetime.strptime(date, "%Y.%m")
    return f'{str(tmp_date.month)}/{str(tmp_date.year)}'


def _list_to_markdown(list_data: list) -> str:
    res_str = ""
    for item in list_data:
        res_item = re.sub(r'Highlight \d+:', '', str(item))
        res_str += "* " + res_item + "\n"
    return res_str


def yaml_to_json(yaml):
    raw_json = json.loads(json.dumps(yaml, indent=4))

    web_json = {}

    # Basics
    web_basic = {}
    raw_basic = raw_json['basic']
    web_basic['name'] = raw_basic['name']
    web_basic['label'] = raw_basic.get('label', "")
    web_basic['bio'] = raw_basic['bio']
    web_basic['image'] = ""
    web_basic['email'] = raw_basic['contact']['email']
    web_basic['phone'] = raw_basic['contact']['phone']
    web_basic['url'] = ""
    web_basic['summary'] = raw_json.get('summary', "")
    web_basic['location'] = {}
    web_basic['location']['address'] = raw_basic['address']
    web_basic['location']['postalCode'] = ""
    web_basic['location']['city'] = raw_basic['address'].split(',')[0]
    web_basic['location']['countryCode'] = ""
    web_basic['location']['region'] = ""
    web_basic['relExp'] = ""
    web_basic['totalExp'] = "2 Years"
    web_basic['objective'] = ""
    web_basic['profiles'] = []
    for website in raw_basic['websites']:
        web_basic['profiles'].append({
            "network": website['icon'],
            "username": website['text'],
            "url": website['url']
        })
    web_json["basics"] = web_basic

    # Skills
    web_skill = {"languages": [], "frameworks": [], "libraries": [],
                 "databases": [], "technologies": [], "practices": [], "tools": []}
    raw_technical = []
    raw_non_technical = []
    for category in raw_json['skills']:
        if 'Technical' in category['category']:
            raw_technical = category['skills']
        elif 'Non-technical' in category['category']:
            raw_non_technical = category['skills']
    for skill in raw_technical:
        web_skill['technologies'].append({
            "name": skill,
            "level": 3
        })
    for skill in raw_non_technical:
        web_skill['practices'].append({
            "name": skill,
            "level": 3
        })
    web_json['skills'] = web_skill

    # Work Experiences
    web_work = []
    for work in raw_json["experiences"]:
        web_work.append({
            "id": "1",
            "name": work['company'],
            "position": ' | '.join(job['name'] for job in work['titles']),
            "url": "",
            "isWorkingHere": False,
            "startDate": format_date(str(work['startdate'])),
            "endDate": format_date(str(work['enddate'])),
            "years": get_date_difference(str(work['startdate']), str(work['enddate'])),
            "highlights": work.get('highlights', []),
            "summary": _list_to_markdown(work.get('highlights', []))
        })
    web_json['work'] = web_work

    # Education
    web_education = []
    for edu in raw_json['education']:
        web_edu = {
            'institution': edu['school'],
            'url': "",
            'studyType': edu['type'],
            'area': edu['area'],
            'branch': edu['branch'],
            'startDate': format_date(str(edu['startdate'])),
            'endDate': format_date(str(edu['enddate'])),
            'score': edu.get('gpa', ""),
            'courses': edu.get('courses', [])
        }
        web_education.append(web_edu)
    web_json['education'] = web_education

    # activities
    web_activities = {"involvements": "", "achievements": ""}
    achievements = ""
    for award in raw_json.get('achievements', []):
        achievements += f"* {award['year']}: {award['title']} ({award['money']})\n"
    web_activities['achievements'] = achievements

    web_json['activities'] = web_activities

    web_json['projects'] = []
    for proj in raw_json['projects']:
        web_json['projects'].append({
            **proj,
            'summary': f"* **Skills**: {proj['skills']} \n" + _list_to_markdown(proj.get('highlights', []))
        })
    web_json['volunteer'] = raw_json.get("volunteer", [])
    web_json['awards'] = raw_json.get("awards", [])

    return web_json


def main():
    # yaml_data = read_yaml(filename='./my_applications/resume_raw.yaml')
    # yaml_data = read_yaml(filename='my_applications/20230916__NOIR__VueJS Developer/VueJS Developer.yaml')
    yaml_data = read_yaml(filename='my_applications/20230917__Solas IT Recruitment__Frontend React Developer.yaml')
    print(yaml_data)
    json_data = yaml_to_json(yaml_data)
    print(json_data)

    # Write the data to the JSON file
    with open("data.json", "w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file)


if __name__ == '__main__':
    main()
