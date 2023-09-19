import json
import logging
import os
import time
from datetime import datetime
# from IPython.display import display, Markdown
from pathvalidate import sanitize_filename

import utils

from prompts import Job_Post, Resume_Builder
from yaml_to_json import yaml_to_json

# create logger
logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, root_path="my_applications", openai_model_name="gpt-3.5-turbo"):
        self.root_path: str = root_path
        self.job_text: str = ""
        self.resume_text: dict = {}
        self.parsed_job: dict = {}
        self.resume = None
        self.resume_filename: str = ""
        self.folder: str = ""
        self.llm_kwargs = dict(
            model_name=openai_model_name,
            model_kwargs=dict(top_p=0.6, frequency_penalty=0.1),
        )

    def set_resume_text(self, resume_text: dict = {}, filename: str = ""):
        if not resume_text and not filename:
            logger.warning("Neither resume text nor filename have been provided.")
            return None
        if resume_text:
            self.resume_text = resume_text
        else:
            self.resume_text = utils.read_yaml(filename=filename)

    def set_job_text(self, job_text: str = "", filename: str = ""):
        if not job_text and not filename:
            logger.warning("Neither job text nor filename have been provided.")
            return None
        if job_text:
            self.job_text = job_text
        else:
            self.job_text = utils.read_jobfile(filename=filename)

    def _create_company_folder(self):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

    def read_and_parse_job(self):
        print("=========== Start parsing job information ===========")
        if not self.job_text:
            logger.warning("Job_text is empty, please call set_job_text() first.")
            return None

        start_time = time.time()
        job_post = Job_Post(self.job_text)
        self.parsed_job = job_post.parse_job_post(verbose=False)

        company_name = self.parsed_job["company"]
        job_title = self.parsed_job["job_title"]
        today_date = datetime.today().strftime("%Y%m%d")
        self.folder = f"{self.root_path}/{today_date}__{company_name}__{job_title}"
        self._create_company_folder()

        job_filename = f"{self.folder}/{job_title}"
        utils.write_yaml(self.parsed_job, filename=f"{job_filename}.job")

        print(f'Step 1: Parsing Done: {job_filename}. Time Using: {time.time() - start_time:.6f}')

    def read_resume(self):
        print("=========== Start reading resume ===========")
        start_time = time.time()

        if not self.parsed_job:
            self.read_and_parse_job()
        if not self.resume_text:
            logger.warning("resume_text is empty, please call set_resume_text() first.")
            return None

        self.resume = Resume_Builder(
            resume=self.resume_text,
            parsed_job=self.parsed_job,
            llm_kwargs=self.llm_kwargs,
        )
        print(f'Step 2: Read Resume Done. Time Using: {time.time() - start_time:.6f}')

    def update_experiences(self, update_yaml=False) -> str:
        print("=========== Start updating experiences ===========")
        start_time = time.time()
        if not self.resume:
            self.read_resume()
        experiences = self.resume.rewrite_unedited_experiences(verbose=False)
        self.resume.experiences = experiences
        if update_yaml:
            experiences_yaml = utils.dict_to_yaml_string(dict(experiences=experiences))
            self.update_resume_data(experiences_yaml)
        print(f'Step 3: Update Experiences Done. Time Using: {time.time() - start_time:.6f}')
        return experiences

    def update_projects(self, update_yaml=False) -> str:
        print("=========== Start updating projects ===========")
        start_time = time.time()
        if not self.resume:
            self.read_resume()
        projects = self.resume.rewrite_projects_desc(verbose=False)
        self.resume.projects = projects
        if update_yaml:
            projects_yaml = utils.dict_to_yaml_string(dict(projects=projects))
            self.update_resume_data(projects_yaml)
        print(f'Step 4: Update Projects Done. Time Using: {time.time() - start_time:.6f}')
        return projects

    def update_skills(self, update_yaml=False) -> str:
        """
        This will match the required skills from the job post with your resume sections
        Outputs a combined list of skills extracted from the job post and included in the raw resume
        """
        print("=========== Start extracting skills ===========")
        start_time = time.time()
        skills = self.resume.extract_matched_skills(verbose=False)
        self.resume.skills = skills
        if update_yaml:
            skills_yaml = utils.dict_to_yaml_string(dict(skills=skills))
            self.update_resume_data(skills_yaml)
        print(f'Step 5: Extract Skills From Job Done. Time Using: {time.time() - start_time:.6f}')
        return skills

    def update_summary(self, update_yaml=False) -> str:
        print("=========== Start updating summary ===========")
        start_time = time.time()
        if not self.resume:
            self.read_resume()
        summary = self.resume.write_summary(verbose=True)
        self.resume.summary = summary
        if update_yaml:
            summary_yaml = utils.dict_to_yaml_string(dict(summary=summary))
            self.update_resume_data(summary_yaml)
        print(f'Step 6: Update Summary Done. Time Using: {time.time() - start_time:.6f}')
        return summary

    def generate_resume_yaml(self):
        if not self.parsed_job:
            self.read_and_parse_job()
        if not self.resume:
            self.read_resume()

        self.resume_filename = os.path.join(
            self.folder,
            sanitize_filename(f"{self.parsed_job['job_title']}")
        )
        resume_final = self.resume.finalize()
        utils.write_yaml(resume_final, filename=f"{self.resume_filename}.yaml")

    def update_resume_data(self, edits):
        # Review the generated output in previous cell.
        # If any updates are needed, copy the cell output below between the triple quotes
        # Set value to """" """" if no edits are needed
        edits = edits.strip()
        updated = []
        if edits:
            new_edit = utils.read_yaml(edits)
            if "experiences" in new_edit:
                updated.append('experiences')
                self.resume.experiences = new_edit["experiences"]
            if "projects" in new_edit:
                updated.append('projects')
                self.resume.projects = new_edit["projects"]
            if "skills" in new_edit:
                updated.append('projects')
                self.resume.skills = new_edit["skills"]
            if "summary" in new_edit:
                updated.append('summary')
                self.resume.summary = new_edit["summary"]

        self.generate_resume_yaml()
        print(f"Successfully: {', '.join(updated)} updated successfully")

    def improve_final_resume(self):
        print("=========== Start improving final resume ===========")
        start_time = time.time()

        if not self.resume_filename:
            self.generate_resume_yaml()

        final_resume = Resume_Builder(
            resume=utils.read_yaml(filename=f"{self.resume_filename}.yaml"),
            parsed_job=utils.read_yaml(filename=f"{self.resume_filename}.job"),
            is_final=True,
            llm_kwargs=self.llm_kwargs,
        )
        improvements = final_resume.suggest_improvements(verbose=True)
        improvements_yaml = utils.dict_to_yaml_string(dict(improvements=improvements))
        self.update_resume_data(improvements_yaml)
        print(f'Step 8: Improve Final Resume Done. Time Using: {time.time() - start_time:.6f}')

    def generate_tex(self):
        print("=========== Start update experiences ===========")
        utils.generate_new_tex(yaml_file=f"{self.resume_filename}.yaml")

    def generate_json(self):
        yaml_data = utils.read_yaml(f"{self.resume_filename}.yaml")
        json_data = yaml_to_json(yaml_data)

        # Write the data to the JSON file
        with open(f"{self.resume_filename}.json", "w", encoding="utf-8") as json_file:
            json.dump(json_data, json_file)

        print("Successfully generate json file.")

    def generate_pdf(self):
        print("=========== Start update experiences ===========")
        # Most common errors during pdf generation occur due to special characters.
        # Escape them with backslashes in the yaml, e.g. $ -> \$
        pdf_file = utils.generate_pdf(yaml_file=f"{self.resume_filename}.yaml")
        # display(Markdown((f"[{pdf_file}](<{pdf_file}>)")))

    def main(self):
        # Step 1 - Read and parse job posting
        self.read_and_parse_job()

        # Step 2 - read raw resume and create Resume builder object
        self.read_resume()

        # Step 3 - Rephrase unedited experiences. Try re-running cells in case of missing answers or hallucinations.
        self.update_experiences()

        # Step 4 - Rephrase projects
        self.update_projects()

        # Step 5 - Extract skills
        self.update_skills()

        # Step 6 - Create a resume summary
        self.update_summary()

        # Step 7 - Generate final resume yaml for review
        self.generate_resume_yaml()

        # Step 8 - Identify resume improvements
        self.improve_final_resume()

        # Step 9 - Generate pdf from yaml
        # generate_pdf(resume_filename)
        self.generate_tex()
        self.generate_json()


if __name__ == '__main__':
    ## Inputs
    my_files_dir = "my_applications"  # location for all job and resume files
    job_file = "job.txt"  # filename with job post text. The entire job post can be pasted in this file, as is.
    raw_resume_file = "resume_raw.yaml"  # filename for raw resume yaml. See example in repo for instructions.

    NOIR = Pipeline()
    #
    job_content = utils.read_jobfile(filename="./my_applications/job.txt")
    resume_content = utils.read_yaml(filename="./my_applications/resume_raw.yaml")
    #
    # # NOIR.set_resume_text()
    NOIR.set_job_text(job_text=job_content)
    NOIR.set_resume_text(resume_text=resume_content)
    NOIR.main()
