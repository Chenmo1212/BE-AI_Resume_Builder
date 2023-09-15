import os
from datetime import datetime
from IPython.display import display, Markdown
from pathvalidate import sanitize_filename

import utils

from prompts import Job_Post, Resume_Builder


def read_and_parse_job():
    job_post = Job_Post(
        utils.read_jobfile(os.path.join(my_files_dir, job_file)),
    )
    parsed_job = job_post.parse_job_post(verbose=False)

    company_name = parsed_job["company"]
    job_title = parsed_job["job_title"]
    today_date = datetime.today().strftime("%Y%m%d")
    job_filename = os.path.join(
        my_files_dir, sanitize_filename(f"{today_date}__{company_name}__{job_title}")
    )
    # print(f"#filename: {job_filename}.job\n")
    utils.write_yaml(parsed_job, filename=f"{job_filename}.job")
    print(f'Step 1: Parsing Done: {job_filename}')
    return parsed_job


def read_resume(parsed_job):
    my_resume = Resume_Builder(
        resume=utils.read_yaml(filename=os.path.join(my_files_dir, raw_resume_file)),
        parsed_job=parsed_job,
        llm_kwargs=llm_kwargs,
    )
    print(f'Step 2: Read Resume Done.')
    return my_resume


def update_experiences(resume):
    experiences = resume.rewrite_unedited_experiences(verbose=False)
    utils.write_yaml(dict(experiences=experiences))
    update_resume_data(resume)
    print(f'Step 3: Update Experiences Done.')


def update_projects(resume):
    projects = resume.rewrite_projects_desc(verbose=False)
    utils.write_yaml(dict(projects=projects))
    update_resume_data(resume)
    print(f'Step 4: Update Projects Done.')


def update_skills(resume):
    # This will match the required skills from the job post with your resume sections
    # Outputs a combined list of skills extracted from the job post and included in the raw resume
    skills = resume.extract_matched_skills(verbose=False)
    utils.write_yaml(dict(skills=skills))
    update_resume_data(resume)
    print(f'Step 5: Extract Skills From Job Done.')


def update_summary(resume):
    summary = resume.write_summary(verbose=True)
    utils.write_yaml(dict(summary=summary))
    update_resume_data(resume)
    print(f'Step 6: Update Summary Done.')


def update_resume_data(resume):
    # Review the generated output in previous cell.
    # If any updates are needed, copy the cell output below between the triple quotes
    # Set value to """" """" if no edits are needed
    edits = """ """

    edits = edits.strip()
    if edits:
        new_edit = utils.read_yaml(edits)
        if "experiences" in new_edit:
            resume.experiences = new_edit["experiences"]
        if "projects" in new_edit:
            resume.projects = new_edit["projects"]
        if "skills" in new_edit:
            resume.skills = new_edit["skills"]
        if "summary" in new_edit:
            resume.summary = new_edit["summary"]


def generate_resume_yaml(resume, parsed_job):
    today_date = datetime.today().strftime("%Y%m%d")
    resume_filename = os.path.join(
        my_files_dir, sanitize_filename(f"{today_date}__{parsed_job['company']}__{parsed_job['job_title']}")
    )
    resume_final = resume.finalize()
    utils.write_yaml(resume_final, filename=f"{resume_filename}.yaml")
    print(f'Step 7: Generate Resume Yaml Done.')
    return resume_filename


def update_resume(resume_filename):
    # A previously generated resume can also be used here by manually providing resume_filename.
    # Requires the associated parsed job file.
    final_resume = Resume_Builder(
        resume=utils.read_yaml(filename=f"{resume_filename}.yaml"),
        parsed_job=utils.read_yaml(filename=f"{resume_filename}.job"),
        is_final=True,
        llm_kwargs=llm_kwargs,
    )
    improvements = final_resume.suggest_improvements(verbose=True)
    utils.write_yaml(dict(improvements=improvements))
    print(f'Step 8: Generate Resume Yaml Done.')


def generate_tex(resume_filename):
    utils.generate_new_tex(yaml_file=f"{resume_filename}.yaml")


def generate_pdf(resume_filename):
    # Most common errors during pdf generation occur due to special characters. Escape them with backslashes in the yaml, e.g. $ -> \$
    pdf_file = utils.generate_pdf(yaml_file=f"{resume_filename}.yaml")
    display(Markdown((f"[{pdf_file}](<{pdf_file}>)")))


def pipeline():
    # Step 1 - Read and parse job posting
    parsed_job = read_and_parse_job()

    # Step 2 - read raw resume and create Resume builder object
    my_resume = read_resume(parsed_job)

    # Step 3 - Rephrase unedited experiences. Try re-running cells in case of missing answers or hallucinations.
    update_experiences(my_resume)

    # Step 4 - Rephrase projects
    update_projects(my_resume)

    # Step 5 - Extract skills
    update_skills(my_resume)

    # Step 6 - Create a resume summary
    update_summary(my_resume)

    # Step 7 - Generate final resume yaml for review
    resume_filename = generate_resume_yaml(my_resume, parsed_job)

    # Step 8 - Identify resume improvements
    update_resume(resume_filename)

    # Step 9 - Generate pdf from yaml
    # generate_pdf(resume_filename)
    generate_tex(resume_filename)


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

    pipeline()
