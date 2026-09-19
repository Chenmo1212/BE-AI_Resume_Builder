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

    web_json = raw_json

    # Basics

    # Skills — pass through the frontend flat format produced by Pipeline._skills_to_frontend_format.
    # Deduplication already happened upstream; we keep dict.fromkeys here only as a safety net
    # for JSON files that were generated outside the pipeline (e.g. hand-edited resumes).
    raw_skills = raw_json.get('skills', {})
    raw_technical = [item["name"] for item in raw_skills.get("technical", []) if isinstance(item, dict)]
    raw_non_technical = [item["name"] for item in raw_skills.get("nonTechnical", []) if isinstance(item, dict)]
    web_json['skills'] = {
        "technical": [{"name": skill} for skill in dict.fromkeys(raw_technical)],
        "nonTechnical": [{"name": skill} for skill in dict.fromkeys(raw_non_technical)],
    }


    # Work Experiences
    web_work = []
    for work in raw_json["work"]:
        web_work.append({
            **work,
            "summary": _list_to_markdown(work.get('highlights', []))
        })
    web_json['work'] = web_work

    # activities
    web_json['activities']["involvements"] = ""
    web_json['volunteer'] = raw_json.get("volunteer", [])
    web_json['awards'] = raw_json.get("awards", [])

    return web_json


def main():
    # yaml_data = read_yaml(filename='./my_applications/resume_raw.yaml')
    # yaml_data = read_yaml(filename='my_applications/20230916__NOIR__VueJS Developer/VueJS Developer.yaml')
    yaml_data = read_yaml(filename='my_applications/test.yaml')
    json_data = yaml_to_json(yaml_data)

    # Write the data to the JSON file
    with open("data.json", "w", encoding="utf-8") as json_file:
        json.dump(json_data, json_file)


if __name__ == '__main__':
    main()
