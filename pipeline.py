import os
import time
from datetime import datetime
from IPython.display import display, Markdown
from pathvalidate import sanitize_filename

import utils

from prompts import Job_Post, Resume_Builder


class Pipeline:
    def __init__(self, job_path, raw_resume):
        self.job_path = job_path
        self.raw_resume_file = raw_resume
        self.parsed_job = None
        self.resume = None
        self.resume_filename = None
        self.folder = None

    def _create_company_folder(self):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

    def read_and_parse_job(self):
        print("=========== Start parsing job information ===========")
        start_time = time.time()
        job_post = Job_Post(utils.read_jobfile(self.job_path))
        self.parsed_job = job_post.parse_job_post(verbose=False)

        company_name = self.parsed_job["company"]
        job_title = self.parsed_job["job_title"]
        today_date = datetime.today().strftime("%Y%m%d")
        root_path = self.job_path.split('/')[0]
        self.folder = f"{root_path}/{today_date}__{company_name}__{job_title}"
        self._create_company_folder()

        job_filename = f"{self.folder}/{job_title}"
        utils.write_yaml(self.parsed_job, filename=f"{job_filename}.job")

        print(f'Step 1: Parsing Done: {job_filename}. Time Using: {time.time() - start_time:.6f}')

    def read_resume(self):
        print("=========== Start reading resume ===========")
        start_time = time.time()

        self.resume = Resume_Builder(
            resume=utils.read_yaml(filename=os.path.join(self.raw_resume_file)),
            parsed_job=self.parsed_job,
            llm_kwargs=llm_kwargs,
        )
        print(f'Step 2: Read Resume Done. Time Using: {time.time() - start_time:.6f}')

    def update_experiences(self):
        print("=========== Start updating experiences ===========")
        start_time = time.time()

        experiences = self.resume.rewrite_unedited_experiences(verbose=False)
        experiences_yaml = utils.dict_to_yaml_string(dict(experiences=experiences))
        self.update_resume_data(experiences_yaml)
        print(f'Step 3: Update Experiences Done. Time Using: {time.time() - start_time:.6f}')

    def update_projects(self):
        print("=========== Start updating projects ===========")
        start_time = time.time()
        projects = self.resume.rewrite_projects_desc(verbose=False)
        projects_yaml = utils.dict_to_yaml_string(dict(projects=projects))
        self.update_resume_data(projects_yaml)
        print(f'Step 4: Update Projects Done. Time Using: {time.time() - start_time:.6f}')

    def update_skills(self):
        print("=========== Start extracting skills ===========")
        start_time = time.time()
        # This will match the required skills from the job post with your resume sections
        # Outputs a combined list of skills extracted from the job post and included in the raw resume
        skills = self.resume.extract_matched_skills(verbose=False)
        skills_yaml = utils.dict_to_yaml_string(dict(skills=skills))
        self.update_resume_data(skills_yaml)
        print(f'Step 5: Extract Skills From Job Done. Time Using: {time.time() - start_time:.6f}')

    def update_summary(self):
        print("=========== Start updating summary ===========")
        start_time = time.time()
        summary = self.resume.write_summary(verbose=True)
        summary_yaml = utils.dict_to_yaml_string(dict(summary=summary))
        self.update_resume_data(summary_yaml)
        print(f'Step 6: Update Summary Done. Time Using: {time.time() - start_time:.6f}')

    def generate_resume_yaml(self):
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
        # A previously generated resume can also be used here by manually providing resume_filename.
        # Requires the associated parsed job file.
        final_resume = Resume_Builder(
            resume=utils.read_yaml(filename=f"{self.resume_filename}.yaml"),
            parsed_job=utils.read_yaml(filename=f"{self.resume_filename}.job"),
            is_final=True,
            llm_kwargs=llm_kwargs,
        )
        improvements = final_resume.suggest_improvements(verbose=True)
        improvements_yaml = utils.dict_to_yaml_string(dict(improvements=improvements))
        self.update_resume_data(improvements_yaml)
        print(f'Step 8: Improve Final Resume Done. Time Using: {time.time() - start_time:.6f}')

    def generate_tex(self):
        print("=========== Start update experiences ===========")
        utils.generate_new_tex(yaml_file=f"{self.resume_filename}.yaml")

    def generate_pdf(self):
        print("=========== Start update experiences ===========")
        # Most common errors during pdf generation occur due to special characters. Escape them with backslashes in the yaml, e.g. $ -> \$
        pdf_file = utils.generate_pdf(yaml_file=f"{self.resume_filename}.yaml")
        display(Markdown((f"[{pdf_file}](<{pdf_file}>)")))

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


if __name__ == '__main__':
    ## Inputs
    my_files_dir = "my_applications"  # location for all job and resume files
    job_file = "job.txt"  # filename with job post text. The entire job post can be pasted in this file, as is.
    raw_resume_file = "resume_raw.yaml"  # filename for raw resume yaml. See example in repo for instructions.

    # Model for matching resume to job post (except extraction chains)
    # gpt-4 is not publicly available yet and can be 20-30 times costlier than the default model gpt-3.5-turbo.
    # Simple extraction chains are hardcoded to use the cheaper gpt-3.5 model.
    # openai_model_name = "gpt-4"
    openai_model_name = "gpt-3.5-turbo"

    # temperature lower than 1 is preferred. temperature=0 returns deterministic output
    temperature = 0.5

    llm_kwargs = dict(
        model_name=openai_model_name,
        model_kwargs=dict(top_p=0.6, frequency_penalty=0.1),
    )

    NOIR = Pipeline(job_path='my_applications/job.txt', raw_resume='my_applications/resume_raw.yaml')
    NOIR.main()
