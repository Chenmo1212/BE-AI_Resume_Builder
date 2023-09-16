from utils import read_yaml
import json
from datetime import datetime


def get_year_difference(start_date, end_date):
    try:
        # Convert the date strings to datetime objects
        date1 = datetime.strptime(start_date, "%Y.%m")
        date2 = datetime.strptime(end_date, "%Y.%m")

        # Calculate the difference in years
        year_difference = abs(date1.year - date2.year)
        month_difference = abs(date1.month - date2.month)
        formatted_result = "{:.2f}".format(year_difference + month_difference / 12)

        return str(formatted_result)
    except ValueError:
        return ""  # Handle invalid date strings gracefully


def _list_to_markdown(list_data: list) -> str:
    res_str = ""
    for item in list_data:
        res_str += "* " + str(item) + "\n"
    return res_str


def yaml_to_json(yaml):
    raw_json = json.loads(json.dumps(yaml, indent=4))

    web_json = {}

    # Basics
    web_basic = {}
    raw_basic = raw_json['basic']
    web_basic['name'] = raw_basic['name']
    web_basic['label'] = raw_basic.get('label', "")
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
            "position": ', '.join(job['name'] for job in work['titles']),
            "url": "",
            "isWorkingHere": False,
            "startDate": str(work['startdate']),
            "endDate": str(work['enddate']),
            "years": get_year_difference(str(work['startdate']), str(work['enddate'])) + " years",
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
            'startDate': str(edu['startdate']),
            'endDate': str(edu['enddate']),
            'score': edu.get('gpa', ""),
            'courses': edu.get('courses', [])
        }
        web_education.append(web_edu)
    web_json['education'] = web_education

    # activities
    web_activities = {"involvements": "", "projects": [], "achievements": ""}
    for proj in raw_json['projects']:
        web_activities['projects'].append(proj)
    web_json['activities'] = web_activities

    web_json['volunteer'] = []
    web_json['awards'] = []

    for award in raw_json.get('achievements', []):
        web_json['awards'].append({
            "title": award['title'],
            "date": award['year'],
            "awarder": "",
            "summary": "",
            "id": award['title'],
        })

    return web_json


def main():
    # yaml_data = read_yaml(filename='./my_applications/resume_raw.yaml')
    yaml_data = read_yaml(filename='my_applications/20230916__NOIR__VueJS Developer/VueJS Developer.yaml')
    print(yaml_data)
    json_data = yaml_to_json(yaml_data)
    print(json_data)

    # Write the data to the JSON file
    with open("data.json", "w") as json_file:
        json.dump(json_data, json_file)


if __name__ == '__main__':
    main()
